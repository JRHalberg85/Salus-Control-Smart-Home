"""Support for binary (door/window/smoke/leak) sensors."""

from datetime import timedelta
import logging
import async_timeout

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorEntity
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import CONF_HOST, CONF_TOKEN

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): cv.string,
    }
)

async def async_update_data(gateway):
    """Fetch data from the API endpoint and update binary sensor devices."""
    retries = 3
    for attempt in range(retries):
        try:
            async with async_timeout.timeout(10):
                await gateway.poll_status()
                devices = gateway.get_binary_sensor_devices()
                _LOGGER.debug(f"Devices fetched: {devices}")

                valid_devices = []
                for device in devices.values():
                    _LOGGER.debug(f"Device data: {device}")
                    if device.available:
                        valid_devices.append(device)
                    else:
                        _LOGGER.warning(f"Device {device.unique_id} is not available.")

                if not valid_devices:
                    _LOGGER.error("No available devices found from the gateway.")
                    return [] 

                return valid_devices 

        except asyncio.TimeoutError:
            _LOGGER.error(f"Request timed out on attempt {attempt + 1}. Retrying...")
        except Exception as e:
            _LOGGER.error(f"Error fetching data on attempt {attempt + 1}: {e}")
        
        if attempt < retries - 1:
            await asyncio.sleep(5)

    _LOGGER.error("Max retries reached, data fetch failed.")
    return []

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Salus binary sensors from a config entry."""
    gateway = hass.data[DOMAIN][config_entry.entry_id] 
    
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="sensor",
        update_method=lambda: async_update_data(gateway),  
        update_interval=timedelta(seconds=10),
    )

    await coordinator.async_refresh()

    if coordinator.data is None:
        _LOGGER.error("Coordinator data is None, cannot set up sensors.")
        return

    valid_devices = [
        SalusBinarySensor(coordinator, device, gateway)
        for device in coordinator.data
        if device.available
    ]

    async_add_entities(valid_devices)

    for device in valid_devices:
        _LOGGER.debug(f"Adding sensor: {device.name}, Unique ID: {device.unique_id}")



class SalusBinarySensor(BinarySensorEntity):
    """Representation of a binary sensor."""

    def __init__(self, coordinator, device, gateway):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._device = device
        self.gateway = gateway

    async def async_update(self):
        """Update the entity."""
        await self._coordinator.async_request_refresh()

    @property
    def available(self):
        """Return if entity is available."""
        return self._device.available

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "name": self._device.name,
            "identifiers": {(DOMAIN, self._device.unique_id)},
            "manufacturer": self._device.manufacturer,
            "model": self._device.model,
            "sw_version": self._device.sw_version,
        }

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._device.unique_id

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self._device.is_on

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device.device_class

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._device.name
    
    @property
    def icon(self):
        """Return the icon to use in the frontend based on the state."""
        if self.is_on: 
            return "mdi:valve-open"  
        else:  
            return "mdi:valve-closed"
