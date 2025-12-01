"""Support for Salus iT500 climate devices."""
import asyncio
import logging

from aiohttp import ClientResponseError

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SalusDataCoordinator
from .const import DOMAIN
from .pyit500.heatingzone import ConsolidatedMode, HeatingZone
from .pyit500.zone import OnOffStatus, Prefix
from .pyit500.device import SystemType, TemperatureUnit

_LOGGER = logging.getLogger(__name__)

# Preset modes mapping to ConsolidatedMode
PRESET_AUTO = "auto"
PRESET_MANUAL = "manual"
PRESET_TEMP_HOLD = "temp_hold"

PRESET_MODES = [PRESET_AUTO, PRESET_MANUAL, PRESET_TEMP_HOLD]

# Mapping between HA HVAC modes and Salus modes
HVAC_MODE_TO_SALUS = {
    HVACMode.OFF: ConsolidatedMode.OFF,
    HVACMode.HEAT: ConsolidatedMode.AUTO,
}

SALUS_MODE_TO_HVAC = {
    ConsolidatedMode.OFF: HVACMode.OFF,
    ConsolidatedMode.AUTO: HVACMode.HEAT,
    ConsolidatedMode.MANUAL: HVACMode.HEAT,
    ConsolidatedMode.TEMP_HOLD: HVACMode.HEAT,
}

SALUS_MODE_TO_PRESET = {
    ConsolidatedMode.AUTO: PRESET_AUTO,
    ConsolidatedMode.MANUAL: PRESET_MANUAL,
    ConsolidatedMode.TEMP_HOLD: PRESET_TEMP_HOLD,
}

PRESET_TO_SALUS_MODE = {
    PRESET_AUTO: ConsolidatedMode.AUTO,
    PRESET_MANUAL: ConsolidatedMode.MANUAL,
    PRESET_TEMP_HOLD: ConsolidatedMode.TEMP_HOLD,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Salus climate entities from a config entry."""
    coordinator: SalusDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []

    # Always add CH1 (primary heating zone)
    entities.append(SalusThermostat(coordinator, Prefix.CH1, "Heating Zone 1"))

    # Add CH2 if system supports it
    if coordinator.device.system_type == SystemType.CH1_CH2:
        entities.append(SalusThermostat(coordinator, Prefix.CH2, "Heating Zone 2"))

    async_add_entities(entities)


class SalusThermostat(CoordinatorEntity[SalusDataCoordinator], ClimateEntity):
    """Representation of a Salus thermostat."""

    _attr_has_entity_name = False  # We set full name including device name
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_preset_modes = PRESET_MODES

    def __init__(
        self,
        coordinator: SalusDataCoordinator,
        zone_prefix: Prefix,
        name: str,
    ) -> None:
        """Initialize the thermostat."""
        super().__init__(coordinator)
        self._zone_prefix = zone_prefix
        
        # Optimistic state for immediate UI updates
        self._optimistic_target_temp = None
        self._optimistic_hvac_mode = None
        self._optimistic_preset_mode = None

        # Set temperature unit based on device configuration
        if coordinator.device.temperature_unit == TemperatureUnit.FAHRENHEIT:
            self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
        else:
            self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        # Use device name as prefix for entity name
        device_name = coordinator.device.description or "Salus iT500"
        self._attr_name = f"{device_name} {name}"
        self._attr_unique_id = (
            f"{coordinator.device.device_id}_{zone_prefix.value}_climate"
        )

    @property
    def _zone(self) -> HeatingZone:
        """Return the heating zone for this thermostat."""
        if self._zone_prefix == Prefix.CH1:
            return self.coordinator.device.ch1
        return self.coordinator.device.ch2

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._zone.current_room_temp

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        # Use optimistic value if available, otherwise use actual value
        if self._optimistic_target_temp is not None:
            return self._optimistic_target_temp
        return self._zone.current_setpoint

    @property
    def hvac_mode(self) -> HVACMode:
        """Return hvac operation mode."""
        # Use optimistic value if available, otherwise use actual value
        if self._optimistic_hvac_mode is not None:
            return self._optimistic_hvac_mode
        mode = self._zone.consolidated_mode
        return SALUS_MODE_TO_HVAC.get(mode, HVACMode.OFF)

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current running hvac operation."""
        if self._zone.relay_status == OnOffStatus.ON:
            return HVACAction.HEATING
        if self._zone.consolidated_mode == ConsolidatedMode.OFF:
            return HVACAction.OFF
        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        # Use optimistic value if available, otherwise use actual value
        if self._optimistic_preset_mode is not None:
            return self._optimistic_preset_mode
        mode = self._zone.consolidated_mode
        return SALUS_MODE_TO_PRESET.get(mode)

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        if self._attr_temperature_unit == UnitOfTemperature.FAHRENHEIT:
            return 41.0  # 5°C in Fahrenheit
        return 5.0

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if self._attr_temperature_unit == UnitOfTemperature.FAHRENHEIT:
            return 95.0  # 35°C = 95°F
        return 35.0

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        # Set optimistic state for immediate UI feedback
        self._optimistic_target_temp = temperature
        self.async_write_ha_state()

        # Retry logic for transient API errors
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff
        
        try:
            for attempt in range(max_retries):
                try:
                    await self._zone.async_set_current_setpoint(temperature)
                    await self.coordinator.async_request_refresh()
                    return  # Success
                except ClientResponseError as err:
                    if err.status in (500, 502, 503, 504) and attempt < max_retries - 1:
                        # Transient server error, retry
                        delay = retry_delays[attempt]
                        _LOGGER.warning(
                            "API error setting temperature (attempt %d/%d), retrying in %ds: %s",
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
                            "Failed to set temperature to %s: API returned %s - %s",
                            temperature,
                            err.status,
                            err.message,
                        )
                        raise HomeAssistantError(
                            f"Failed to set temperature: API error {err.status}"
                        ) from err
        finally:
            # Clear optimistic state after all attempts complete
            self._optimistic_target_temp = None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        if hvac_mode not in HVAC_MODE_TO_SALUS:
            _LOGGER.error("Unsupported HVAC mode: %s", hvac_mode)
            return

        # Set optimistic state for immediate UI feedback
        self._optimistic_hvac_mode = hvac_mode
        salus_mode = HVAC_MODE_TO_SALUS[hvac_mode]
        # Also set preset mode optimistically
        self._optimistic_preset_mode = SALUS_MODE_TO_PRESET.get(salus_mode)
        self.async_write_ha_state()

        # Retry logic for transient API errors
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff
        
        try:
            for attempt in range(max_retries):
                try:
                    await self._zone.async_set_consolidated_mode(salus_mode)
                    await self.coordinator.async_request_refresh()
                    return  # Success
                except ClientResponseError as err:
                    if err.status in (500, 502, 503, 504) and attempt < max_retries - 1:
                        # Transient server error, retry
                        delay = retry_delays[attempt]
                        _LOGGER.warning(
                            "API error setting HVAC mode (attempt %d/%d), retrying in %ds: %s",
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
                            "Failed to set HVAC mode to %s: API returned %s - %s",
                            hvac_mode,
                            err.status,
                            err.message,
                        )
                        raise HomeAssistantError(
                            f"Failed to set HVAC mode: API error {err.status}"
                        ) from err
        finally:
            # Clear optimistic state after all attempts complete
            self._optimistic_hvac_mode = None
            self._optimistic_preset_mode = None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode not in PRESET_TO_SALUS_MODE:
            _LOGGER.error("Unsupported preset mode: %s", preset_mode)
            return

        # Set optimistic state for immediate UI feedback
        self._optimistic_preset_mode = preset_mode
        self.async_write_ha_state()

        salus_mode = PRESET_TO_SALUS_MODE[preset_mode]
        current_mode = self._zone.consolidated_mode

        # Retry logic for transient API errors
        max_retries = 3
        retry_delays = [1, 2, 4]  # Exponential backoff
        
        try:
            for attempt in range(max_retries):
                try:
                    # Workaround for Salus API quirk: Direct TEMP_HOLD → AUTO transition doesn't stick
                    # Need to go through MANUAL mode first to clear the temp_hold state
                    if current_mode == ConsolidatedMode.TEMP_HOLD and salus_mode == ConsolidatedMode.AUTO:
                        _LOGGER.debug("Switching from TEMP_HOLD to AUTO via MANUAL mode")
                        await self._zone.async_set_consolidated_mode(ConsolidatedMode.MANUAL)
                        # Small delay to let API process the manual mode change
                        await asyncio.sleep(0.5)

                    await self._zone.async_set_consolidated_mode(salus_mode)
                    await self.coordinator.async_request_refresh()
                    return  # Success
                except ClientResponseError as err:
                    if err.status in (500, 502, 503, 504) and attempt < max_retries - 1:
                        # Transient server error, retry
                        delay = retry_delays[attempt]
                        _LOGGER.warning(
                            "API error setting preset mode (attempt %d/%d), retrying in %ds: %s",
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
                            "Failed to set preset mode to %s: API returned %s - %s",
                            preset_mode,
                            err.status,
                            err.message,
                        )
                        raise HomeAssistantError(
                            f"Failed to set preset mode: API error {err.status}"
                        ) from err
        finally:
            # Clear optimistic state after all attempts complete
            self._optimistic_preset_mode = None

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        return {
            "frost_active": self._zone.frost_active.friendly_name,
            "schedule_type": self._zone.schedule_type.friendly_name,
        }
