"""Support for acre Intrusion binary sensors."""

from __future__ import annotations

from pyspcwebgw import SpcWebGateway
from pyspcwebgw.const import ZoneInput, ZoneType
from pyspcwebgw.zone import Zone

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_API_URL, DATA_API, SIGNAL_UPDATE_SENSOR, DOMAIN

SYSTEM_ALERTS = {
    0: ("mains_fail", "Mains Power Fault", BinarySensorDeviceClass.PROBLEM),
    1: ("battery_fail", "Battery Fault", BinarySensorDeviceClass.BATTERY),
    2: ("aux_fuse", "Auxiliary Fuse", BinarySensorDeviceClass.PROBLEM),
    5: ("bell_tamper", "Bell Tamper", BinarySensorDeviceClass.TAMPER),
    6: ("cabinet_tamper", "Cabinet Tamper", BinarySensorDeviceClass.TAMPER),
    9: ("wireless_tamper", "Wireless Tamper", BinarySensorDeviceClass.TAMPER),
    10: ("wireless_jamming", "Wireless Jamming", BinarySensorDeviceClass.PROBLEM),
    11: ("modem1_fault", "Modem 1 Fault", BinarySensorDeviceClass.PROBLEM),
    12: ("modem1_line_fault", "Modem 1 Line Fault", BinarySensorDeviceClass.PROBLEM),
    13: ("modem2_fault", "Modem 2 Fault", BinarySensorDeviceClass.PROBLEM),
    14: ("modem2_line_fault", "Modem 2 Line Fault", BinarySensorDeviceClass.PROBLEM),
    15: ("cable_fault", "Cable Fault", BinarySensorDeviceClass.PROBLEM),
    16: ("fail_to_communicate", "Fail to Communicate", BinarySensorDeviceClass.PROBLEM),
    17: ("user_duress", "User Duress", BinarySensorDeviceClass.SAFETY),
    18: ("date_time_lost", "Date/Time Lost", BinarySensorDeviceClass.PROBLEM),
    19: ("user_rf_panic", "User RF Panic", BinarySensorDeviceClass.SAFETY),
    20: ("user_man_down", "User Man Down", BinarySensorDeviceClass.SAFETY),
    21: ("panel_power_supply_problem", "Panel Power Supply Problem", BinarySensorDeviceClass.PROBLEM),
}

DOOR_STATES = {
    0: "closed",
    1: "open_too_long",
    2: "left_open",
    3: "forced",
    4: "tamper",
    5: "offline"
}

WIRELESS_STATES = {
    0: "closed",
    1: "tamper",
    2: "open",
    3: "fault"
}

def _get_device_class(zone_type: ZoneType) -> BinarySensorDeviceClass | None:
    """Get the device class based on zone type."""
    return {
        ZoneType.ALARM: BinarySensorDeviceClass.MOTION,
        ZoneType.ENTRY_EXIT: BinarySensorDeviceClass.DOOR,
        ZoneType.FIRE: BinarySensorDeviceClass.SMOKE,
        ZoneType.TECHNICAL: BinarySensorDeviceClass.PROBLEM,
        ZoneType.PANIC: BinarySensorDeviceClass.SAFETY,
        ZoneType.HOLD_UP: BinarySensorDeviceClass.SAFETY,
        ZoneType.TAMPER: BinarySensorDeviceClass.TAMPER,
        ZoneType.MEDICAL: BinarySensorDeviceClass.PROBLEM,
        ZoneType.KEYARM: BinarySensorDeviceClass.LOCK,
        ZoneType.SEISMIC: BinarySensorDeviceClass.VIBRATION,
    }.get(zone_type)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Intrusion binary sensor."""
    if discovery_info is None:
        return
    api: SpcWebGateway = hass.data[DATA_API]
    async_add_entities(
        [
            SpcBinarySensor(zone)
            for zone in api.zones.values()
            if _get_device_class(zone.type)
        ]
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    """Set up acre Intrusion binary sensors."""
    api = hass.data[DATA_API]
    api_ip = entry.data[CONF_API_URL].split("//")[-1].split("/")[0]
    entities = []

    # Add zone sensors
    entities.extend(
        [
            SpcBinarySensor(zone, api_ip)
            for zone in api.zones.values()
            if _get_device_class(zone.type)
        ]
    )

    # Add door sensors
    if hasattr(api, 'doors'):
        entities.extend([SpcDoorSensor(door, api_ip) for door in api.doors.values()])

    # Add wireless sensors
    if hasattr(api, 'wireless_sensors'):
        entities.extend([SpcWirelessSensor(sensor, api_ip) for sensor in api.wireless_sensors.values()])

    # Add system alert sensors
    if hasattr(api, 'alerts'):
        entities.extend(
            [
                SystemAlertSensor(api, alert_id, name, device_class, api_ip)
                for alert_id, (key, name, device_class) in SYSTEM_ALERTS.items()
            ]
        )

    async_add_entities(entities)
    return True


class SpcBinarySensor(BinarySensorEntity):
    """Representation of a sensor based on a Intrusion zone."""

    _attr_should_poll = False

    def __init__(self, zone: Zone, api_ip: str) -> None:
        """Initialize the sensor device."""
        self._zone = zone
        self._attr_name = zone.name
        self._attr_unique_id = f"acre_intrusion_zone_{zone.id}"
        self._attr_device_class = _get_device_class(zone.type)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Controller",
        }

    async def async_added_to_hass(self) -> None:
        """Call for adding new entities."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE_SENSOR.format(self._zone.id),
                self._update_callback,
            )
        )

    @callback
    def _update_callback(self) -> None:
        """Call update method."""
        self.async_schedule_update_ha_state(True)

    @property
    def is_on(self) -> bool:
        """Whether the device is switched on."""
        return self._zone.input == ZoneInput.OPEN


class SystemAlertSensor(BinarySensorEntity):
    """Representation of a system alert sensor."""

    def __init__(self, api, alert_id: int, name: str, device_class: str, api_ip: str) -> None:
        """Initialize the sensor."""
        self._api = api
        self._alert_id = alert_id
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_unique_id = f"acre_intrusion_alert_{alert_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Controller",
        }

    @property
    def is_on(self) -> bool:
        """Return true if the alert is active."""
        alert_state = int(self._api.alerts.get("input", "0"), 16)
        return bool(alert_state & (1 << self._alert_id))


class SpcDoorSensor(BinarySensorEntity):
    """Representation of an SPC door sensor."""

    def __init__(self, door, api_ip: str) -> None:
        """Initialize the sensor."""
        self._door = door
        self._attr_name = f"Door {door.name}"
        self._attr_unique_id = f"acre_intrusion_door_sensor_{door.id}"
        self._attr_device_class = BinarySensorDeviceClass.DOOR
        self._attr_extra_state_attributes = {
            "door_status": DOOR_STATES.get(door.status, "unknown")
        }
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Controller",
        }

    @property
    def is_on(self) -> bool:
        """Return true if door is open."""
        return self._door.status in [1, 2, 3]  # Open states


class SpcWirelessSensor(BinarySensorEntity):
    """Representation of an SPC wireless sensor."""

    def __init__(self, sensor, api_ip: str) -> None:
        """Initialize the sensor."""
        self._sensor = sensor
        self._attr_name = f"Wireless {sensor.name}"
        self._attr_unique_id = f"acre_intrusion_wireless_{sensor.id}"
        self._attr_device_class = BinarySensorDeviceClass.MOTION
        self._attr_extra_state_attributes = {
            "signal_strength": sensor.signal,
            "battery_low": bool(sensor.battery == 1),
            "status": WIRELESS_STATES.get(sensor.status, "unknown")
        }
        self._attr_device_info = {
            "identifiers": {(DOMAIN, api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Controller",
        }

    @property
    def is_on(self) -> bool:
        """Return true if sensor is triggered."""
        return self._sensor.status in [2, 3]  # Open or fault states
