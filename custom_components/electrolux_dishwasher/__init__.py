"""Electrolux/AEG Dishwasher integration."""

import logging
import shutil
from pathlib import Path

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ElectroluxApi
from .const import DOMAIN
from .coordinator import ElectroluxCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "button"]

CARD_JS = "tomtut-dishwasher-card.js"
CARD_DIR = "tomtut-dishwasher"
CARD_URL = f"/local/{CARD_JS}"
IMAGES_URL = f"/local/{CARD_DIR}"


async def _deploy_frontend(hass: HomeAssistant) -> None:
    """Copy card JS and images to www/ so they are served by HA."""
    www_dir = Path(hass.config.path("www"))
    www_dir.mkdir(exist_ok=True)

    integration_dir = Path(__file__).parent
    frontend_dir = integration_dir / "frontend"

    if not frontend_dir.exists():
        _LOGGER.debug("No frontend directory found, skipping card deployment")
        return

    # Copy card JS
    card_src = frontend_dir / CARD_JS
    card_dst = www_dir / CARD_JS
    if card_src.exists():
        if not card_dst.exists() or card_src.stat().st_mtime > card_dst.stat().st_mtime:
            shutil.copy2(card_src, card_dst)
            _LOGGER.info("Deployed %s to %s", CARD_JS, card_dst)

    # Copy images
    images_src = frontend_dir / "images"
    images_dst = www_dir / CARD_DIR
    if images_src.exists():
        images_dst.mkdir(exist_ok=True)
        for img in images_src.glob("*.png"):
            dst = images_dst / img.name
            if not dst.exists() or img.stat().st_mtime > dst.stat().st_mtime:
                shutil.copy2(img, dst)
                _LOGGER.info("Deployed image %s", img.name)

    # Register card as Lovelace resource
    await _register_card_resource(hass)


async def _register_card_resource(hass: HomeAssistant) -> None:
    """Register the card JS as a Lovelace resource if not already registered."""
    try:
        resources = hass.data.get("lovelace", {}).get("resources")
        if resources is None:
            return

        # Check if already registered
        existing = await resources.async_get_items() if hasattr(resources, "async_get_items") else []
        for item in existing:
            if CARD_JS in item.get("url", ""):
                _LOGGER.debug("Card resource already registered")
                return

        # Register
        await resources.async_create_item({"res_type": "module", "url": CARD_URL})
        _LOGGER.info("Registered Lovelace resource: %s", CARD_URL)
    except Exception as err:
        _LOGGER.debug("Could not auto-register card resource: %s (register manually via UI)", err)


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

    # Deploy card + images to www/
    await _deploy_frontend(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
