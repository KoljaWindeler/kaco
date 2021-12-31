"""Provide the initial setup."""
import logging
from typing import Dict
from integrationhelper.const import CC_STARTUP_VERSION
from .const import *

from homeassistant.helpers import update_coordinator
from homeassistant.core import HomeAssistant

from tzlocal import get_localzone
from functools import partial
import requests
from datetime import timedelta

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Provide Setup of platform."""
    _LOGGER.info(
        CC_STARTUP_VERSION.format(name=DOMAIN, version=VERSION, issue_link=ISSUE_URL)
    )
    return True


async def async_setup_entry(hass, config_entry):
    """Set up this integration using UI/YAML."""
    config_entry.data = ensure_config(
        config_entry.data
    )  # make sure that missing storage values will be default (const function)
    config_entry.options = config_entry.data
    config_entry.add_update_listener(update_listener)
    # Add sensor
    hass.async_add_job(
        hass.config_entries.async_forward_entry_setup(config_entry, PLATFORM)
    )
    return True


async def async_remove_entry(hass, config_entry):
    """Handle removal of an entry."""
    try:
        await hass.config_entries.async_forward_entry_unload(config_entry, PLATFORM)
        _LOGGER.info("Successfully removed sensor from the integration")
    except ValueError:
        pass


async def update_listener(hass, entry):
    """Update listener."""
    entry.data = entry.options
    await hass.config_entries.async_forward_entry_unload(entry, PLATFORM)
    hass.async_add_job(hass.config_entries.async_forward_entry_setup(entry, PLATFORM))


def exc():
    """Print nicely formated exception."""
    _LOGGER.error("\n\n============= KACO Integration Error ================")
    _LOGGER.error("unfortunately KACO hit an error, please open a ticket at")
    _LOGGER.error("https://github.com/kcinnaySte/kaco/issues")
    _LOGGER.error("and paste the following output:\n")
    _LOGGER.error(traceback.format_exc())
    _LOGGER.error("\nthanks, Kolja")
    _LOGGER.error("============= KACO Integration Error ================\n\n")


async def get_coordinator(hass: HomeAssistant, config: Dict) -> update_coordinator.DataUpdateCoordinator:
    ip = config.get(CONF_KACO_URL)
    kwhInterval = float(config.get(CONF_KWH_INTERVAL))
    if kwhInterval == None:
        kwhInterval = float(DEFAULT_KWH_INTERVAL)
    interval = float(config.get(CONF_INTERVAL))
    if interval == None:
        interval = float(DEFAULT_INTERVAL)
    _LOGGER.debug("initialize the date coordinator for IP %s", ip)
    if DOMAIN in hass.data:
        if ip in hass.data[DOMAIN]:
            if "coordinator" in hass.data[DOMAIN][ip]:
                return hass.data[DOMAIN][ip]["coordinator"]
        else:
            hass.data[DOMAIN][ip] = dict()
    else:
        hass.data[DOMAIN] = dict()
        hass.data[DOMAIN][ip] = dict()

    async def async_get_datas() -> Dict:
        url_rt = "http://" + ip + "/realtime.csv"
        url_today = (
            "http://" + ip + "/" + datetime.date.today().strftime("%Y%m%d") + ".csv"
        )

        if "values" in hass.data[DOMAIN][ip]:
            values = hass.data[DOMAIN][ip]["values"]
        else:
            values = dict()
            values["extra"] = dict()
        if not "max_power" in values["extra"]:
            values["extra"]["max_power"] = 0


        try:
            now = datetime.datetime.now(get_localzone()).replace(microsecond=0)

            if not "last_kWh_Update" in values["extra"]:
                values["extra"]["last_kWh_Update"] = now - timedelta(seconds=kwhInterval)

            d = await hass.async_add_executor_job(
                partial(requests.get, url_rt, timeout=2)
            )
            ds = d.content.decode("ISO-8859-1").split(";")

            if len(ds) != 14:
                _LOGGER.warn("KACO Panel with IP %s is unavilable", ip)
                return None

            values["extra"]["last_updated"] = now

            values[MEAS_GEN_VOLT1.valueKey] = round(float(ds[1]) / (65535 / 1600), 3)
            values[MEAS_GEN_VOLT2.valueKey] = round(float(ds[2]) / (65535 / 1600), 3)
            values[MEAS_GEN_CURR1.valueKey] = round(float(ds[6]) / (65535 / 200), 3)
            values[MEAS_GEN_CURR2.valueKey] = round(float(ds[7]) / (65535 / 200), 3)

            values[MEAS_GRID_VOLT1.valueKey] = round(float(ds[3]) / (65535 / 1600), 3)
            values[MEAS_GRID_VOLT2.valueKey] = round(float(ds[4]) / (65535 / 1600), 3)
            values[MEAS_GRID_VOLT3.valueKey] = round(float(ds[5]) / (65535 / 1600), 3)
            values[MEAS_GRID_CURR1.valueKey] = round(float(ds[8]) / (65535 / 200), 3)
            values[MEAS_GRID_CURR2.valueKey] = round(float(ds[9]) / (65535 / 200), 3)
            values[MEAS_GRID_CURR3.valueKey] = round(float(ds[10]) / (65535 / 200), 3)

            values["extra"]["temp"] = float(ds[12]) / 100
            values["extra"]["status"] = t[int(ds[13])]
            values["extra"]["status_code"] = int(ds[13])
            values[MEAS_CURRENT_POWER.valueKey] = round(float(ds[11]) / (65535 / 100000))

            if values[MEAS_CURRENT_POWER.valueKey] > values["extra"]["max_power"]:
                values["extra"]["max_power"] = values[MEAS_CURRENT_POWER.valueKey]
                hass.data[DOMAIN][ip]["max_power"] = values[MEAS_CURRENT_POWER.valueKey]

            if now >= values["extra"]["last_kWh_Update"] + datetime.timedelta(
                seconds=kwhInterval
            ) or not MEAS_ENERGY_TODAY.valueKey in values:
                d = await hass.async_add_executor_job(
                    partial(requests.get, url_today, timeout=10)
                )
                d = d.content.decode("ISO-8859-1")

                if len(d) > 10:
                    ds = d.split("\r")[1]
                    dss = ds.split(";")
                    values[MEAS_ENERGY_TODAY.valueKey] = float(dss[4])
                    hass.data[DOMAIN][ip][MEAS_ENERGY_TODAY.valueKey] = values[MEAS_ENERGY_TODAY.valueKey]
                    #TODO Lokal speichern da UID
                    values["extra"]["serialno"] = dss[1]
                    hass.data[DOMAIN][ip]["serialno"] = values["extra"]["serialno"]
                    values["extra"]["model"] = dss[0]
                    values["extra"]["last_kWh_Update"] = now
        except requests.exceptions.Timeout as to:
            _LOGGER.warning("KACO Panel with IP %s doesn't answer", ip)
            raise to
        except Exception as ex:
            exc()
            raise ex
        hass.data[DOMAIN][ip]["values"] = values
        return values


    coordinator = update_coordinator.DataUpdateCoordinator(
        hass,
        logging.getLogger(__name__),
        name=DOMAIN + "_" + ip,
        update_method=async_get_datas,
        update_interval=timedelta(seconds=interval),
    )
    hass.data[DOMAIN][ip]["coordinator"] = coordinator
    await coordinator.async_refresh()
    return coordinator
