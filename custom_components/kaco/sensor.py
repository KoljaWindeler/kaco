"""
Custom component to grab data from a kaco solar inverter.

@ Author	  : Kolja Windeler
@ Date		  : 2020/08/10
@ Description : Grabs and parses the data of a kaco inverter
"""
import logging
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.const import (CONF_NAME)

from tzlocal import get_localzone
from functools import partial
import requests
import datetime
import traceback
from .const import *

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
	"""Run setup via YAML."""
	_LOGGER.debug("Config via YAML")
	if(config is not None):
		async_add_entities([kaco_sensor(hass, config)], True)


async def async_setup_entry(hass, config, async_add_devices):
	"""Run setup via Storage."""
	_LOGGER.debug("Config via Storage/UI")
	if(len(config.data) > 0):
		async_add_devices([kaco_sensor(hass, config.data)], True)


class kaco_sensor(Entity):
	"""Representation of a Sensor."""

	def __init__(self, hass, config):
		"""Initialize the sensor."""
		self._state_attributes = None
		self._state = None

		self._url = config.get(CONF_KACO_URL)
		self._name = config.get(CONF_NAME)
		self._icon = config.get(CONF_ICON)
		self._kwh_interval = int(config.get(CONF_KWH_INTERVAL))
		self._interval = int(config.get(CONF_INTERVAL))

		now = datetime.datetime.now(get_localzone()).replace(microsecond=0)
		self._lastUpdate_kwh = now - datetime.timedelta(seconds = self._kwh_interval)
		self._lastUpdate = now - datetime.timedelta(seconds = self._interval)
		self._id = self._url.split('.')[-1]

		_LOGGER.debug("KACO config: ")
		_LOGGER.debug("\tname: " + self._name)
		_LOGGER.debug("\turl: " + self._url)
		_LOGGER.debug("\ticon: " + str(self._icon))

		self.kaco = {
			'extra': {
				'genVolt1': 0,
				'genVolt2': 0,
				'genCur1': 0,
				'genCur2': 0,
				'gridVolt1': 0,
				'gridVolt2': 0,
				'gridVolt3': 0,
				'gridCur1': 0,
				'gridCur2': 0,
				'gridCur3': 0,
				'temp': 0,
				'kwh_today': 0,
				'max_power': 0,
				'status': "loading",
				'status_code': 0,

				'last_updated': None,
				'reload_at': None,
			},
			'power': 0,
		}

		self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, "kaco_"+str(self._id), hass=hass)

	@property
	def name(self):
		"""Return the name of the sensor."""
		return self._name

	@property
	def device_state_attributes(self):
		"""Return the state attributes."""
		return self._state_attributes

	@property
	def unit_of_measurement(self):
		"""Return the unit the value is expressed in."""
		return "W"

	@property
	def state(self):
		"""Return the state of the sensor."""
		return self._state

	@property
	def icon(self):
		"""Return the icon to use in the frontend."""
		return self._icon

	def exc(self):
		"""Print nicely formated exception."""
		_LOGGER.error("\n\n============= KACO Integration Error ================")
		_LOGGER.error("unfortunately KACO hit an error, please open a ticket at")
		_LOGGER.error("https://github.com/KoljaWindeler/kaco/issues")
		_LOGGER.error("and paste the following output:\n")
		_LOGGER.error(traceback.format_exc())
		_LOGGER.error("\nthanks, Kolja")
		_LOGGER.error("============= KACO Integration Error ================\n\n")

	async def get_data(self):
		url_rt = "http://"+self._url+"/realtime.csv"
		url_today = "http://"+self._url+"/"+datetime.date.today().strftime('%Y%m%d')+".csv"

		try:
			now = datetime.datetime.now(get_localzone()).replace(microsecond=0)

			d = await self.hass.async_add_executor_job(partial(requests.get, url_rt, timeout=2))
			ds = d.content.decode('ISO-8859-1').split(';')

			if(len(ds)==14):
				self._lastUpdate = now
				self.kaco['extra']['last_updated'] = now
				self.kaco['extra']['reload_at'] = now + datetime.timedelta(seconds = self._interval)

				self.kaco['extra']['genVolt1'] = round(float(ds[1])/(65535/1600),3)
				self.kaco['extra']['genVolt2'] = round(float(ds[2])/(65535/1600),3)
				self.kaco['extra']['genCur1'] =  round(float(ds[6])/(65535/200),3)
				self.kaco['extra']['genCur2'] =  round(float(ds[7])/(65535/200),3)

				self.kaco['extra']['gridVolt1'] = round(float(ds[3])/(65535/1600),3)
				self.kaco['extra']['gridVolt2'] = round(float(ds[4])/(65535/1600),3)
				self.kaco['extra']['gridVolt3'] = round(float(ds[5])/(65535/1600),3)
				self.kaco['extra']['gridCur1'] =  round(float(ds[8])/(65535/200),3)
				self.kaco['extra']['gridCur2'] =  round(float(ds[9])/(65535/200),3)
				self.kaco['extra']['gridCur3'] =  round(float(ds[10])/(65535/200),3)

				self.kaco['extra']['temp'] = float(ds[12])/100
				self.kaco['extra']['status'] = t[int(ds[13])]
				self.kaco['extra']['status_code'] = int(ds[13])
				self.kaco['power'] = round(float(ds[11])/(65535/100000))

				if(self.kaco['power'] > self.kaco['extra']['max_power']):
					self.kaco['extra']['max_power'] = self.kaco['power']


			if(now > self._lastUpdate_kwh + datetime.timedelta(seconds = self._kwh_interval)):
				d = await self.hass.async_add_executor_job(partial(requests.get, url_today, timeout=2))
				d = d.content.decode('ISO-8859-1')

				if(len(d)>10):
					ds = d.split('\r')[1]
					kwh = float(ds.split(';')[4])
					self.kaco['extra']['kwh_today'] = kwh
					self._lastUpdate_kwh = now
		except requests.exceptions.Timeout:
			pass
			#print("timeout exception on Kaco integration")
		except Exception:
			self.exc()


	async def async_update(self):
		"""Fetch new state data for the sensor.
		This is the only method that should fetch new data for Home Assistant.
		"""
		try:
			# first run
			if(self.kaco['extra']['reload_at'] is None):
				await self.get_data()
			# check if we're past reload_at
			elif(self.kaco['extra']['reload_at'] <= datetime.datetime.now(get_localzone())):
				await self.get_data()

			# update states
			self._state_attributes = self.kaco['extra']
			self._state = self.kaco['power']
		except Exception:
			self._state = "error"
			self.exc()
