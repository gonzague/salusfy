"""Module to provide the Device class"""
from typing import Any
from asyncio import sleep, create_task
import xmltodict
from .auth import Auth
from .zone import Prefix, OnOffStatus
from .heatingzone import HeatingZone
from .hotwaterzone import HotWaterZone
from .enumfriendly import EnumFriendly, IntEnumFriendly


class SystemAttribute(EnumFriendly):
    """Enum for system wide (rather than Zone) Device attribute names."""

    OTA_STATUS = "S00"
    ENERGY_SAVE_STATUS = "S01"
    UPGRADE_AVAILABLE = "S02"
    BATTERY_STATUS = "S03"
    TIME_ZONE = "S04"
    SYSTEM_MODE = "S05"
    SYSTEM_TYPE = "S06"
    TEMPERATURE_UNIT = "S07"
    HOUR_FORMAT = "S08"
    FROST_TEMPERATURE = "S09"
    HOLIDAY_OPTION = "S10"
    HOLIDAY_START = "S11"
    HOLIDAY_END = "S12"
    THERMOSTAT_MICROPROCESSOR_VERSION = "S13"
    DAYLIGHT_SAVING_TIME = "S14"
    SPAN = "S15"
    DISPLAY_TOLERANCE = "S16"
    DISPLAY_OFFSET = "S17"
    CH2_DISPLAY_OFFSET = "S18"
    DELAY_START_ENABLE = "S19"
    DESCRIPTION = "desc"


class SystemType(IntEnumFriendly):
    """Enum for Device System Type."""

    CH1 = 0
    CH1_CH2 = 1
    CH1_HOT_WATER = 2


class TemperatureUnit(IntEnumFriendly):
    """Enum for Temperature Unit."""

    CELSIUS = 0
    FAHRENHEIT = 1


class Device:
    """Class that represents a Device object in the Salus iT500 API."""

    # Constructor
    def __init__(self, device_id: int, raw_data: dict, auth: Auth):
        """Initialise a device object."""
        self._device_id = int(device_id)
        self.raw_data = raw_data
        self.auth = auth
        self.ch1 = HeatingZone(self, Prefix.CH1)
        self.ch2 = HeatingZone(self, Prefix.CH2)
        self.hw = HotWaterZone(self, Prefix.HW)

    # Device Class Methods
    @classmethod
    async def async_get_device(cls, auth, device_id) -> "Device":
        """Return a device."""
        device = Device(device_id, None, auth)
        await device.async_update()
        return device

    # Properties
    @property
    def device_id(self) -> int:
        """Return the ID of the device."""
        return self._device_id

    @property
    def system_type(self) -> SystemType:
        """Return the system type.
        (0 = CH1, 1 = CH1+CH2, 2 = CH1 + Hot Water)"""
        return SystemType(int(self.get_attr(SystemAttribute.SYSTEM_TYPE)))

    @property
    def temperature_unit(self) -> TemperatureUnit:
        """Return the temperature unit.
        (0 = Celsius, 1 = Fahrenheit)"""
        return TemperatureUnit(int(self.get_attr(SystemAttribute.TEMPERATURE_UNIT)))

    @property
    def frost_temperature(self) -> float:
        """Return the set frost temperature, in C."""
        return int(self.get_attr(SystemAttribute.FROST_TEMPERATURE)) / 100

    @property
    def holiday_option(self) -> OnOffStatus:
        """Return the Holiday option status."""
        return OnOffStatus(int(self.get_attr(SystemAttribute.HOLIDAY_OPTION)))

    async def async_set_holiday_option(self, value: OnOffStatus):
        """Set the Holiday option status."""
        return await self.async_set_attr(SystemAttribute.HOLIDAY_OPTION, value)

    @property
    def holiday_start(self) -> str:
        """Return the Holiday start date & time, as string (YYYYMMDDHHMM)."""
        return str(self.get_attr(SystemAttribute.HOLIDAY_START))

    async def async_set_holiday_start(self, value: str):
        """Set the Holiday start date & time, as string (YYYYMMDDHHMM)."""
        return await self.async_set_attr(SystemAttribute.HOLIDAY_START, value)

    @property
    def holiday_end(self) -> str:
        """Return the Holiday end date & time, as string."""
        return str(self.get_attr(SystemAttribute.HOLIDAY_END))

    async def async_set_holiday_end(self, value: str):
        """Set the Holiday end date & time, as string (YYYYMMDDHHMM)."""
        return await self.async_set_attr(SystemAttribute.HOLIDAY_END, value)

    @property
    def description(self) -> str:
        """Return the description of the system."""
        return str(self.get_attr(SystemAttribute.DESCRIPTION))

    def get_attr(self, attr: SystemAttribute) -> Any:
        """Return the value of an attribute in the System, based on the Device raw data."""
        return self.get_raw_attr(attr.value)

    async def async_set_attr(
        self,
        attr: SystemAttribute,
        attr_value: Any,
    ) -> int:
        """Sets an attribute for the system."""
        return await self.async_control(attr.value, attr_value)

    def get_raw_attr(self, attr) -> Any:
        """Return the value of an attribute in the Device raw data."""
        return self.raw_data["attrList:" + attr]["value"]

    async def async_control(
        self,
        attr1_name: str,
        attr1_value: str,
        attr2_name: str = None,
        attr2_value: str = None,
        attr3_name: str = None,
        attr3_value: str = None,
    ) -> int:
        """Control the device."""
        params = {"devId": self.device_id, "name1": attr1_name, "value1": attr1_value}
        if attr2_name is not None:
            params["name2"] = attr2_name
            params["value2"] = attr2_value
        if attr3_name is not None:
            params["name3"] = attr3_name
            params["value3"] = attr3_value

        resp = await self.auth.request(
            "get", "setMultiDeviceAttributes2", params=params
        )
        resp.raise_for_status()
        create_task(self.async_update(1))
        return int(
            xmltodict.parse(await resp.text(), xml_attribs=False)[
                "ns1:setMultiDeviceAttributes2Response"
            ]["retCode"]
        )

    async def async_update(self, delay=0):
        """Update the device data."""
        await sleep(delay)
        resp = await self.auth.request(
            "post", "getDeviceAttributesWithValues", data={"devId": self.device_id}
        )
        resp.raise_for_status()
        self.raw_data = xmltodict.parse(
            await resp.text(), xml_attribs=False, postprocessor=Device.xml_postprocessor
        )["ns1:getDeviceAttributesWithValuesResponse"]

    @staticmethod
    def xml_postprocessor(_path, key, value) -> tuple:
        """Called by xmltodict. Extracts the configurations and attrList key/value pairs."""
        if key == "configurations":
            return "configurations:" + value["property"], value
        if key == "attrList":
            return "attrList:" + value["name"], value
        return key, value
