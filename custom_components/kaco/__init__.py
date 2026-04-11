
from __future__ import annotations

"""Initialer Setup & DataUpdateCoordinator für die KACO Integration."""

import logging
import random
import requests
import datetime
from datetime import timedelta
from typing import Dict, Any
from functools import partial

from homeassistant.core import HomeAssistant
from homeassistant.helpers import update_coordinator
from tzlocal import get_localzone

from .const import (
    DOMAIN,
    PLATFORM,
    ISSUE_URL,
    VERSION,
    t,
    DEFAULT_KWH_INTERVAL,
    DEFAULT_INTERVAL,
    CONF_KWH_INTERVAL,
    CONF_INTERVAL,
    CONF_KACO_URL,
    MEAS_GEN_VOLT1,
    MEAS_GEN_VOLT2,
    MEAS_GEN_CURR1,
    MEAS_GEN_CURR2,
    MEAS_GRID_VOLT1,
    MEAS_GRID_VOLT2,
    MEAS_GRID_VOLT3,
    MEAS_GRID_CURR1,
    MEAS_GRID_CURR2,
    MEAS_GRID_CURR3,
    MEAS_CURRENT_POWER,
    MEAS_ENERGY_TODAY,
    ensure_config,
)

_LOGGER = logging.getLogger(__name__)

# Optionales Start-Up Logging (ohne harte Abhängigkeit von integrationhelper)
try:
    from integrationhelper.const import CC_STARTUP_VERSION  # type: ignore
    _STARTUP_FMT = CC_STARTUP_VERSION
except Exception:
    _STARTUP_FMT = "Starting {name} v{version}. Report issues at {issue_link}"

# Backoff/Retry/Logging-Konstanten
_MIN_INTERVAL = 5        # Sekunden (Mindest-Poll)
_MAX_INTERVAL = 120      # Sekunden (Max-Poll)
_BACKOFF_BASE = 2.0      # exponentieller Faktor
_JITTER_FRACTION = 0.15  # ±15% Zufallsjitter
_WARN_UNTIL_FAILS = 3    # bis zu 3 Warnungen, danach DEBUG
_RETRY_PER_POLL = 2      # lokale Wiederholungsversuche pro Poll
_RT_TIMEOUT = 5          # Timeout realtime.csv
_DAY_TIMEOUT = 10        # Timeout Tagesdatei


def _apply_backoff(current: float, fail_count: int) -> float:
    """Berechne neues Intervall mit exponentiellem Backoff und Jitter."""
    factor = _BACKOFF_BASE ** max(0, fail_count - 1)
    base = min(_MAX_INTERVAL, max(_MIN_INTERVAL, current * factor))
    jitter = 1.0 + random.uniform(-_JITTER_FRACTION, _JITTER_FRACTION)
    return float(min(_MAX_INTERVAL, max(_MIN_INTERVAL, base * jitter)))


def _log_timeout(ip: str, fail_count: int):
    """Reduziere Log-Spam: nur die ersten Timeouts als WARNING."""
    if fail_count <= _WARN_UNTIL_FAILS:
        _LOGGER.warning("Timeout from KACO Panel %s (fail %d)", ip, fail_count)
    else:
        _LOGGER.debug("Timeout from KACO Panel %s (fail %d)", ip, fail_count)


def _bootstrap_defaults(existing: Dict | None) -> Dict:
    """Default-Werte, damit coordinator.data nie None sein muss."""
    values: Dict[str, Any] = existing or {}
    values.setdefault("extra", {})
    values["extra"].setdefault("max_power", 0)
    values["extra"].setdefault("serialno", "no_serial")
    values["extra"].setdefault("model", "no_model")
    return values


async def async_setup(hass: HomeAssistant, config):
    """Basis-Setup (Logeintrag)."""
    _LOGGER.info(_STARTUP_FMT.format(name=DOMAIN, version=VERSION, issue_link=ISSUE_URL))
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry):
    """Setup via UI/YAML."""
    # Defaults für fehlende Werte
    new_data = ensure_config(config_entry.data)
    hass.config_entries.async_update_entry(config_entry, data=new_data, options=new_data)

    # Listener für Options-Änderungen
    config_entry.add_update_listener(update_listener)

    # Entitäten laden
    await hass.config_entries.async_forward_entry_setups(config_entry, [PLATFORM])
    return True


async def async_remove_entry(hass: HomeAssistant, config_entry):
    """Unload bei Entfernen."""
    try:
        await hass.config_entries.async_forward_entry_unload(config_entry, PLATFORM)
        _LOGGER.info("Successfully removed sensor from the integration")
    except ValueError:
        pass


async def update_listener(hass: HomeAssistant, entry):
    """Options‑Update: Entitäten neu laden."""
    entry.data = entry.options
    await hass.config_entries.async_forward_entry_unload(entry, PLATFORM)
    hass.async_add_job(hass.config_entries.async_forward_entry_setups(entry, [PLATFORM]))


async def get_coordinator(hass: HomeAssistant, config: Dict) -> update_coordinator.DataUpdateCoordinator:
    """Erzeuge (oder re-use) den DataUpdateCoordinator für die gegebene IP."""
    ip = config.get(CONF_KACO_URL)
    kwh_interval = float(config.get(CONF_KWH_INTERVAL)) if config.get(CONF_KWH_INTERVAL) is not None else float(DEFAULT_KWH_INTERVAL)
    base_interval = float(config.get(CONF_INTERVAL)) if config.get(CONF_INTERVAL) is not None else float(DEFAULT_INTERVAL)

    _LOGGER.debug("Initialize the data coordinator for IP %s", ip)

    # Datenstruktur vorbereiten
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(ip or "unknown", {})
    node = hass.data[DOMAIN][ip or "unknown"]

    node.setdefault("fail_count", 0)
    node.setdefault("work_interval", float(base_interval))
    node.setdefault("values", _bootstrap_defaults(node.get("values")))

    async def async_get_datas() -> Dict:
        """Poll-Funktion (robust), liefert immer ein Dict zurück."""
        values = _bootstrap_defaults(node.get("values"))

        # Falls keine IP konfiguriert wurde: keine Netzwerkanfrage, nur Defaults/letzte Werte
        if not ip or not isinstance(ip, str) or not ip.strip():
            _LOGGER.warning("KACO url missing in config; using inert coordinator with defaults.")
            node["values"] = values
            return node["values"]

        # Ab hier: normales Verhalten mit Retry/Backoff
        url_rt = "http://" + ip + "/realtime.csv"
        url_today = "http://" + ip + "/" + datetime.date.today().strftime("%Y%m%d") + ".csv"

        try:
            now = datetime.datetime.now(get_localzone()).replace(microsecond=0)
            if "last_kWh_Update" not in values["extra"]:
                values["extra"]["last_kWh_Update"] = now - timedelta(seconds=kwh_interval)

            # --- realtime.csv mit lokalen Retries ---
            ds = None
            for _attempt in range(1 + _RETRY_PER_POLL):
                try:
                    d = await hass.async_add_executor_job(
                        partial(requests.get, url_rt, timeout=_RT_TIMEOUT)
                    )
                    parts = d.content.decode("ISO-8859-1").split(";")
                    if len(parts) == 14:
                        ds = parts
                        break
                    ds = None
                except requests.exceptions.Timeout:
                    ds = None
                except Exception:
                    ds = None

            if ds is None:
                node["fail_count"] += 1
                _log_timeout(ip, node["fail_count"])
                node["work_interval"] = _apply_backoff(node["work_interval"], node["fail_count"])
                node["values"] = values
                coord = node.get("coordinator")
                if coord:
                    coord.update_interval = timedelta(seconds=node["work_interval"])
                return node["values"]

            # Erfolg
            node["fail_count"] = 0
            node["work_interval"] = float(base_interval)
            values["extra"]["last_updated"] = now

            # Parsing / Skalierung
            values[MEAS_GEN_VOLT1.valueKey] = round(float(ds[1])  / (65535 / 1600), 3)
            values[MEAS_GEN_VOLT2.valueKey] = round(float(ds[2])  / (65535 / 1600), 3)
            values[MEAS_GEN_CURR1.valueKey] = round(float(ds[6])  / (65535 / 200 ), 3)
            values[MEAS_GEN_CURR2.valueKey] = round(float(ds[7])  / (65535 / 200 ), 3)
            values[MEAS_GRID_VOLT1.valueKey] = round(float(ds[3])  / (65535 / 1600), 3)
            values[MEAS_GRID_VOLT2.valueKey] = round(float(ds[4])  / (65535 / 1600), 3)
            values[MEAS_GRID_VOLT3.valueKey] = round(float(ds[5])  / (65535 / 1600), 3)
            values[MEAS_GRID_CURR1.valueKey] = round(float(ds[8])  / (65535 / 200 ), 3)
            values[MEAS_GRID_CURR2.valueKey] = round(float(ds[9])  / (65535 / 200 ), 3)
            values[MEAS_GRID_CURR3.valueKey] = round(float(ds[10]) / (65535 / 200 ), 3)
            values["extra"]["temp"] = float(ds[12]) / 100
            values["extra"]["status"] = t[int(ds[13])]
            values["extra"]["status_code"] = int(ds[13])
            values[MEAS_CURRENT_POWER.valueKey] = round(float(ds[11]) / (65535 / 100000))
            if values[MEAS_CURRENT_POWER.valueKey] > values["extra"]["max_power"]:
                values["extra"]["max_power"] = values[MEAS_CURRENT_POWER.valueKey]
            node["max_power"] = values[MEAS_CURRENT_POWER.valueKey]

            # Tagesdatei (Energie heute), rate-limited
            need_day = (
                now >= values["extra"]["last_kWh_Update"] + timedelta(seconds=kwh_interval)
                or MEAS_ENERGY_TODAY.valueKey not in values
            )
            if need_day:
                d = await hass.async_add_executor_job(
                    partial(requests.get, url_today, timeout=_DAY_TIMEOUT)
                )
                if d.status_code == 200:
                    text = d.content.decode("ISO-8859-1")
                    if len(text) > 10:
                        lines = text.split("\r")
                        if len(lines) > 1:
                            cols = lines[1].split(";")
                            if len(cols) > 4:
                                values[MEAS_ENERGY_TODAY.valueKey] = float(cols[4])
                                node[MEAS_ENERGY_TODAY.valueKey] = values[MEAS_ENERGY_TODAY.valueKey]
                                values["extra"]["serialno"] = cols[1]
                                node["serialno"] = values["extra"]["serialno"]
                                values["extra"]["model"] = cols[0]
                                values["extra"]["last_kWh_Update"] = now

        except requests.exceptions.Timeout:
            node["fail_count"] += 1
            _log_timeout(ip, node["fail_count"])
            node["work_interval"] = _apply_backoff(node["work_interval"], node["fail_count"])
            node["values"] = values
            coord = node.get("coordinator")
            if coord:
                coord.update_interval = timedelta(seconds=node["work_interval"])
            return node["values"]

        except Exception as ex:
            node["fail_count"] += 1
            _LOGGER.error("Exception while fetching data (fail %d): %s", node["fail_count"], ex)
            node["work_interval"] = _apply_backoff(node["work_interval"], node["fail_count"])
            node["values"] = values
            coord = node.get("coordinator")
            if coord:
                coord.update_interval = timedelta(seconds=node["work_interval"])
            return node["values"]

        # Erfolg: Werte persistieren & Intervall ggf. zurücksetzen
        node["values"] = values
        coord = node.get("coordinator")
        if coord:
            coord.update_interval = timedelta(seconds=node["work_interval"])
        return values

    # Coordinator erzeugen (oder re-use)
    if "coordinator" in node and isinstance(node["coordinator"], update_coordinator.DataUpdateCoordinator):
        _LOGGER.debug("Use existing coordinator for %s", ip or "unknown")
        return node["coordinator"]

    _LOGGER.debug("Create new coordinator for %s", ip or "unknown")
    coordinator = update_coordinator.DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name=f"{DOMAIN}_{ip or 'unknown'}",
        update_method=async_get_datas,
        update_interval=timedelta(seconds=node["work_interval"]),
    )
    node["coordinator"] = coordinator

    # Erster Refresh (nicht-blockierend)
    await coordinator.async_refresh()
    _LOGGER.debug("Coordinator initialized for %s", ip or "unknown")
    return coordinator
