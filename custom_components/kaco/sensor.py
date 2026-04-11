
"""
Custom component to grab data from a kaco solar inverter.
@ Author : Kolja Windeler
@ Date : 2020/08/10
@ Description : Grabs and parses the data of a kaco inverter
"""
from __future__ import annotations

import logging
from homeassistant.helpers import update_coordinator
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME, UnitOfEnergy
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.kaco import get_coordinator
from .const import (
    DOMAIN,
    DEFAULT_ICON,
    DEFAULT_NAME,
    CONF_KACO_URL,
    MEAS_VALUES,
    MeasurementObj,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Run setup via YAML."""
    _LOGGER.debug("Config via YAML")
    if config is not None:
        coordinator = await get_coordinator(hass, config)
        async_add_entities(
            [
                KacoSensor(hass, config, coordinator, sensor_obj)
                for sensor_obj in MEAS_VALUES
                if sensor_obj.checkEnabled(config)
            ],
            # Wichtig: KEIN erzwungenes initiales Update – Coordinator liefert Daten nach.
            False,
        )


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Run setup via Storage/UI."""
    _LOGGER.debug("Config via Storage/UI")
    if len(config_entry.data) > 0:
        coordinator = await get_coordinator(hass, config_entry.data)
        async_add_devices(
            [
                KacoSensor(hass, config_entry.data, coordinator, sensor_obj)
                for sensor_obj in MEAS_VALUES
                if sensor_obj.checkEnabled(config_entry.data)
            ],
            # Wichtig: KEIN erzwungenes initiales Update
            False,
        )


class KacoSensor(CoordinatorEntity, SensorEntity):
    """Representation of a KACO Sensor."""

    def __init__(
        self,
        hass,
        config: dict,
        coordinator: update_coordinator.DataUpdateCoordinator,
        sensor_obj: MeasurementObj,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self.coordinator = coordinator

        self._value_key = sensor_obj.valueKey
        self._unit = sensor_obj.unit
        self._description = sensor_obj.description
        self._url: str = config.get(CONF_KACO_URL) or ""
        self._name: str = config.get(CONF_NAME) or DEFAULT_NAME
        self._icon = DEFAULT_ICON

        # Fallback-ID aus Host/IP (letztes Label) oder komplette URL
        try:
            self._id = (self._url.split(".")[-1] or self._url).strip()
        except Exception:
            self._id = (self._url or "unknown").strip()

        _LOGGER.debug("KACO config:")
        _LOGGER.debug("\tname: %s", self._name)
        _LOGGER.debug("\turl: %s", self._url)
        _LOGGER.debug("\ticon: %s", self._icon)
        _LOGGER.debug("\tvalueKey: %s", self._value_key)
        _LOGGER.debug("\tInitData: %s", getattr(self.coordinator, "data", None))

    @property
    def unique_id(self) -> str:
        """Stable unique_id even if coordinator has no data yet."""
        serial = None
        try:
            if self.coordinator and self.coordinator.data:
                serial = self.coordinator.data.get("extra", {}).get("serialno")
        except Exception:
            serial = None
        base = serial or self._id or self._url or "unknown"
        return f"{DOMAIN}_{base}_{self._value_key}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self._name} {self._description}"

    @property
    def icon(self) -> str:
        """Return the icon for the frontend."""
        return self._icon

    @property
    def device_info(self):
        """Device info without hard dependency on live data."""
        info = {
            "identifiers": {(DOMAIN, self._id)},
            "name": self.name,
            "configuration_url": f"http://{self._url}" if self._url else None,
            "manufacturer": "Kaco",
        }
        try:
            if self.coordinator and self.coordinator.data:
                model = self.coordinator.data.get("extra", {}).get("model")
                if model:
                    info["model"] = model
        except Exception:
            pass
        return info

    @property
    def extra_state_attributes(self):
        """Return extra attributes if available."""
        try:
            if self.coordinator and self.coordinator.data:
                return self.coordinator.data.get("extra")
            return None
        except Exception:
            return None

    # HA <2022: unit_of_measurement; HA 2022+: native_unit_of_measurement
    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def native_unit_of_measurement(self):
        return self._unit

    @property
    def native_value(self):
        """Return the sensor value if available, else None."""
        try:
            if self.coordinator and self.coordinator.data:
                return self.coordinator.data.get(self._value_key)
            return None
        except Exception:
            return None

    @property
    def device_class(self):
        if self._unit == UnitOfEnergy.KILO_WATT_HOUR:
            return SensorDeviceClass.ENERGY
        if self._unit in ["W", "kW"]:
            return SensorDeviceClass.POWER
        return None

    @property
    def state_class(self):
        if self._unit == UnitOfEnergy.KILO_WATT_HOUR:
            return "total_increasing"
        if self._unit in ["W", "kW"]:
            return "measurement"
        return None

    # Wichtig: **keine** eigene `available`-Property überschreiben.
    # Wir nutzen die von `CoordinatorEntity`, die auf `last_update_success` basiert.

