"""Support for acre Intrusion alarm systems."""
from __future__ import annotations

import logging
import asyncio

from pyspcwebgw import SpcWebGateway
from pyspcwebgw.area import Area
from pyspcwebgw.zone import Zone
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery, aiohttp_client  # Added aiohttp_client import
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    DATA_API,
    CONF_WS_URL,
    CONF_API_URL,
    SIGNAL_UPDATE_ALARM,
    SIGNAL_UPDATE_SENSOR,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.LOCK,
    Platform.SWITCH,
    Platform.CAMERA,
    Platform.EVENT,
]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_WS_URL): cv.string,
                vol.Required(CONF_API_URL): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the acre_intrusion component."""
    # Configuration through config flow is preferred
    if DOMAIN not in config:
        return True

    async def async_update_callback(spc_object):
        if isinstance(spc_object, Area):
            async_dispatcher_send(hass, SIGNAL_UPDATE_ALARM.format(spc_object.id))
        elif isinstance(spc_object, Zone):
            async_dispatcher_send(hass, SIGNAL_UPDATE_SENSOR.format(spc_object.id))

    session = aiohttp_client.async_get_clientsession(hass)
    domain_config = config.get(DOMAIN, {})

    spc = SpcWebGateway(
        loop=hass.loop,
        session=session,
        api_url=domain_config.get(CONF_API_URL),
        ws_url=domain_config.get(CONF_WS_URL),
        async_callback=async_update_callback,
    )

    # Only proceed with setup if we have configuration
    if not domain_config:
        return True

    hass.data[DATA_API] = spc

    if not await spc.async_load_parameters():
        _LOGGER.error("Failed to load area/zone information from acre_intrusion")
        return False

    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    spc.start()
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up acre Intrusion from a config entry."""
    async def async_update_callback(spc_object):
        """Handle updates from the SPC panel."""
        if isinstance(spc_object, Area):
            async_dispatcher_send(hass, SIGNAL_UPDATE_ALARM.format(spc_object.id))
        elif isinstance(spc_object, Zone):
            async_dispatcher_send(hass, SIGNAL_UPDATE_SENSOR.format(spc_object.id))

    try:
        session = aiohttp_client.async_get_clientsession(hass)
        
        spc = SpcWebGateway(
            loop=asyncio.get_event_loop(),
            session=session,
            api_url=entry.data[CONF_API_URL],
            ws_url=entry.data[CONF_WS_URL],
            async_callback=async_update_callback,
        )

        # Initialize the connection
        try:
            if not await spc.async_load_parameters():
                _LOGGER.error("Failed to load parameters from SPC panel")
                return False
        except Exception as err:
            _LOGGER.error("Failed to connect to SPC panel: %s", err)
            return False

        # Store the API object
        hass.data[DATA_API] = spc

        # Set up all platforms using the new method
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        
        # Start websocket connection
        spc.start()
        return True

    except Exception as err:
        _LOGGER.error("Error setting up SPC integration: %s", err)
        return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.entry_id not in hass.data:
        return False

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )
    if unload_ok:
        hass.data[DATA_API].stop()
        hass.data.pop(DATA_API)

    return unload_ok
