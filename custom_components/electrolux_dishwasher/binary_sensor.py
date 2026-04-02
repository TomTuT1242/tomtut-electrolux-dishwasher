"""Binary sensor platform for Electrolux Dishwasher."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ElectroluxCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ElectroluxCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DishwasherRunningSensor(coordinator, entry),
        DishwasherDoorSensor(coordinator, entry),
        DishwasherConnectedSensor(coordinator, entry),
        DishwasherSaltWarningSensor(coordinator, entry),
        DishwasherRinseAidWarningSensor(coordinator, entry),
    ]
    async_add_entities(entities)


class DishwasherBaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator: ElectroluxCoordinator, entry: ConfigEntry, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data['appliance_id']}_{key}"
        self._attr_name = f"{entry.data.get('appliance_name', 'Dishwasher')} {name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["appliance_id"])},
            "name": entry.data.get("appliance_name", "Geschirrspülmaschine"),
            "manufacturer": "AEG/Electrolux",
            "model": "GI8700B2SC 8000 XXL",
        }


class DishwasherRunningSensor(DishwasherBaseBinarySensor):
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:dishwasher"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "running", "Läuft")

    @property
    def is_on(self) -> bool:
        return self.coordinator.appliance_state in ("RUNNING", "DELAYED_START")


class DishwasherDoorSensor(DishwasherBaseBinarySensor):
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "door", "Tür")

    @property
    def is_on(self) -> bool:
        return self.coordinator.door_state == "OPEN"


class DishwasherConnectedSensor(DishwasherBaseBinarySensor):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "connected", "Verbunden")

    @property
    def is_on(self) -> bool:
        return self.coordinator.connection_state == "connected"


class DishwasherSaltWarningSensor(DishwasherBaseBinarySensor):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:shaker-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "salt_warning", "Salz fehlt")

    @property
    def is_on(self) -> bool:
        return any(
            a.get("code") == "DISH_ALARM_SALT_MISSING"
            for a in self.coordinator.alerts
        )


class DishwasherRinseAidWarningSensor(DishwasherBaseBinarySensor):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:water-alert-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "rinse_aid_warning", "Klarspüler niedrig")

    @property
    def is_on(self) -> bool:
        return any(
            a.get("code") == "DISH_ALARM_RINSE_AID_LOW"
            for a in self.coordinator.alerts
        )
