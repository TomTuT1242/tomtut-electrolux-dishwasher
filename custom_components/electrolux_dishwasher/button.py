"""Button platform for Electrolux Dishwasher."""

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ElectroluxCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ElectroluxCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DishwasherCommandButton(coordinator, entry, "START", "Start", "mdi:play"),
        DishwasherCommandButton(coordinator, entry, "PAUSE", "Pause", "mdi:pause"),
        DishwasherCommandButton(coordinator, entry, "RESUME", "Fortsetzen", "mdi:play-pause"),
        DishwasherCommandButton(coordinator, entry, "STOPRESET", "Stop/Reset", "mdi:stop"),
        DishwasherCommandButton(coordinator, entry, "ON", "Einschalten", "mdi:power"),
        DishwasherCommandButton(coordinator, entry, "OFF", "Ausschalten", "mdi:power-off"),
    ]
    async_add_entities(entities)


class DishwasherCommandButton(CoordinatorEntity, ButtonEntity):
    """Button to send command to dishwasher."""

    def __init__(
        self,
        coordinator: ElectroluxCoordinator,
        entry: ConfigEntry,
        command: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._command = command
        self._attr_unique_id = f"{entry.data['appliance_id']}_cmd_{command.lower()}"
        self._attr_name = f"{entry.data.get('appliance_name', 'Dishwasher')} {name}"
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["appliance_id"])},
            "name": entry.data.get("appliance_name", "Geschirrspülmaschine"),
            "manufacturer": "AEG/Electrolux",
            "model": "GI8700B2SC 8000 XXL",
        }

    async def async_press(self) -> None:
        """Send command on button press."""
        _LOGGER.info("Sending command %s", self._command)
        await self.coordinator.send_command(self._command)
