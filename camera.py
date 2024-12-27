"""Support for SPC cameras."""
from __future__ import annotations

import logging
import base64
from typing import Any
import aiohttp

from pyspcwebgw import SpcWebGateway

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import aiohttp_client

from .const import CONF_API_URL, DATA_API, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SPC cameras."""
    api = hass.data[DATA_API]
    api_ip = entry.data[CONF_API_URL].split("//")[-1].split("/")[0]

    # Test creating a single camera regardless of verification zones
    cameras = []
    _LOGGER.debug("Setting up SPC cameras with API URL: %s", api._api_url)
    
    # Add a camera for each zone ID (1-8 typically for SPC panels)
    for zone_id in range(1, 9):
        camera = SpcCamera(
            zone_id=zone_id,
            name=f"SPC Camera {zone_id}",
            api_ip=api_ip,
            api_url=api._api_url
        )
        cameras.append(camera)
        _LOGGER.debug("Added camera for zone %s", zone_id)

    if cameras:
        async_add_entities(cameras)
        _LOGGER.info("Added %s SPC cameras", len(cameras))

class SpcCamera(Camera):
    """SPC camera."""

    def __init__(self, zone_id: int, name: str, api_ip: str, api_url: str) -> None:
        """Initialize the camera."""
        super().__init__()
        self._zone_id = zone_id
        self._attr_name = name
        self._attr_unique_id = f"acre_intrusion_camera_{zone_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Controller",
        }
        self._last_image = None
        self._api_url = api_url
        self._session = None
        _LOGGER.debug("Initialized camera %s with API URL: %s", self._attr_name, self._api_url)

    @property
    def supported_features(self) -> CameraEntityFeature:
        """Return supported features."""
        return CameraEntityFeature.STREAM

    async def async_stream_source(self) -> str | None:
        """Return stream source URL."""
        return f"{self._api_url}/spc/image/{self._zone_id}"

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return image response."""
        try:
            url = f"{self._api_url}/spc/image/{self._zone_id}"
            _LOGGER.debug("Fetching camera image from: %s", url)
            
            if self._session is None:
                self._session = aiohttp_client.async_get_clientsession(self.hass)
            
            async with self._session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if (data.get("status") == "success" and 
                        "data" in data and 
                        "image" in data["data"] and 
                        "data" in data["data"]["image"]):
                        
                        image_data = data["data"]["image"]["data"]
                        decoded_image = base64.b64decode(image_data)
                        self._last_image = decoded_image
                        return decoded_image
            
            return self._last_image
                            
        except Exception as err:
            _LOGGER.error("Error getting camera image: %s", err)
            return self._last_image
