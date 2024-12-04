"""Support for Salus iT600."""
import logging
import time
from asyncio import sleep

from homeassistant import config_entries, core
from homeassistant.helpers import device_registry as dr

from homeassistant.const import (
    CONF_HOST,
    CONF_TOKEN
)

from pyit600.exceptions import IT600AuthenticationError, IT600ConnectionError
from pyit600.gateway import IT600Gateway

from .config_flow import CONF_FLOW_TYPE, CONF_USER
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

GATEWAY_PLATFORMS = ["climate", "binary_sensor"] #, "switch", "cover", "sensor"


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Salus iT600 component."""
    return True


async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up components from a config entry."""
    hass.data[DOMAIN] = {}
    if entry.data[CONF_FLOW_TYPE] == CONF_USER:
        if not await async_setup_gateway_entry(hass, entry):
            return False

    return True

async def async_setup_gateway_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up the Gateway component from a config entry."""
    host = entry.data[CONF_HOST]
    euid = entry.data[CONF_TOKEN]

    # Connect to gateway
    gateway = IT600Gateway(host=host, euid=euid)
    try:
        for remaining_attempts in reversed(range(3)):
            try:
                await gateway.connect()
                
                # Tilføj logik til poll_status
                import time
                start_time = time.time()
                await gateway.poll_status()
                _LOGGER.info(f"Polling completed in {time.time() - start_time} seconds")
                break
            except Exception as e:
                if remaining_attempts == 0:
                    _LOGGER.error(f"Connection failed after {time.time() - start_time} seconds: {e}")
                    raise e
                else:
                    _LOGGER.warning(f"Retrying connection ({3 - remaining_attempts}/3)...")
                    await sleep(3)
    except IT600ConnectionError:
        _LOGGER.error("Connection error: check if you have specified gateway's HOST correctly.")
        return False
    except IT600AuthenticationError:
        _LOGGER.error("Authentication error: check if you have specified gateway's EUID correctly.")
        return False

    # Brug poll_status som indikator for forbindelsen
    try:
        await gateway.poll_status()
        _LOGGER.info("Gateway connected successfully.")
    except IT600ConnectionError:
        _LOGGER.warning("Gateway not connected. Integration set up in limited mode.")
        hass.data[DOMAIN][entry.entry_id] = None
        return True

    hass.data[DOMAIN][entry.entry_id] = gateway

    gateway_info = gateway.get_gateway_device()

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, gateway_info.unique_id)},
        identifiers={(DOMAIN, gateway_info.unique_id)},
        manufacturer=gateway_info.manufacturer,
        name=gateway_info.name,
        model=gateway_info.model,
        sw_version=gateway_info.sw_version,
    )

    for component in GATEWAY_PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, [component])

    return True
