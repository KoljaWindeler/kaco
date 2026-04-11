
from __future__ import annotations

"""
Konstanten & Hilfsfunktionen für die KACO Custom Component.
- Konfiguration/Schema
- Measurement-Definitionen
- Tolerante Validierung (check_data)
- Form-Erstellung für Config-Flow
"""

from typing import Dict
from collections import OrderedDict
import logging
import datetime
from functools import partial

import voluptuous as vol
import requests
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
)

_LOGGER = logging.getLogger(__name__)

# -----------------------------
# Status-Tabelle (vom WR)
# -----------------------------
# Hinweis: Liste gekürzt/komprimiert; leere Indizes bleiben leer.
t: list[str] = ["" for _ in range(168)]
t_map = {
    0: "Initphase",
    1: "Waiting for feed-in",
    2: "Generator voltage too low",
    3: "Constant volt. control",
    4: "Feed-in mode",
    7: "Self test in progress",
    8: "Self test in progress",
    9: "Test mode",
    10: "Temperature in unit too high",
    11: "Power limitation",
    17: "Powador-protect disconnection",
    18: "Resid. current shutdown (AFI)",
    19: "Generator insulation fault",
    20: "Power rampup active",
    21: "Protect. shutdown overcurrent DC1",
    22: "Protect. shutdown overcurrent DC2",
    23: "Protect. shutdown overcurrent DC3",
    29: "Check ground fault fuse",
    30: "Voltage trans. fault",
    31: "RCD module error",
    32: "Self test error",
    33: "DC feed-in error",
    34: "Internal communication error",
    35: "Protect. shutdown SW",
    36: "Protect. shutdown HW",
    37: "Unknown Hardware",
    38: "Error: Generator Voltage too high",
    41: "Line failure: undervoltage L1",
    42: "Line failure: overvoltage L1",
    43: "Line failure: undervoltage L2",
    44: "Line failure: overvoltage L2",
    45: "Line failure: undervoltage L3",
    46: "Line failure: overvoltage L3",
    47: "Line failure: line-to-line voltage",
    48: "Line failure: underfreqency",
    49: "Line failure: overfrequency",
    50: "Line failure: average voltage",
    55: "DC link voltage error",
    56: "SPI Shutdown",
    57: "Waiting for reactivation",
    58: "Control board overtemperature",
    60: "Generator voltage too high",
    61: "External limit",
    62: "Standalone mode",
    63: "Power reduction P(f)",
    64: "Output current limiting",
    65: "ROCOF error",
    67: "Power section 1 error",
    68: "Power section 2 error",
    69: "Power section 3 error",
    70: "Fan 1 error",
    71: "Fan 2 error",
    72: "Fan 3 error",
    73: "Grid failure: Islanding",
    74: "External reactive power request",
    78: "Resid. current shutdown (AFI)",
    79: "Insulation measurement",
    80: "Insulation meas. not possible",
    81: "Protect. shutdown grid voltage L1",
    82: "Protect. shutdown grid voltage L2",
    83: "Protect. shutdown grid voltage L3",
    84: "Protect. shutdown overv. DC link",
    85: "Protect. shutdown underv. DC link",
    86: "Protect. shutdown unbal. DC link",
    87: "Protect. shutdown overcurrent L1",
    88: "Protect. shutdown overcurrent L2",
    89: "Protect. shutdown overcurrent L3",
    90: "Protect. shutdown voltage drop 5V",
    91: "Protect. shutdown voltage drop 2.5V",
    92: "Protect. shutdown voltage drop 1.5V",
    93: "Self test error buffer 1",
    94: "Self test error buffer 2",
    95: "Self test error relay 1",
    96: "Self test error relay 2",
    97: "Protect. shutdown HW overcurrent",
    98: "Protect. shutdown HW gate driver",
    99: "Protect. shutdown HW buffer-enable",
    100: "Protect. shutdown HW overtemperature",
    101: "Plausibility fault temperature",
    102: "Plausibility fault efficiency",
    103: "Plausibility fault DC link",
    104: "Plausibility fault RCD module",
    105: "Plausibility fault relay",
    106: "Plausibility fault DCDC converter",
    108: "Line failure: overvoltage L1",
    109: "Line failure: overvoltage L2",
    110: "Line failure: overvoltage L3",
    111: "Line failure: undervoltage L1",
    112: "Line failure: undervoltage L2",
    113: "Line failure: undervoltage L3",
    114: "Communication error DC/DC",
    115: "Negative DC current 1",
    116: "Negative DC current 2",
    117: "Negative DC current 3",
    118: "DC overvoltage 1",
    119: "DC overvoltage 2",
    120: "DC overvoltage 3",
    121: "Door opened",
    125: "Error relay control",
    126: "Error RCD measurement",
    127: "Error AC voltage measurement",
    128: "Error internal memory 1",
    129: "Power reduction P(U)",
    130: "Self-test error AFCI module",
    131: "Arc detected on DC1",
    132: "Arc detected on DC2",
    133: "Arc detected on DC3",
    134: "AFCI power supply critical",
    135: "Internal AFCI ADC failed",
    136: "AFCI algorithm failed",
    138: "AFCI parameters corrupted",
    139: "Error external memory 1",
    140: "Not enough AFCI DC inputs",
    141: "Error controller output pin",
    142: "AFCI activation failed",
    148: "Error external memory 1",
    149: "Communication error AFCI module",
    150: "Protect. shutdown voltage drop 1.65V",
    151: "Input current limitation DC1",
    152: "Input current limitation DC2",
    153: "Input current limitation DC3",
    154: "Input power limitation DC1",
    155: "Input power limitation DC2",
    156: "Input power limitation DC3",
    160: "Failure: Grid relay L1",
    161: "Failure: Grid relay L2",
    162: "Failure: Grid relay L3",
    163: "Failure: Grid relay N",
    164: "Failure: Filter relay L1",
    165: "Failure: Filter relay L2",
    166: "Failure: Filter relay L3",
    167: "Failure: Filter relay N",
}
for idx, txt in t_map.items():
    t[idx] = txt

# -----------------------------
# Generals / Meta
# -----------------------------
DOMAIN = "kaco"
PLATFORM = "sensor"
VERSION = "0.1.0"
ISSUE_URL = "https://github.com/KoljaWindeler/kaco/issues"
SCAN_INTERVAL = datetime.timedelta(seconds=5)  # optional

# -----------------------------
# Konfiguration
# -----------------------------
CONF_KACO_URL = "url"
CONF_NAME = "name"
CONF_KWH_INTERVAL = "kwh_interval"
CONF_INTERVAL = "interval"
CONF_GENERATOR_VOLTAGE = "generator_voltage"
CONF_GENERATOR_CURRENT = "generator_current"
CONF_GRID_VOLTAGE = "grid_voltage"
CONF_GRID_CURRENT = "grid_current"

# Defaults
DEFAULT_ICON = "mdi:solar-power"
DEFAULT_NAME = "kaco"
DEFAULT_KWH_INTERVAL = "120"
DEFAULT_INTERVAL = "20"
DEFAULT_GENERATOR_VOLTAGE = False
DEFAULT_GENERATOR_CURRENT = False
DEFAULT_GRID_VOLTAGE = False
DEFAULT_GRID_CURRENT = False

# -----------------------------
# Measurement-Definitionen
# -----------------------------
class MeasurementObj:
    valueKey: str
    unit: str
    isMandatory: bool
    _enableKey: str | None

    def __init__(self, valueKey: str, unit: str, enableKey: str | None = None, isMandatory: bool = False):
        self.valueKey = valueKey
        self.unit = unit
        self._enableKey = enableKey
        self.isMandatory = isMandatory

    @property
    def description(self) -> str:
        # "currentPower" -> "Current Power"
        val = ""
        for char in self.valueKey:
            if char.isupper():
                val += " "
            val += char
        val_list = list(val)
        if val_list:
            val_list[0] = val_list[0].upper()
        return "".join(val_list)

    def checkEnabled(self, config: Dict) -> bool:
        if self.isMandatory:
            return True
        return bool(config.get(self._enableKey, False))


MEAS_CURRENT_POWER = MeasurementObj("currentPower", UnitOfPower.WATT, isMandatory=True)
MEAS_ENERGY_TODAY = MeasurementObj("energyToday", UnitOfEnergy.KILO_WATT_HOUR, isMandatory=True)
MEAS_GEN_VOLT1 = MeasurementObj("generatorVoltage1", UnitOfElectricPotential.VOLT, CONF_GENERATOR_VOLTAGE)
MEAS_GEN_VOLT2 = MeasurementObj("generatorVoltage2", UnitOfElectricPotential.VOLT, CONF_GENERATOR_VOLTAGE)
MEAS_GEN_CURR1 = MeasurementObj("generatorCurrent1", UnitOfElectricCurrent.AMPERE, CONF_GENERATOR_CURRENT)
MEAS_GEN_CURR2 = MeasurementObj("generatorCurrent2", UnitOfElectricCurrent.AMPERE, CONF_GENERATOR_CURRENT)
MEAS_GRID_VOLT1 = MeasurementObj("gridVoltage1", UnitOfElectricPotential.VOLT, CONF_GRID_VOLTAGE)
MEAS_GRID_VOLT2 = MeasurementObj("gridVoltage2", UnitOfElectricPotential.VOLT, CONF_GRID_VOLTAGE)
MEAS_GRID_VOLT3 = MeasurementObj("gridVoltage3", UnitOfElectricPotential.VOLT, CONF_GRID_VOLTAGE)
MEAS_GRID_CURR1 = MeasurementObj("gridCurrent1", UnitOfElectricCurrent.AMPERE, CONF_GRID_CURRENT)
MEAS_GRID_CURR2 = MeasurementObj("gridCurrent2", UnitOfElectricCurrent.AMPERE, CONF_GRID_CURRENT)
MEAS_GRID_CURR3 = MeasurementObj("gridCurrent3", UnitOfElectricCurrent.AMPERE, CONF_GRID_CURRENT)

MEAS_VALUES = [
    MEAS_CURRENT_POWER,
    MEAS_ENERGY_TODAY,
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
]

ERROR_URL = "url_error"

# -----------------------------
# YAML-Schema (optional)
# -----------------------------
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_KACO_URL): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.Coerce(int),
        vol.Optional(CONF_KWH_INTERVAL, default=DEFAULT_KWH_INTERVAL): vol.Coerce(int),
        vol.Optional(CONF_GENERATOR_VOLTAGE, default=DEFAULT_GENERATOR_VOLTAGE): vol.Coerce(bool),
        vol.Optional(CONF_GENERATOR_CURRENT, default=DEFAULT_GENERATOR_CURRENT): vol.Coerce(bool),
        vol.Optional(CONF_GRID_VOLTAGE, default=DEFAULT_GRID_VOLTAGE): vol.Coerce(bool),
        vol.Optional(CONF_GRID_CURRENT, default=DEFAULT_GRID_CURRENT): vol.Coerce(bool),
    }
)

# -----------------------------
# UI-Hilfsfunktionen
# -----------------------------
async def check_data(user_input, async_add_executor_job):
    """
    Best-Effort-Validierung der URL:
    - Kurzer Timeout
    - Bei Fehler NICHT blockieren (gibt {} zurück)
    """
    if CONF_KACO_URL in user_input:
        url = "http://" + user_input[CONF_KACO_URL] + "/realtime.csv"
        try:
            # Timeout muss an requests.get übergeben werden (via partial)
            await async_add_executor_job(partial(requests.get, url, timeout=3))
            return {}
        except Exception as ex:
            _LOGGER.warning(
                "Validation of %s failed: %s — proceeding without blocking.",
                url,
                ex,
            )
            return {}
    return {}

def ensure_config(user_input: Dict | None) -> Dict:
    """Sorge für vollständige Konfig mit Defaults."""
    out: Dict = {
        CONF_NAME: "",
        CONF_KACO_URL: "",
        CONF_INTERVAL: DEFAULT_INTERVAL,
        CONF_KWH_INTERVAL: DEFAULT_KWH_INTERVAL,
        CONF_GENERATOR_VOLTAGE: DEFAULT_GENERATOR_VOLTAGE,
        CONF_GENERATOR_CURRENT: DEFAULT_GENERATOR_CURRENT,
        CONF_GRID_VOLTAGE: DEFAULT_GRID_VOLTAGE,
        CONF_GRID_CURRENT: DEFAULT_GRID_CURRENT,
    }
    if user_input is not None:
        out[CONF_NAME] = user_input.get(CONF_NAME, out[CONF_NAME])
        out[CONF_KACO_URL] = user_input.get(CONF_KACO_URL, out[CONF_KACO_URL])
        out[CONF_INTERVAL] = user_input.get(CONF_INTERVAL, out[CONF_INTERVAL])
        out[CONF_KWH_INTERVAL] = user_input.get(CONF_KWH_INTERVAL, out[CONF_KWH_INTERVAL])
        out[CONF_GENERATOR_VOLTAGE] = user_input.get(CONF_GENERATOR_VOLTAGE, out[CONF_GENERATOR_VOLTAGE])
        out[CONF_GENERATOR_CURRENT] = user_input.get(CONF_GENERATOR_CURRENT, out[CONF_GENERATOR_CURRENT])
        out[CONF_GRID_VOLTAGE] = user_input.get(CONF_GRID_VOLTAGE, out[CONF_GRID_VOLTAGE])
        out[CONF_GRID_CURRENT] = user_input.get(CONF_GRID_CURRENT, out[CONF_GRID_CURRENT])
    return out

def create_form(user_input: Dict | None):
    """Erzeuge das Formular-Schema für UI-Setup/Options."""
    user_input = ensure_config(user_input)
    data_schema = OrderedDict()
    data_schema[vol.Required(CONF_NAME, default=user_input[CONF_NAME])] = str
    data_schema[vol.Required(CONF_KACO_URL, default=user_input[CONF_KACO_URL])] = str
    data_schema[vol.Optional(CONF_INTERVAL, default=user_input[CONF_INTERVAL])] = vol.Coerce(int)
    data_schema[vol.Optional(CONF_KWH_INTERVAL, default=user_input[CONF_KWH_INTERVAL])] = vol.Coerce(int)
    data_schema[vol.Optional(CONF_GENERATOR_VOLTAGE, default=user_input[CONF_GENERATOR_VOLTAGE])] = bool
    data_schema[vol.Optional(CONF_GENERATOR_CURRENT, default=user_input[CONF_GENERATOR_CURRENT])] = bool
    data_schema[vol.Optional(CONF_GRID_VOLTAGE, default=user_input[CONF_GRID_VOLTAGE])] = bool
    data_schema[vol.Optional(CONF_GRID_CURRENT, default=user_input[CONF_GRID_CURRENT])] = bool
    return data_schema
