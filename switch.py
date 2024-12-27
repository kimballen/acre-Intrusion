"""Support for Acre SPC outputs."""
from __future__ import annotations

import logging
from typing import Any

from pyspcwebgw import SpcWebGateway

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import timedelta

from . import DATA_API
from .const import CONF_API_URL, DATA_API, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up SPC outputs from config entry."""
    api: SpcWebGateway = hass.data[DATA_API]
    session = aiohttp_client.async_get_clientsession(hass)
    api_ip = entry.data[CONF_API_URL].split("//")[-1].split("/")[0]  # Extract IP address from API URL
    
    async def async_update_data():
        """Fetch data from API."""
        try:
            async with session.get(f"{api._api_url}/spc/output") as resp:
                if resp.status == 200:
                    output_data = await resp.json()
                    if (output_data.get("status") == "success" 
                        and "data" in output_data 
                        and "output" in output_data["data"]):
                        return output_data["data"]["output"]
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="spc_output",
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_refresh()

    outputs = []
    for output in coordinator.data:
        if output.get("name"):  # Only add outputs with a name
            outputs.append(
                SpcSwitch(
                    coordinator=coordinator,
                    output_id=output.get("id"),
                    name=output.get("name"),
                    api=api,
                    session=session,
                    state=output.get("state") == "1",
                    api_ip=api_ip
                )
            )
    
    if outputs:
        async_add_entities(outputs)

class SpcSwitch(SwitchEntity):
    """Representation of a SPC output."""

    def __init__(self, coordinator: DataUpdateCoordinator, output_id: str, name: str, api: SpcWebGateway, session: aiohttp.ClientSession, state: bool, api_ip: str) -> None:
        """Initialize the switch."""
        self.coordinator = coordinator
        self._output_id = output_id
        self._api = api
        self._session = session
        self._base_url = api._api_url  # Store base URL at init
        self._attr_name = name
        self._attr_unique_id = f"acre_intrusion_output_{output_id}"
        self._state = state
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Output",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the output on."""
        try:
            async with self._session.put(
                f"{self._base_url}/spc/output/{self._output_id}/set"
            ) as resp:
                if resp.status == 200:
                    self._state = True
                    await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to turn on output %s: %s", self._output_id, err)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the output off."""
        try:
            async with self._session.put(
                f"{self._base_url}/spc/output/{self._output_id}/reset"
            ) as resp:
                if resp.status == 200:
                    self._state = False
                    await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to turn off output %s: %s", self._output_id, err)

    @property
    def is_on(self) -> bool:
        """Return true if output is on."""
        return self._state

    async def async_update(self) -> None:
        """Update output state."""
        await self.coordinator.async_request_refresh()
        for output in self.coordinator.data:
            if output["id"] == self._output_id:
                self._state = output["state"] == "1"
                break
