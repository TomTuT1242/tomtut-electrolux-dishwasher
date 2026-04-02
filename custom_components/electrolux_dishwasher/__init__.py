"""Electrolux/AEG Dishwasher integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ElectroluxApi
from .const import DOMAIN
from .coordinator import ElectroluxCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Electrolux Dishwasher from a config entry."""
    session = async_get_clientsession(hass)
    api = ElectroluxApi(session)

    try:
        await api.authenticate(entry.data["session_token"])
    except Exception:
        _LOGGER.warning("Session expired, re-authentication needed")
        return False

    coordinator = ElectroluxCoordinator(
        hass, api, entry.data["appliance_id"]
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
