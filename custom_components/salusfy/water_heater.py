"""Support for Salus iT500 water heater devices."""
import asyncio
import logging

from aiohttp import ClientResponseError

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SalusDataCoordinator
from .const import DOMAIN
from .pyit500.hotwaterzone import Mode as HotWaterMode, HotWaterZone
from .pyit500.zone import OnOffStatus
from .pyit500.device import SystemType

_LOGGER = logging.getLogger(__name__)

# Operation modes
OPERATION_AUTO = "auto"
OPERATION_ONCE = "boost"
OPERATION_ON = "on"
OPERATION_OFF = "off"

OPERATION_LIST = [OPERATION_AUTO, OPERATION_ONCE, OPERATION_ON, OPERATION_OFF]

# Mapping between HA operation modes and Salus modes
OPERATION_TO_SALUS = {
    OPERATION_AUTO: HotWaterMode.AUTO,
    OPERATION_ONCE: HotWaterMode.ONCE,
    OPERATION_ON: HotWaterMode.ON,
    OPERATION_OFF: HotWaterMode.OFF,
}

SALUS_TO_OPERATION = {
    HotWaterMode.AUTO: OPERATION_AUTO,
    HotWaterMode.ONCE: OPERATION_ONCE,
    HotWaterMode.ON: OPERATION_ON,
    HotWaterMode.OFF: OPERATION_OFF,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Salus water heater entities from a config entry."""
    coordinator: SalusDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Only add hot water if system supports it
    if coordinator.device.system_type == SystemType.CH1_HOT_WATER:
        entities.append(SalusWaterHeater(coordinator))

    if entities:
        async_add_entities(entities)


class SalusWaterHeater(CoordinatorEntity[SalusDataCoordinator], WaterHeaterEntity):
    """Representation of a Salus hot water heater."""

    _attr_has_entity_name = False  # We set full name including device name
    _attr_supported_features = WaterHeaterEntityFeature.OPERATION_MODE
    _attr_temperature_unit = None  # Water heater doesn't use temperature

    def __init__(self, coordinator: SalusDataCoordinator) -> None:
        """Initialize the water heater."""
        super().__init__(coordinator)
        
        # Optimistic state for immediate UI updates
        self._optimistic_operation_mode = None

        # Use device name as prefix for entity name
        device_name = coordinator.device.description or "Salus iT500"
        self._attr_name = f"{device_name} Teplá voda"

        self._attr_unique_id = f"{coordinator.device.device_id}_hw_water_heater"
        self._attr_operation_list = OPERATION_LIST
        self._attr_min_temp = None
        self._attr_max_temp = None

    @property
    def _zone(self) -> HotWaterZone:
        """Return the hot water zone."""
        return self.coordinator.device.hw

    @property
    def current_operation(self) -> str | None:
        """Return current operation mode."""
        # Use optimistic value if available, otherwise use actual value
        if self._optimistic_operation_mode is not None:
            return self._optimistic_operation_mode
        mode = self._zone.mode
        return SALUS_TO_OPERATION.get(mode)

    @property
    def state(self) -> str:
        """Return the current state based on operation mode."""
        # State should reflect operation mode, not just on/off status
        # This fixes the issue where "auto" mode shows as "on"
        operation = self.current_operation
        if operation == OPERATION_OFF:
            return STATE_OFF
        # For all other modes (auto, boost, on), return on
        return STATE_ON

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new operation mode."""
        if operation_mode not in OPERATION_TO_SALUS:
            _LOGGER.error("Unsupported operation mode: %s", operation_mode)
            return

        # Set optimistic state for immediate UI feedback
        self._optimistic_operation_mode = operation_mode
        self.async_write_ha_state()

        salus_mode = OPERATION_TO_SALUS[operation_mode]
        
        # Retry logic for transient API errors
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff
        
        try:
            for attempt in range(max_retries):
                try:
                    await self._zone.async_set_mode(salus_mode)

                    # Schedule refresh after delay to allow Salus API to process the change
                    # Salus API can take 10-30 seconds to update the state
                    await self.coordinator.async_request_refresh()
                    return  # Success
                except ClientResponseError as err:
                    if err.status in (500, 502, 503, 504) and attempt < max_retries - 1:
                        # Transient server error, retry
                        delay = retry_delays[attempt]
                        _LOGGER.warning(
                            "API error setting operation mode (attempt %d/%d), retrying in %ds: %s",
                            attempt + 1,
                            max_retries,
                            delay,
                            err,
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Non-retryable error or final attempt
                        _LOGGER.error(
                            "Failed to set operation mode to %s: API returned %s - %s",
                            operation_mode,
                            err.status,
                            err.message,
                        )
                        raise HomeAssistantError(
                            f"Failed to set operation mode: API error {err.status}"
                        ) from err
        finally:
            # Clear optimistic state after all attempts complete
            self._optimistic_operation_mode = None

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the water heater."""
        await self.async_set_operation_mode(OPERATION_ON)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the water heater."""
        await self.async_set_operation_mode(OPERATION_OFF)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        attrs = {
            "schedule_type": self._zone.schedule_type.friendly_name,
            "running_mode": self._zone.running_mode.friendly_name,
        }

        # Add boost remaining hours if in boost mode
        if self._zone.mode == HotWaterMode.ONCE:
            attrs["boost_remaining_hours"] = self._zone.boost_remaining_hours

        return attrs
