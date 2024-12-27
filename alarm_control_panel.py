"""Support for acre Intrusion alarm systems."""

from __future__ import annotations

from pyspcwebgw import SpcWebGateway
from pyspcwebgw.area import Area
from pyspcwebgw.const import AreaMode

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.config_entries import ConfigEntry

from .const import DATA_API, SIGNAL_UPDATE_ALARM, DOMAIN, CONF_API_URL
from .storage import PinStorage

import re
import logging

_LOGGER = logging.getLogger(__name__)

def _get_alarm_state(area: Area) -> AlarmControlPanelState | None:
    """Get the alarm state."""

    if area.verified_alarm:
        return AlarmControlPanelState.TRIGGERED

    mode_to_state = {
        AreaMode.UNSET: AlarmControlPanelState.DISARMED,
        AreaMode.PART_SET_A: AlarmControlPanelState.ARMED_HOME,
        AreaMode.PART_SET_B: AlarmControlPanelState.ARMED_NIGHT,
        AreaMode.FULL_SET: AlarmControlPanelState.ARMED_AWAY,
    }
    return mode_to_state.get(area.mode)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the SPC alarm control panel platform."""
    if discovery_info is None:
        return
    api: SpcWebGateway = hass.data[DATA_API]
    async_add_entities([SpcAlarm(area=area, api=api) for area in api.areas.values()])


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    """Set up the acre Intrusion alarm control panel from a config entry."""
    api: SpcWebGateway = hass.data[DATA_API]
    api_ip = entry.data[CONF_API_URL].split("//")[-1].split("/")[0]
    async_add_entities([SpcAlarm(area=area, api=api, api_ip=api_ip) for area in api.areas.values()])
    return True


class SpcAlarm(AlarmControlPanelEntity):
    """Representation of the SPC alarm panel."""

    _attr_should_poll = False
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.ARM_NIGHT
    )
    _attr_code_arm_required = True
    _attr_code_format = "^[0-9]{6}$"  # Require exactly 6 digits

    def __init__(self, area: Area, api: SpcWebGateway, api_ip: str) -> None:
        """Initialize the SPC alarm panel."""
        self._area = area
        self._api = api
        self._attr_name = area.name
        self._attr_unique_id = f"acre_intrusion_alarm_{area.id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Controller",
        }
        self._valid_codes = self._api.get_user_codes() if hasattr(self._api, 'get_user_codes') else None

    async def async_added_to_hass(self) -> None:
        """Call for adding new entities."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_ALARM.format(self._area.id),
                self._update_callback,
            )
        )

    @callback
    def _update_callback(self) -> None:
        """Call update method."""
        self.async_schedule_update_ha_state(True)

    @property
    def changed_by(self) -> str:
        """Return the user the last change was triggered by."""
        return self._area.last_changed_by

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the state of the device."""
        return _get_alarm_state(self._area)

    async def _validate_code(self, code: str | None) -> bool:
        """Validate given code."""
        if code is None:
            return False
            
        pin_storage = PinStorage(self.hass)
        await pin_storage.async_load()
        return pin_storage.verify_pin(code)

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        pin_storage = PinStorage(self.hass)
        await pin_storage.async_load()
        
        if not pin_storage.verify_pin(code):
            _LOGGER.warning("Invalid code provided for disarming")
            return

        await self._api.change_mode(area=self._area, new_mode=AreaMode.UNSET)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        pin_storage = PinStorage(self.hass)
        await pin_storage.async_load()
        
        if not pin_storage.verify_pin(code):
            _LOGGER.warning("Invalid code provided for arming home")
            return

        await self._api.change_mode(area=self._area, new_mode=AreaMode.PART_SET_A)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send arm night command."""
        if not self._validate_code(code):
            _LOGGER.warning("Invalid code provided for arming night")
            return

        await self._api.change_mode(area=self._area, new_mode=AreaMode.PART_SET_B)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        pin_storage = PinStorage(self.hass)
        await pin_storage.async_load()
        
        if not pin_storage.verify_pin(code):
            _LOGGER.warning("Invalid code provided for arming away")
            return

        await self._api.change_mode(area=self._area, new_mode=AreaMode.FULL_SET)


class IntrusionAlarm(AlarmControlPanelEntity):
    """Representation of the Intrusion alarm panel."""
    # ...existing code...
