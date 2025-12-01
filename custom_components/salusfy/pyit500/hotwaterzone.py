"""Module to provide the HotWaterZone class"""
from .zone import Zone, ZoneAttribute, ScheduleType, OnOffStatus
from .enumfriendly import IntEnumFriendly


class Mode(IntEnumFriendly):
    """Enum for Hot Water Modes."""

    AUTO = 0
    ONCE = 1
    ON = 2
    OFF = 3


class RunningMode(IntEnumFriendly):
    """Enum for Hot Water Running Mode"""

    AUTO = 0
    MANUAL = 1


class HotWaterZone(Zone):
    """Class that represents a Hot Water zone of Device in the Salus iT500 API."""

    @property
    def mode(self) -> Mode:
        """Return the Zone's mode."""
        return Mode(int(self.get_attr(ZoneAttribute.HW_MODE)))

    async def async_set_mode(self, value: Mode):
        """Set the Zone's mode."""
        return await self.async_set_attr(ZoneAttribute.HW_MODE, value.value)

    @property
    def boost_remaining_hours(self) -> int:
        """Return the Zone's boost remaining hours."""
        return int(self.get_attr(ZoneAttribute.HW_BOOST_REMAINING_HOURS))

    @property
    def schedule_type(self) -> ScheduleType:
        """Return the Zone's schedule type."""
        return ScheduleType(int(self.get_attr(ZoneAttribute.HW_SCHEDULE_TYPE)))

    @property
    def on_off_status(self) -> OnOffStatus:
        """Return the Zone's on/off status type."""
        return OnOffStatus(int(self.get_attr(ZoneAttribute.HW_ON_OFF_STATUS)))

    @property
    def running_mode(self) -> RunningMode:
        """Return the Zone's running mode type."""
        return RunningMode(int(self.get_attr(ZoneAttribute.HW_RUNNING_MANUAL_MODE)))
