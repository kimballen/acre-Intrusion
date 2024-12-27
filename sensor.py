"""Support for acre Intrusion system information."""
from __future__ import annotations

import logging
from pyspcwebgw import SpcWebGateway
import aiohttp
from datetime import timedelta
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    EntityCategory,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory  # Add this import
from homeassistant.helpers import aiohttp_client

from . import DATA_API
from .const import CONF_API_URL, DATA_API

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = [
    SensorEntityDescription(
        key="batt_volt",
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,  # Changed from string to enum
    ),
    SensorEntityDescription(
        key="aux_volt",
        name="Auxiliary Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="aux_curr",
        name="Auxiliary Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="ac_freq",
        name="AC Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="gsm_signal",
        name="GSM Signal",
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_batt_volt",
        name="PSU Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_batt_curr",
        name="PSU Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out1_volt",
        name="PSU Output 1 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out1_curr",
        name="PSU Output 1 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out2_volt",
        name="PSU Output 2 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out2_curr",
        name="PSU Output 2 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out3_volt",
        name="PSU Output 3 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out3_curr",
        name="PSU Output 3 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

PANEL_SENSOR_TYPES = [
    SensorEntityDescription(
        key="panel_type",
        name="Panel Type",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="panel_variant",
        name="Panel Variant",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="panel_version",
        name="Panel Version",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="panel_device_id",
        name="Panel Device ID",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="panel_sn",
        name="Panel Serial Number",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="panel_cfgtime",
        name="Panel Configuration Time",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="panel_hw_ver_major",
        name="Panel Hardware Version Major",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="panel_hw_ver_minor",
        name="Panel Hardware Version Minor",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="panel_hw_ver_vds",
        name="Panel Hardware Version VDS",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="panel_license_key",
        name="Panel License Key",
        device_class=None,
        state_class=None,
    ),
]

XBUS_SENSORS = [
    SensorEntityDescription(
        key="xbus_status",
        name="X-BUS Status",
        icon="mdi:network",
    ),
    SensorEntityDescription(
        key="xbus_voltage",
        name="X-BUS Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

SYSTEM_SENSOR_TYPES = [
    SensorEntityDescription(
        key="system_time",
        name="System Time",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="system_engmode",
        name="Engineering Mode",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="system_rf_type",
        name="RF Type",
        device_class=None,
        state_class=None,
    ),
    SensorEntityDescription(
        key="system_rf_version",
        name="RF Version",
        device_class=None,
        state_class=None,
    ),
]

MODEM_SENSOR_TYPES = [
    SensorEntityDescription(
        key="port",
        name="Port",
        icon="mdi:port",
    ),
    SensorEntityDescription(
        key="enabled",
        name="Enabled",
        icon="mdi:power",
    ),
    SensorEntityDescription(
        key="status",
        name="Status",
        icon="mdi:information",
    ),
    SensorEntityDescription(
        key="state",
        name="State",
        icon="mdi:state-machine",
    ),
    SensorEntityDescription(
        key="type",
        name="Type",
        icon="mdi:cellphone-link",
    ),
    SensorEntityDescription(
        key="id_type",
        name="Model",
        icon="mdi:radio-tower",
    ),
    SensorEntityDescription(
        key="id_fw",
        name="Firmware",
        icon="mdi:firmware",
    ),
    SensorEntityDescription(
        key="id_hw",
        name="Hardware Version",
        icon="mdi:circuit-board",
    ),
    SensorEntityDescription(
        key="capabilities",
        name="Capabilities",
        icon="mdi:feature-search",
    ),
    SensorEntityDescription(
        key="gsm_signal",
        name="GSM Signal",
        icon="mdi:signal",
        native_unit_of_measurement="bars",
    ),
    SensorEntityDescription(
        key="incoming_time",
        name="Incoming Time",
        icon="mdi:timer-outline",
    ),
    SensorEntityDescription(
        key="incoming_count",
        name="Incoming Count",
        icon="mdi:counter",
    ),
    SensorEntityDescription(
        key="outgoing_time",
        name="Outgoing Time",
        icon="mdi:timer",
    ),
    SensorEntityDescription(
        key="outgoing_count",
        name="Outgoing Count",
        icon="mdi:counter",
    ),
    SensorEntityDescription(
        key="outgoing_failed",
        name="Failed Outgoing",
        icon="mdi:alert-circle",
    ),
    SensorEntityDescription(
        key="incoming_sms_count",
        name="Incoming SMS",
        icon="mdi:message-incoming",
    ),
    SensorEntityDescription(
        key="outgoing_sms_count",
        name="Outgoing SMS",
        icon="mdi:message-outgoing",
    ),
]

# Add this new constant after other sensor type definitions
ETHERNET_SENSOR_TYPES = [
    SensorEntityDescription(
        key="fitted",
        name="Ethernet Fitted",
        icon="mdi:ethernet",
    ),
    SensorEntityDescription(
        key="state",
        name="Ethernet State",
        icon="mdi:ethernet",
    ),
    SensorEntityDescription(
        key="dhcp_enabled",
        name="DHCP Enabled",
        icon="mdi:ip-network",
    ),
    SensorEntityDescription(
        key="mac_address",
        name="MAC Address",
        icon="mdi:ethernet",
    ),
    SensorEntityDescription(
        key="ip_address",
        name="IP Address",
        icon="mdi:ip",
    ),
    SensorEntityDescription(
        key="netmask",
        name="Network Mask",
        icon="mdi:ip-network",
    ),
    SensorEntityDescription(
        key="gateway",
        name="Gateway",
        icon="mdi:router-network",
    ),
    SensorEntityDescription(
        key="tx_packets",
        name="Transmitted Packets",
        icon="mdi:upload-network",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="tx_bytes",
        name="Transmitted Bytes",
        icon="mdi:upload-network",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="bytes",
    ),
    SensorEntityDescription(
        key="rx_packets",
        name="Received Packets",
        icon="mdi:download-network",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorEntityDescription(
        key="rx_bytes",
        name="Received Bytes",
        icon="mdi:download-network",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="bytes",
    ),
]

# Add this new constant after other sensor type definitions
AREA_SENSOR_TYPES = [
    SensorEntityDescription(
        key="mode",
        name="Mode",
        icon="mdi:security",
    ),
    SensorEntityDescription(
        key="last_set_time",
        name="Last Set Time",
        icon="mdi:clock",
    ),
    SensorEntityDescription(
        key="last_unset_time",
        name="Last Unset Time",
        icon="mdi:clock",
    ),
    SensorEntityDescription(
        key="last_set_user_id",
        name="Last Set User ID",
        icon="mdi:account",
    ),
    SensorEntityDescription(
        key="last_set_user_name",
        name="Last Set User Name",
        icon="mdi:account",
    ),
    SensorEntityDescription(
        key="last_unset_user_id",
        name="Last Unset User ID",
        icon="mdi:account",
    ),
    SensorEntityDescription(
        key="last_unset_user_name",
        name="Last Unset User Name",
        icon="mdi:account",
    ),
    SensorEntityDescription(
        key="last_alarm",
        name="Last Alarm",
        icon="mdi:alarm",
    ),
]

# Add this new constant after other sensor type definitions
XBUS_NODE_SENSOR_TYPES = [
    SensorEntityDescription(
        key="aux_volt",
        name="Auxiliary Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="aux_curr",
        name="Auxiliary Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out1_volt",
        name="PSU Output 1 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out1_curr",
        name="PSU Output 1 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out2_volt",
        name="PSU Output 2 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out2_curr",
        name="PSU Output 2 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out3_volt",
        name="PSU Output 3 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_out3_curr",
        name="PSU Output 3 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_batt_volt",
        name="PSU Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="psu_batt_curr",
        name="PSU Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

SCAN_INTERVAL = timedelta(minutes=1)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Acre SPC sensor based on a config entry."""
    api: SpcWebGateway = hass.data[DATA_API]
    session = aiohttp_client.async_get_clientsession(hass)
    api_ip = entry.data[CONF_API_URL].split("//")[-1].split("/")[0]  # Extract IP address from API URL
    
    # Create update coordinator
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="acre_intrusion_psu",
        update_method=lambda: async_update_data(api, session),
        update_interval=SCAN_INTERVAL,
    )

    # Initial data fetch
    await coordinator.async_refresh()
    
    entities = []
    for description in SENSOR_TYPES:
        entities.append(SpcSystemSensor(coordinator, api, description, api_ip))
    
    for description in PANEL_SENSOR_TYPES:
        entities.append(SpcSystemSensor(coordinator, api, description, api_ip))
    
    for description in SYSTEM_SENSOR_TYPES:
        entities.append(SpcSystemSensor(coordinator, api, description, api_ip))
    
    for modem_num in range(1, 3):  # Support for 2 modems
        if any(key.startswith(f"modem_{modem_num}_") for key in coordinator.data or {}):
            for description in MODEM_SENSOR_TYPES:
                entities.append(
                    ModemSensor(
                        coordinator,
                        api,
                        description,
                        modem_num,
                        api_ip
                    )
                )
    
    if hasattr(api, 'xbus_nodes'):
        for node in api.xbus_nodes.values():
            for description in XBUS_SENSORS:
                entities.append(XbusNodeSensor(node, description, api_ip))
    
    # Add ethernet sensors
    if coordinator.data and any(key.startswith("ethernet_") for key in coordinator.data):
        for description in ETHERNET_SENSOR_TYPES:
            entities.append(
                EthernetSensor(
                    coordinator,
                    api,
                    description,
                    api_ip
                )
            )

    # Add area sensors
    if coordinator.data and any(key.startswith("area_") for key in coordinator.data):
        for area_id in range(1, 6):  # Assuming up to 5 areas
            if any(key.startswith(f"area_{area_id}_") for key in coordinator.data):
                for description in AREA_SENSOR_TYPES:
                    entities.append(
                        AreaSensor(
                            coordinator,
                            api,
                            description,
                            area_id,
                            api_ip
                        )
                    )

    # Add xbus node sensors
    if coordinator.data and any(key.startswith("xbusnode_") for key in coordinator.data):
        for node_id in range(1, 9):  # Assuming up to 8 nodes
            if any(key.startswith(f"xbusnode_{node_id}_") for key in coordinator.data):
                for description in XBUS_NODE_SENSOR_TYPES:
                    entities.append(
                        XbusNodeSensor(
                            coordinator,
                            api,
                            description,
                            node_id,
                            api_ip
                        )
                    )

    async_add_entities(entities)

async def async_update_data(api, session):
    """Fetch data from API."""
    try:
        data = {}
        base_url = api._api_url  # Changed from api.api_url to api._api_url
        
        # Get PSU data according to API spec
        async with session.get(f"{base_url}/spc/psu") as resp:  # Updated endpoint
            if resp.status == 200:
                psu_data = await resp.json()
                if psu_data.get("status") == "success" and "data" in psu_data:
                    psu = psu_data["data"].get("psu", {})
                    # Map data according to API response
                    for key in ["batt_volt", "aux_volt", "aux_curr", "ac_freq"]:
                        if key in psu:
                            data[key] = psu[key]

        # Get panel data according to API spec
        async with session.get(f"{base_url}/spc/panel") as resp:  # Added endpoint
            if resp.status == 200:
                panel_data = await resp.json()
                if panel_data.get("status") == "success" and "data" in panel_data:
                    panel = panel_data["data"].get("panel", {})
                    # Map data according to API response
                    data.update({
                        "panel_type": panel.get("type"),
                        "panel_variant": panel.get("variant"),
                        "panel_version": panel.get("version"),
                        "panel_device_id": panel.get("device-id"),
                        "panel_sn": panel.get("sn"),
                        "panel_cfgtime": panel.get("cfgtime"),
                        "panel_hw_ver_major": panel.get("hw_ver_major"),
                        "panel_hw_ver_minor": panel.get("hw_ver_minor"),
                        "panel_hw_ver_vds": panel.get("hw_ver_vds"),
                        "panel_license_key": panel.get("license_key"),
                    })

        # Get system data according to API spec
        async with session.get(f"{base_url}/spc/system") as resp:  # Added endpoint
            if resp.status == 200:
                system_data = await resp.json()
                if system_data.get("status") == "success" and "data" in system_data:
                    system = system_data["data"].get("system", {})
                    # Map data according to API response
                    data.update({
                        "system_time": system.get("time"),
                        "system_engmode": system.get("engmode"),
                        "system_rf_type": system.get("rf_type"),
                        "system_rf_version": system.get("rf_version"),
                    })

        # Get modem data according to API spec
        async with session.get(f"{base_url}/spc/modem") as resp:  # Added endpoint
            if resp.status == 200:
                modem_data = await resp.json()
                if modem_data.get("status") == "success" and "data" in modem_data:
                    modems = modem_data["data"].get("modem", [])
                    for i, modem in enumerate(modems, 1):
                        for key, value in modem.items():
                            data[f"modem_{i}_{key}"] = value

        # Get ethernet data
        async with session.get(f"{base_url}/spc/ethernet") as resp:
            if resp.status == 200:
                ethernet_data = await resp.json()
                if (ethernet_data.get("status") == "success" 
                    and "data" in ethernet_data 
                    and "ethernet" in ethernet_data["data"]):
                    ethernet = ethernet_data["data"]["ethernet"]
                    for key, value in ethernet.items():
                        data[f"ethernet_{key}"] = value

        # Get area data
        async with session.get(f"{base_url}/spc/area") as resp:
            if resp.status == 200:
                area_data = await resp.json()
                if (area_data.get("status") == "success" 
                    and "data" in area_data 
                    and "area" in area_data["data"]):
                    areas = area_data["data"]["area"]
                    for area in areas:
                        area_id = area["id"]
                        for key, value in area.items():
                            data[f"area_{area_id}_{key}"] = value

        # Get xbus node data
        async with session.get(f"{base_url}/spc/xbusnode") as resp:
            if resp.status == 200:
                xbusnode_data = await resp.json()
                if (xbusnode_data.get("status") == "success" 
                    and "data" in xbusnode_data 
                    and "xbusnode" in xbusnode_data["data"]):
                    xbusnodes = xbusnode_data["data"]["xbusnode"]
                    for node in xbusnodes:
                        node_id = node["id"]
                        for key, value in node.items():
                            data[f"xbusnode_{node_id}_{key}"] = value

        _LOGGER.debug("Fetched data: %s", data)
        return data

    except Exception as err:
        _LOGGER.error("Error fetching data: %s", err)
        return None

class SpcSystemSensor(CoordinatorEntity, SensorEntity):
    """Representation of a SPC sensor."""

    def __init__(
        self, coordinator, api: SpcWebGateway, description: SensorEntityDescription, api_ip: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._attr_name = description.name
        self._attr_unique_id = f"acre_intrusion_system_{description.key}"
        self._attr_device_info = {
            "identifiers": {("acre_intrusion", api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Panel",
        }

    @property
    def native_value(self) -> float | str | None:
        """Return the native value of the sensor."""
        if not self.coordinator.data:
            return None
            
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None

        try:
            if isinstance(value, str):
                # Convert string values to float if applicable
                if value.endswith('V'):
                    return float(value.rstrip('V'))
                elif value.endswith('mA'):
                    return float(value.rstrip('mA'))
                elif value.endswith('Hz'):
                    return float(value.rstrip('Hz'))
            return value
        except (ValueError, TypeError):
            return None

class XbusNodeSensor(SensorEntity):
    """Representation of an X-BUS node sensor."""

    def __init__(self, node, description: SensorEntityDescription, api_ip: str) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._node = node
        self._attr_unique_id = f"acre_intrusion_xbus_{node.id}_{description.key}"
        self._attr_name = f"{node.name} {description.name}"
        self._attr_device_info = {
            "identifiers": {("acre_intrusion", api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC X-BUS Node",
        }

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.entity_description.key == "xbus_voltage":
            value = self._node.aux_volt
            if value and isinstance(value, str):
                try:
                    return float(value.rstrip('V'))
                except ValueError:
                    _LOGGER.error("Could not parse X-BUS voltage value: %s", value)
                    return None
        elif self.entity_description.key == "xbus_status":
            return "Online" if self._node.status == 0 else "Problem"

class ModemSensor(CoordinatorEntity, SensorEntity):
    """Representation of a modem sensor."""

    def __init__(
        self, coordinator, api: SpcWebGateway, description: SensorEntityDescription, modem_num: int, api_ip: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._modem_num = modem_num
        self._attr_name = f"Modem {modem_num} {description.name}"
        self._attr_unique_id = f"acre_intrusion_modem_{modem_num}_{description.key}"
        self._attr_device_info = {
            "identifiers": {("acre_intrusion", api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Modem",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        
        value = self.coordinator.data.get(f"modem_{self._modem_num}_{self.entity_description.key}")
        
        # Special handling for certain values
        if self.entity_description.key == "enabled":
            return "Yes" if value == "1" else "No"
        elif self.entity_description.key == "status" or self.entity_description.key == "state":
            return "Active" if value == "1" else "Inactive"
            
        return value

# Add new EthernetSensor class
class EthernetSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Ethernet sensor."""

    def __init__(
        self, coordinator, api: SpcWebGateway, description: SensorEntityDescription, api_ip: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._attr_name = f"Ethernet {description.name}"
        self._attr_unique_id = f"acre_intrusion_ethernet_{description.key}"
        self._attr_device_info = {
            "identifiers": {("acre_intrusion", api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Ethernet Interface",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        
        value = self.coordinator.data.get(f"ethernet_{self.entity_description.key}")
        
        # Special handling for certain values
        if self.entity_description.key in ["fitted", "state", "dhcp_enabled"]:
            return "Yes" if value == "1" else "No"
        elif self.entity_description.key in ["tx_bytes", "rx_bytes", "tx_packets", "rx_packets"]:
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
            
        return value

# Add new AreaSensor class
class AreaSensor(CoordinatorEntity, SensorEntity):
    """Representation of an Area sensor."""

    def __init__(
        self, coordinator, api: SpcWebGateway, description: SensorEntityDescription, area_id: int, api_ip: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._area_id = area_id
        self._attr_name = f"Area {area_id} {description.name}"
        self._attr_unique_id = f"acre_intrusion_area_{area_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {("acre_intrusion", api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC Area",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        
        value = self.coordinator.data.get(f"area_{self._area_id}_{self.entity_description.key}")
        
        # Special handling for certain values
        if self.entity_description.key in ["last_set_time", "last_unset_time", "last_alarm"]:
            try:
                return int(value)
            except (ValueError, TypeError):
                return None
            
        return value

# Add new XbusNodeSensor class
class XbusNodeSensor(CoordinatorEntity, SensorEntity):
    """Representation of an X-BUS node sensor."""

    def __init__(
        self, coordinator, api: SpcWebGateway, description: SensorEntityDescription, node_id: int, api_ip: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._node_id = node_id
        self._attr_name = f"X-BUS Node {node_id} {description.name}"
        self._attr_unique_id = f"acre_intrusion_xbusnode_{node_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {("acre_intrusion", api_ip)},
            "name": f"SPC Panel ({api_ip})",
            "manufacturer": "Vanderbilt",
            "model": "SPC X-BUS Node",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        
        value = self.coordinator.data.get(f"xbusnode_{self._node_id}_{self.entity_description.key}")
        if value is None:
            return None
            
        # Special handling for certain values
        if self.entity_description.key in ["aux_volt", "psu_out1_volt", "psu_out2_volt", "psu_out3_volt", "psu_batt_volt"]:
            try:
                if isinstance(value, str):
                    return float(value.rstrip('V'))
                return float(value)
            except (ValueError, TypeError, AttributeError):
                return None
        elif self.entity_description.key in ["aux_curr", "psu_out1_curr", "psu_out2_curr", "psu_out3_curr", "psu_batt_curr"]:
            try:
                if isinstance(value, str):
                    return float(value.rstrip('mA'))
                return float(value)
            except (ValueError, TypeError, AttributeError):
                return None
            
        return value
