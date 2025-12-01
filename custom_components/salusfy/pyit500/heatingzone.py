"""Module to provide the HeatingZone class"""
from .zone import Zone, ZoneAttribute, ScheduleType, ActiveStatus, OnOffStatus
from .enumfriendly import EnumFriendly, IntEnumFriendly


class AutoTempHoldMode(IntEnumFriendly):
    """Enum for auto/temp hold mode."""

    AUTO = 0
    TEMP_HOLD = 1


class ConsolidatedMode(EnumFriendly):
    """Enum for consolidated heating mode.
    Value is a tuple representing (ch_off_mode, ch_manual_mode, ch_auto_temp_hold_mode)."""

    OFF = (1, 0, 0)
    MANUAL = (0, 1, 0)
    TEMP_HOLD = (0, 0, 1)
    AUTO = (0, 0, 0)
    UNKNOWN = (1, 1, 1)


class HeatingZone(Zone):
    """Class that represents a Heating zone of Device in the Salus iT500 API."""

    @property
    def current_room_temp(self) -> float:
        """Return the Zone's current room temperature, in C."""
        return int(self.get_attr(ZoneAttribute.CH_CURRENT_ROOM_TEMPERATURE)) / 100

    @property
    def current_setpoint(self) -> float:
        """Return the Zone's current setpoint, in C."""
        return int(self.get_attr(ZoneAttribute.CH_CURRENT_SETPOINT)) / 100

    async def async_set_current_setpoint(self, value: float) -> int:
        """Set the Zone's current setpoint, in C.
        The API will change the mode if required."""
        return await self.async_set_attr(ZoneAttribute.CH_CURRENT_SETPOINT, int(value * 100))

    @property
    def schedule_type(self) -> ScheduleType:
        """Return the Zone's schedule type."""
        return ScheduleType(int(self.get_attr(ZoneAttribute.CH_SCHEDULE_TYPE)))

    @property
    def relay_status(self) -> OnOffStatus:
        """Return the Zone's relay status type."""
        return OnOffStatus(int(self.get_attr(ZoneAttribute.CH_RELAY_ON_OFF_STATUS)))

    @property
    def auto_temp_hold_mode(self) -> AutoTempHoldMode:
        """Return the Zone's auto mode / temp hold mode."""
        return AutoTempHoldMode(
            int(self.get_attr(ZoneAttribute.CH_AUTO_TEMP_HOLD_MODE))
        )

    async def async_set_auto_temp_hold_mode(self, value: AutoTempHoldMode):
        """Set the Zone's auto mode / temp hold mode."""
        return await self.async_set_attr(ZoneAttribute.CH_AUTO_TEMP_HOLD_MODE, value)

    @property
    def off_mode(self) -> ActiveStatus:
        """Return the Zone's off mode."""
        return ActiveStatus(int(self.get_attr(ZoneAttribute.CH_OFF_MODE)))

    async def async_set_off_mode(self, value: ActiveStatus):
        """Set the Zone's off mode.
        Note: Active = Zone is Off, Inactive = Zone is in some other mode."""
        return await self.async_set_attr(ZoneAttribute.CH_OFF_MODE, value)

    @property
    def frost_active(self) -> ActiveStatus:
        """Return the Zone's frost active state."""
        return ActiveStatus(int(self.get_attr(ZoneAttribute.CH_FROST_ACTIVE)))

    @property
    def boost_remaining_hours(self) -> int:
        """Return the Zone's boost remaining house."""
        return int(self.get_attr(ZoneAttribute.CH_BOOST_REMAINING_HOURS))

    @property
    def manual_mode(self) -> ActiveStatus:
        """Return the Zone's manual mode."""
        return ActiveStatus(int(self.get_attr(ZoneAttribute.CH_MANUAL_MODE)))

    async def async_set_manual_mode(self, value: ActiveStatus):
        """Set the Zone's manual mode."""
        return await self.async_set_attr(ZoneAttribute.CH_MANUAL_MODE, value)

    @property
    def manual_mode_setpoint(self) -> float:
        """Return the Zone's manual mode setpoint, in C."""
        return int(self.get_attr(ZoneAttribute.CH_MANUAL_MODE_SETPOINT)) / 100

    async def async_set_manual_mode_setpoint(self, value: float) -> int:
        """Set the Zone's manual mode setpoint, in C."""
        return await self.async_set_attr(
            ZoneAttribute.CH_MANUAL_MODE_SETPOINT, int(value * 100)
        )

    @property
    def auto_mode_setpoint(self) -> float:
        """Return the Zone's auto mode setpoint, in C."""
        return int(self.get_attr(ZoneAttribute.CH_AUTO_MODE_SETPOINT)) / 100

    async def async_set_auto_mode_setpoint(self, value: float) -> int:
        """Set the Zone's auto mode setpoint, in C."""
        return await self.async_set_attr(
            ZoneAttribute.CH_AUTO_MODE_SETPOINT, int(value * 100)
        )

    @property
    def consolidated_mode(self) -> ConsolidatedMode:
        """Return the Zone's consolidated heating mode."""
        try:
            return ConsolidatedMode(
                (self.off_mode, self.manual_mode, self.auto_temp_hold_mode)
            )
        except ValueError:
            return ConsolidatedMode.UNKNOWN

    async def async_set_consolidated_mode(self, value: ConsolidatedMode):
        """Set the Zone's consolidated heating mode.
        This will update the off, manual and auto temp hold mode accordingly.

        Note: Salus API sometimes has issues with multiple attribute changes.
        We set them one by one to avoid API errors."""
        off_mode, manual_mode, auto_temp_hold_mode = value.value

        # Set attributes one by one instead of all at once
        # This avoids API 500 errors that occur with multiple simultaneous changes
        if off_mode != self.off_mode:
            await self.async_set_attr(ZoneAttribute.CH_OFF_MODE, off_mode)

        if manual_mode != self.manual_mode:
            await self.async_set_attr(ZoneAttribute.CH_MANUAL_MODE, manual_mode)

        if auto_temp_hold_mode != self.auto_temp_hold_mode:
            await self.async_set_attr(ZoneAttribute.CH_AUTO_TEMP_HOLD_MODE, auto_temp_hold_mode)

        return 0  # Return success
