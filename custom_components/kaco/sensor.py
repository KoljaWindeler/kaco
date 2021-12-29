"""
Custom component to grab data from a kaco solar inverter.

@ Author      : Kolja Windeler
@ Date          : 2020/08/10
@ Description : Grabs and parses the data of a kaco inverter
"""
import logging
from typing import Tuple
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
from homeassistant.helpers import update_coordinator
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import ENTITY_ID_FORMAT, SensorEntity
from homeassistant.const import CONF_NAME

from tzlocal import get_localzone
from functools import partial
import requests
import datetime
import traceback

from custom_components.kaco import get_coordinator
from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Run setup via YAML."""
    _LOGGER.debug("Config via YAML")
    if config is not None:
        coordinator = await get_coordinator(hass, config.data)
        async_add_entities([
            kaco_power_sensor(hass, config.data, coordinator),
            kaco_energy_sensor(hass, config.data, coordinator)], True)


async def async_setup_entry(hass, config, async_add_devices):
    """Run setup via Storage."""
    _LOGGER.debug("Config via Storage/UI")
    if len(config.data) > 0:
        coordinator = await get_coordinator(hass, config.data)
        async_add_devices([
            kaco_power_sensor(hass, config.data, coordinator),
            kaco_energy_sensor(hass, config.data, coordinator)], True)


class kaco_base_sensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    def __init__(
        self, hass, config, coordinator: update_coordinator.DataUpdateCoordinator
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = hass
        self._state_attributes = None
        self.coordinator = coordinator
        self.data = coordinator.data

        self._url = config.get(CONF_KACO_URL)
        self._name = config.get(CONF_NAME)
        self._icon = config.get(CONF_ICON)
        self._kwh_interval = int(config.get(CONF_KWH_INTERVAL))
        self._interval = int(config.get(CONF_INTERVAL))

        self._id = self._url.split(".")[-1]

        _LOGGER.debug("KACO config: ")
        _LOGGER.debug("\tname: " + self._name)
        _LOGGER.debug("\turl: " + self._url)
        _LOGGER.debug("\ticon: " + str(self._icon))

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._id)},
            "name": self.name,
            "configuration_url": "http://" + self._url,
            "manufacturer": "Kaco",
            "model": self.data["extra"]["model"],
        }


class kaco_power_sensor(kaco_base_sensor):
    def __init__(
        self, hass, config, coordinator: update_coordinator.DataUpdateCoordinator
    ):
        super().__init__(hass, config, coordinator)

        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, "kaco_" + str(self._id) + "_power", hass=hass
        )

    @property
    def unique_id(self):
        return self.data["extra"]["serialno"] + "_power"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + " Current"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self.coordinator.data.get("extra")

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return "W"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("power")

class kaco_energy_sensor(kaco_base_sensor):
    def __init__(
        self, hass, config, coordinator: update_coordinator.DataUpdateCoordinator
    ):
        super().__init__(hass, config, coordinator)

        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, "kaco_" + str(self._id) + "_energy", hass=hass
        )

    @property
    def unique_id(self):
        return self.data["extra"]["serialno"] + "_energy"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name + " Energy Today"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self.coordinator.data.get("extra")

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return "kWh"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self.coordinator.data.get("kwh_today")

    @property
    def device_class(self):
        return "energy"

    @property
    def state_class(self):
        return "total_increasing"