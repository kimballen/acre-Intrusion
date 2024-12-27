"""Support for SPC events."""
from __future__ import annotations

import logging
from typing import Any

from pyspcwebgw import SpcWebGateway

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DATA_API

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SPC events from config entry."""
    api: SpcWebGateway = hass.data[DATA_API]
    if hasattr(api, 'events'):
        async_add_entities(SpcEvent(event) for event in api.events.values())

class SpcEvent(EventEntity):
    """Representation of a SPC event."""

    def __init__(self, event) -> None:
        """Initialize the event."""
        self._event = event
        self._attr_name = event.name
        self._attr_unique_id = f"acre_intrusion_event_{event.id}"
        self._attr_device_info = {
            "identifiers": {("acre_intrusion", f"event_{event.id}")},
            "name": event.name,
            "manufacturer": "Vanderbilt",
            "model": "SPC Event",
        }

    @property
    def state(self) -> str:
        """Return the state of the event."""
        return self._event.state
