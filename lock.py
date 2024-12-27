"""Support for SPC Door locks."""
from __future__ import annotations

import logging
from typing import Any

from pyspcwebgw import SpcWebGateway

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_API_URL, DATA_API, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Door modes from SPC documentation
DOOR_MODE_NORMAL = 0
DOOR_MODE_LOCKED = 1
DOOR_MODE_BLOCKED = 2

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the SPC locks."""
    api: SpcWebGateway = hass.data[DATA_API]
    api_ip = entry.data[CONF_API_URL].split("//")[-1].split("/")[0]  # Extract IP address from API URL
    if hasattr(api, 'doors'):
        async_add_entities(SpcDoorLock(door, api_ip) for door in api.doors.values())

class SpcDoorLock(LockEntity):
    """Representation of an SPC door lock."""

    def __init__(self, door, api_ip: str) -> None:
        """Initialize the lock."""
        self._door = door
        self._attr_name = door.name
        self._attr_unique_id = f"acre_intrusion_door_{door.id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Door",
        }

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        return getattr(self._door, 'mode', 0) == 1  # 1 = Locked

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the door."""
        if hasattr(self._door, 'lock'):
            await self._door.lock()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the door."""
        if hasattr(self._door, 'set_normal_mode'):
            await self._door.set_normal_mode()

    async def async_open_permanently(self, **kwargs: Any) -> None:
        """Open the door permanently."""
        if hasattr(self._door, 'open_permanently'):
            await self._door.open_permanently()

    async def async_open_momentarily(self, **kwargs: Any) -> None:
        """Open the door momentarily."""
        if hasattr(self._door, 'open_momentarily'):
            await self._door.open_momentarily()

    async def async_isolate(self, **kwargs: Any) -> None:
        """Isolate the door."""
        if hasattr(self._door, 'isolate'):
            await self._door.isolate()

    async def async_deisolate(self, **kwargs: Any) -> None:
        """Deisolate the door."""
        if hasattr(self._door, 'deisolate'):
            await self._door.deisolate()

    async def async_inhibit(self, **kwargs: Any) -> None:
        """Inhibit the door."""
        if hasattr(self._door, 'inhibit'):
            await self._door.inhibit()

    async def async_deinhibit(self, **kwargs: Any) -> None:
        """Deinhibit the door."""
        if hasattr(self._door, 'deinhibit'):
            await self._door.deinhibit()
