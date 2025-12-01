"""Module to provide the Zone base class"""
from typing import Any, TYPE_CHECKING
from .enumfriendly import EnumFriendly, IntEnumFriendly

if TYPE_CHECKING:
    from .device import Device


class Prefix(EnumFriendly):
    """Enum for heating and hot water zones."""

    CH1 = "A"
    CH2 = "B"
    HW = "C"


class ZoneAttribute(EnumFriendly):
    """Enum for code part of Device attribute names"""

    PROGRAM_MON = "00"
    PROGRAM_TUE = "01"
    PROGRAM_WED = "02"
    PROGRAM_THU = "03"
    PROGRAM_FRI = "04"
    PROGRAM_SAT = "05"
    PROGRAM_SUN = "06"
    HW_MODE = "42"
    HW_BOOST_REMAINING_HOURS = "43"
    HW_SCHEDULE_TYPE = "44"
    HW_ON_OFF_STATUS = "45"
    HW_RUNNING_MANUAL_MODE = "46"
    CH_CURRENT_ROOM_TEMPERATURE = "84"
    CH_CURRENT_SETPOINT = "85"
    CH_SCHEDULE_TYPE = "86"
    CH_RELAY_ON_OFF_STATUS = "87"
    CH_AUTO_TEMP_HOLD_MODE = "88"
    CH_OFF_MODE = "89"
    CH_FROST_ACTIVE = "90"
    CH_BOOST_REMAINING_HOURS = "91"
    CH_MANUAL_MODE = "92"
    CH_MANUAL_MODE_SETPOINT = "93"
    CH_AUTO_MODE_SETPOINT = "94"


class ScheduleType(IntEnumFriendly):
    """Enum for Device schedule types."""

    ALL = 0
    FIVE_TWO = 1
    INDEPENDENT = 2


class OnOffStatus(IntEnumFriendly):
    """Enum for Device modes that can be on/off"""

    OFF = 0
    ON = 1


class ActiveStatus(IntEnumFriendly):
    """Enum for Device modes that can be active/inactive."""

    INACTIVE = 0
    ACTIVE = 1


class Zone:
    """Base class that represents a generic Zone of a Device in the Salus iT500 API."""

    def __init__(self, device: "Device", zone_prefix: Prefix) -> None:
        self.zone_prefix = zone_prefix.value
        self.device = device

    def get_attr(self, attr: ZoneAttribute) -> Any:
        """Returns an attribute for this zone from the parent device raw data."""
        return self.device.get_raw_attr(self.zone_prefix + attr.value)

    async def async_set_attr(
        self,
        attr1: ZoneAttribute = None,
        attr1_value: Any = None,
        attr2: ZoneAttribute = None,
        attr2_value: Any = None,
        attr3: ZoneAttribute = None,
        attr3_value: Any = None,
    ) -> int:
        """Sets an attribute for this zone by setting it on the parent device."""
        attr1 = self.zone_prefix + attr1.value
        if attr2 is not None:
            attr2 = self.zone_prefix + attr2.value
        if attr3 is not None:
            attr3 = self.zone_prefix + attr3.value

        return await self.device.async_control(
            attr1, attr1_value, attr2, attr2_value, attr3, attr3_value
        )

    @property
    def program_mon(self) -> str:
        """Return the zone's program for Monday, as a proprietary string"""
        return str(self.get_attr(ZoneAttribute.PROGRAM_MON))

    @property
    def program_tue(self) -> str:
        """Return the zone's program for Tuesday, as a proprietary string"""
        return str(self.get_attr(ZoneAttribute.PROGRAM_TUE))

    @property
    def program_wed(self) -> str:
        """Return the zone's program for Wednesday, as a proprietary string"""
        return str(self.get_attr(ZoneAttribute.PROGRAM_WED))

    @property
    def program_thu(self) -> str:
        """Return the zone's program for Thursday, as a proprietary string"""
        return str(self.get_attr(ZoneAttribute.PROGRAM_THU))

    @property
    def program_fri(self) -> str:
        """Return the zone's program for Friday, as a proprietary string"""
        return str(self.get_attr(ZoneAttribute.PROGRAM_FRI))

    @property
    def program_sat(self) -> str:
        """Return the zone's program for Saturday, as a proprietary string"""
        return str(self.get_attr(ZoneAttribute.PROGRAM_SAT))

    @property
    def program_sun(self) -> str:
        """Return the zone's program for Sunday, as a proprietary string"""
        return str(self.get_attr(ZoneAttribute.PROGRAM_SUN))
