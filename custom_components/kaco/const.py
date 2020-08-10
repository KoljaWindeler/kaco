from homeassistant.components.sensor import PLATFORM_SCHEMA, ENTITY_ID_FORMAT
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
import requests
import traceback
import logging
import datetime
from collections import OrderedDict


_LOGGER = logging.getLogger(__name__)


t = []
for i in range(0,168):
	t.append("")
t[0]="Initphase"
t[1]="Waiting for feed-in"
t[2]="Generator voltage too low"
t[3]="Constant volt. control"
t[4]="Feed-in mode"
t[5]=""
t[6]=""
t[7]="Self test in progress"
t[8]="Self test in progress"
t[9]="Test mode"
t[10]="Temperature in unit too high"
t[11]="Power limitation"
t[12]=""
t[13]=""
t[14]=""
t[15]=""
t[16]=""
t[17]="Powador-protect disconnection"
t[18]="Resid. current shutdown (AFI)"
t[19]="Generator insulation fault"
t[20]="Power rampup active"
t[21]="Protect. shutdown overcurrent DC1"
t[22]="Protect. shutdown overcurrent DC2"
t[23]="Protect. shutdown overcurrent DC3"
t[24]=""
t[25]=""
t[26]=""
t[27]=""
t[28]=""
t[29]="Check ground fault fuse"
t[30]="Voltage trans. fault"
t[31]="RCD module error"
t[32]="Self test error"
t[33]="DC feed-in error"
t[34]="Internal communication error"
t[35]="Protect. shutdown SW"
t[36]="Protect. shutdown HW"
t[37]="Unknown Hardware"
t[38]="Error: Generator Voltage too high"
t[39]=""
t[40]=""
t[41]="Line failure: undervoltage L1"
t[42]="Line failure: overvoltage L1"
t[43]="Line failure: undervoltage L2"
t[44]="Line failure: overvoltage L2"
t[45]="Line failure: undervoltage L3"
t[46]="Line failure: overvoltage L3"
t[47]="Line failure: line-to-line voltage"
t[48]="Line failure: underfreqency"
t[49]="Line failure: overfrequency"
t[50]="Line failure: average voltage"
t[51]="Line failure: middle overvoltage L1"
t[52]="Line failure: middle undervoltage L1"
t[53]="Line failure: middle overvoltage L2"
t[54]="Line failure: middle undervoltage L2"
t[55]="DC link voltage error"
t[56]="SPI Shutdown"
t[57]="Waiting for reactivation"
t[58]="Control board overtemperature"
t[59]="Self test error"
t[60]="Generator voltage too high"
t[61]="External limit"
t[62]="Standalone mode"
t[63]="Power reduction P(f)"
t[64]="Output current limiting"
t[65]="ROCOF error"
t[66]=""
t[67]="Power section 1 error"
t[68]="Power section 2 error"
t[69]="Power section 3 error"
t[70]="Fan 1 error"
t[71]="Fan 2 error"
t[72]="Fan 3 error"
t[73]="Grid failure: Islanding"
t[74]="External reactive power request"
t[75]="Self test in progress"
t[76]=""
t[77]=""
t[78]="Resid. current shutdown (AFI)"
t[79]="Insulation measurement"
t[80]="Insulation meas. not possible"
t[81]="Protect. shutdown grid voltage L1"
t[82]="Protect. shutdown grid voltage L2"
t[83]="Protect. shutdown grid voltage L3"
t[84]="Protect. shutdown overv. DC link"
t[85]="Protect. shutdown underv. DC link"
t[86]="Protect. shutdown unbal. DC link"
t[87]="Protect. shutdown overcurrent L1"
t[88]="Protect. shutdown overcurrent L2"
t[89]="Protect. shutdown overcurrent L3"
t[90]="Protect. shutdown voltage drop 5V"
t[91]="Protect. shutdown voltage drop 2.5V"
t[92]="Protect. shutdown voltage drop 1.5V"
t[93]="Self test error buffer 1"
t[94]="Self test error buffer 2"
t[95]="Self test error relay 1"
t[96]="Self test error relay 2"
t[97]="Protect. shutdown HW overcurrent"
t[98]="Protect. shutdown HW gate driver"
t[99]="Protect. shutdown HW buffer-enable"
t[100]="Protect. shutdown HW overtemperature"
t[101]="Plausibility fault temperature"
t[102]="Plausibility fault efficiency"
t[103]="Plausibility fault DC link"
t[104]="Plausibility fault RCD module"
t[105]="Plausibility fault relay"
t[106]="Plausibility fault DCDC converter"
t[107]=""
t[108]="Line failure: overvoltage L1"
t[109]="Line failure: overvoltage L2"
t[110]="Line failure: overvoltage L3"
t[111]="Line failure: undervoltage L1"
t[112]="Line failure: undervoltage L2"
t[113]="Line failure: undervoltage L3"
t[114]="Communication error DC/DC"
t[115]="Negative DC current 1"
t[116]="Negative DC current 2"
t[117]="Negative DC current 3"
t[118]="DC overvoltage 1"
t[119]="DC overvoltage 2"
t[120]="DC overvoltage 3"
t[121]="Door opened"
t[122]=""
t[123]=""
t[124]=""
t[125]="Error relay control"
t[126]="Error RCD measurement"
t[127]="Error AC voltage measurement"
t[128]="Error internal memory 1"
t[129]="Power reduction P(U)"
t[130]="Self-test error AFCI module"
t[131]="Arc detected on DC1"
t[132]="Arc detected on DC2"
t[133]="Arc detected on DC3"
t[134]="AFCI power supply critical"
t[135]="Internal AFCI ADC failed"
t[136]="AFCI algorithm failed"
t[137]="Error internal memory 1"
t[138]="AFCI parameters corrupted"
t[139]="Error external memory 1"
t[140]="Not enough AFCI DC inputs"
t[141]="Error controller output pin"
t[142]="AFCI activation failed"
t[143]=""
t[144]=""
t[145]=""
t[146]=""
t[147]=""
t[148]="Error external memory 1"
t[149]="Communication error AFCI module"
t[150]="Protect. shutdown voltage drop 1.65V"
t[151]="Input current limitation DC1"
t[152]="Input current limitation DC2"
t[153]="Input current limitation DC3"
t[154]="Input power limitation DC1"
t[155]="Input power limitation DC2"
t[156]="Input power limitation DC3"
t[157]=""
t[158]=""
t[159]=""
t[160]="Failure: Grid relay L1"
t[161]="Failure: Grid relay L2"
t[162]="Failure: Grid relay L3"
t[163]="Failure: Grid relay N"
t[164]="Failure: Filter relay L1"
t[165]="Failure: Filter relay L2"
t[166]="Failure: Filter relay L3"
t[167]="Failure: Filter relay N"


# generals
DOMAIN = "kaco"
PLATFORM = "sensor"
VERSION = "0.1.0"
ISSUE_URL = "https://github.com/koljawindeler/kaco/issues"
SCAN_INTERVAL = datetime.timedelta(seconds=5)

# configuration
CONF_ICON = "icon"
CONF_KACO_URL = "url"
CONF_NAME = "name"
CONF_KWH_INTERVAL = "kwh_interval"
CONF_INTERVAL = "interval"

# defaults
DEFAULT_ICON = 'mdi:sun'
DEFAULT_NAME = "kaco"
DEFAULT_KWH_INTERVAL = "120"
DEFAULT_INTERVAL = "20"

# error
ERROR_URL = "url_error"

# extend schema to load via YAML
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
	vol.Required(CONF_KACO_URL): cv.string,
	vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
	vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
	vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.Coerce(int),
	vol.Optional(CONF_KWH_INTERVAL, default=DEFAULT_KWH_INTERVAL): vol.Coerce(int),
})



def check_data(user_input):
	"""Check validity of the provided date."""
	ret = {}
	if(CONF_KACO_URL in user_input):
		try:
			url = "http://"+user_input[CONF_KACO_URL]+"/realtime.csv"
			ret = requests.get(url).content
			return {}
		except Exception:
			ret["base"] = ERROR_URL
			return ret

def ensure_config(user_input):
	"""Make sure that needed Parameter exist and are filled with default if not."""
	out = {}
	out[CONF_NAME] = ""
	out[CONF_KACO_URL] = ""
	out[CONF_ICON] = DEFAULT_ICON
	out[CONF_INTERVAL] = DEFAULT_INTERVAL
	out[CONF_KWH_INTERVAL] = DEFAULT_KWH_INTERVAL

	if user_input is not None:
		if CONF_NAME in user_input:
			out[CONF_NAME] = user_input[CONF_NAME]
		if CONF_KACO_URL in user_input:
			out[CONF_KACO_URL] = user_input[CONF_KACO_URL]
		if CONF_ICON in user_input:
			out[CONF_ICON] = user_input[CONF_ICON]
		if CONF_INTERVAL in user_input:
			out[CONF_INTERVAL] = user_input[CONF_INTERVAL]
		if CONF_KWH_INTERVAL in user_input:
			out[CONF_KWH_INTERVAL] = user_input[CONF_KWH_INTERVAL]
	return out


def create_form(user_input):
	"""Create form for UI setup."""
	user_input = ensure_config(user_input)

	data_schema = OrderedDict()
	data_schema[vol.Required(CONF_NAME, default=user_input[CONF_NAME])] = str
	data_schema[vol.Required(CONF_KACO_URL, default=user_input[CONF_KACO_URL])] = str
	data_schema[vol.Optional(CONF_ICON, default=user_input[CONF_ICON])] = str
	data_schema[vol.Optional(CONF_INTERVAL, default=user_input[CONF_INTERVAL])] = vol.Coerce(int)
	data_schema[vol.Optional(CONF_KWH_INTERVAL, default=user_input[CONF_KWH_INTERVAL])] = vol.Coerce(int)

	return data_schema
