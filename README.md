# Kaco

Adds a sensor to Home Assistant that displays several information of a Kaco / Schueco SGI-9k or similar

**This component will set up the following platforms.**

Platform | Description
-- | --
`sensor` | Show date and remaining days to event

![Example](kaco.png)


## Features

- Shows all values from the webinterface
- Status is parsed and shown as text
- Tracks maximal seen power (since restart of HA)
- Configurable update interval

# Installation

## HACS

HACS is at the moment not supported. But I will work on it.

## Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `kaco`.
4. Download _all_ the files from the `custom_components/kaco/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Follow the instructions under [Configuration](#Configuration) below.

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/kaco/translations/en.json
custom_components/kaco/__init__.py
custom_components/kaco/manifest.json
custom_components/kaco/sensor.py
custom_components/kaco/config_flow.py
custom_components/kaco/const.py

```

# Setup

All you need to have the ip adress of the inverter. This is show on the actual device display.

## Configuration options

Key | Type | Required | Default | Description
-- | -- | -- | -- | --
`url` | `string` | `true` | `None` | The IP of the inverter, e.g. 192.168.2.194
`name` | `string` | `false` | `kaco` |  The friendly name of the sensor
`kwh_interval` | `int` | `false` | `120` |  The interval of the kwh update
`interval` | `int` | `false` | `20` |  The interval of all other updates (my inverter crashes if I set it below 5 for more than a day)
`icon` | `string` | `false` | `mdi:weather-sunny` | MDI Icon string, check https://materialdesignicons.com/

## GUI configuration

Config flow is supported and is the prefered way to setup the integration. (No need to restart Home-Assistant)

## Manual configuration

To enable the sensor, add the following lines to your `configuration.yaml` file and replace the link accordingly:

```yaml
# Example entry for configuration.yaml
sensor:
  - platform: kaco
    name: Solar Power
    url: 192.168.2.194
 ```

# Codebase
Manny thanks to [KoljaWindeler](https://github.com/KoljaWindeler) how programmed the base of this integration.