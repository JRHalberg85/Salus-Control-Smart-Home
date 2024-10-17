"""Support for climate devices (thermostats)."""
from datetime import timedelta

import logging
import async_timeout
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import DOMAIN
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_TOKEN
)

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): cv.string,
    }
)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Salus thermostats from a config entry."""

    gateway = hass.data[DOMAIN][config_entry.entry_id]

    async def async_update_data():
        """Fetch data from the API endpoint and update climate devices."""
        try:
            async with async_timeout.timeout(30):
                await gateway.poll_status()
                devices = gateway.get_climate_devices()
                _LOGGER.debug(f"Devices fetched: {devices}")
                return devices
        except Exception as e:
            _LOGGER.error(f"Error fetching data: {e}")
            raise

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sensor",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_refresh()

    async_add_entities(
        SalusThermostat(coordinator, idx, gateway) 
        for idx in coordinator.data
    )

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    pass

class SalusThermostat(ClimateEntity):
    """Representation of a Salus Thermostat."""

    def __init__(self, coordinator, idx, gateway):
        """Initialize the thermostat."""
        self._coordinator = coordinator
        self._idx = idx
        self._gateway = gateway

    async def async_update(self):
        """Update the entity."""
        await self._coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )

    @property
    def supported_features(self):
        """Return the list of supported features."""
        features = ClimateEntityFeature.TARGET_TEMPERATURE
        
        hvac_modes = self._coordinator.data.get(self._idx).hvac_modes
        if HVACMode.OFF in hvac_modes or HVACMode.HEAT in hvac_modes or HVACMode.AUTO in hvac_modes:
            features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        
        if self.preset_modes:
            features |= ClimateEntityFeature.PRESET_MODE
        
        if self.fan_modes:
            features |= ClimateEntityFeature.FAN_MODE
        
        return features

    @property
    def available(self):
        """Return if entity is available."""
        return self._coordinator.data.get(self._idx).available
    
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:contrast-box"
    
    @property
    def device_info(self):
        """Return the device info."""
        device = self._coordinator.data.get(self._idx)
        return {
            "name": device.name,
            "identifiers": {("salus", device.unique_id)},
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.sw_version
        }

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._coordinator.data.get(self._idx).unique_id

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._coordinator.data.get(self._idx).name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._coordinator.data.get(self._idx).temperature_unit

    @property
    def precision(self):
        """Return the precision of the system."""
        return self._coordinator.data.get(self._idx).precision

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._coordinator.data.get(self._idx).current_temperature

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._coordinator.data.get(self._idx).current_humidity

    @property
    def hvac_mode(self):
        """Return the current operation mode."""
        return self._coordinator.data.get(self._idx).hvac_mode

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._coordinator.data.get(self._idx).hvac_modes

    @property
    def hvac_action(self):
        """Return the current HVAC action."""
        return self._coordinator.data.get(self._idx).hvac_action

    @property
    def target_temperature(self):
        """Return the temperature setpoint."""
        return self._coordinator.data.get(self._idx).target_temperature

    @property
    def max_temp(self):
        return self._coordinator.data.get(self._idx).max_temp

    @property
    def min_temp(self):
        return self._coordinator.data.get(self._idx).min_temp

    @property
    def preset_mode(self):
        return self._coordinator.data.get(self._idx).preset_mode

    @property
    def preset_modes(self):
        return self._coordinator.data.get(self._idx).preset_modes

    @property
    def fan_mode(self):
        return self._coordinator.data.get(self._idx).fan_mode

    @property
    def fan_modes(self):
        return self._coordinator.data.get(self._idx).fan_modes

    @property
    def locked(self):
        return self._coordinator.data.get(self._idx).locked

    async def async_set_temperature(self, **kwargs):
        """Set a new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._gateway.set_climate_device_temperature(self._device, temperature)
        await self._coordinator.async_request_refresh()

    async def async_set_fan_mode(self, fan_mode):
        """Set fan mode (auto, low, medium, high, off)."""
        await self._gateway.set_climate_device_fan_mode(self._device, fan_mode)
        await self._coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode):
        """Set the HVAC mode (auto, heat, cool)."""
        await self._gateway.set_climate_device_mode(self._device, hvac_mode)
        await self._coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode):
        """Set the preset mode."""
        await self._gateway.set_climate_device_preset(self._device, preset_mode)
        await self._coordinator.async_request_refresh()
