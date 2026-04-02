"""Config flow for Electrolux/AEG Dishwasher."""

import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ElectroluxApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_EMAIL = "email"
STEP_OTP = "otp"
STEP_SELECT = "select_appliance"


class ElectroluxDishwasherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Electrolux Dishwasher."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._vtoken: str | None = None
        self._session_token: str | None = None
        self._api: ElectroluxApi | None = None
        self._appliances: list = []

    async def async_step_user(self, user_input=None):
        """Handle email input."""
        errors = {}
        if user_input is not None:
            self._email = user_input["email"]
            session = async_get_clientsession(self.hass)
            self._api = ElectroluxApi(session)
            try:
                self._vtoken = await self._api.send_otp(self._email)
                return await self.async_step_otp()
            except Exception as err:
                _LOGGER.error("OTP send failed: %s", err)
                errors["base"] = "otp_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("email"): str}),
            errors=errors,
            description_placeholders={"info": "Enter your AEG/Electrolux account email"},
        )

    async def async_step_otp(self, user_input=None):
        """Handle OTP verification."""
        errors = {}
        if user_input is not None:
            try:
                session_token = await self._api.verify_otp(
                    self._vtoken, user_input["code"]
                )
                await self._api.authenticate(session_token)
                self._session_token = session_token
                self._appliances = await self._api.get_appliances()

                # Filter dishwashers
                dw_appliances = [
                    a for a in self._appliances
                    if a.get("applianceData", {}).get("modelName") == "DW"
                ]

                if len(dw_appliances) == 1:
                    return self._create_entry(dw_appliances[0])
                elif len(dw_appliances) > 1:
                    return await self.async_step_select_appliance()
                else:
                    errors["base"] = "no_dishwasher"

            except Exception as err:
                _LOGGER.error("OTP verify failed: %s", err)
                errors["base"] = "auth_failed"

        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required("code"): str}),
            errors=errors,
            description_placeholders={"email": self._email},
        )

    async def async_step_select_appliance(self, user_input=None):
        """Handle appliance selection if multiple dishwashers."""
        if user_input is not None:
            appliance = next(
                a for a in self._appliances
                if a["applianceId"] == user_input["appliance_id"]
            )
            return self._create_entry(appliance)

        options = {
            a["applianceId"]: a.get("applianceData", {}).get("applianceName", a["applianceId"])
            for a in self._appliances
            if a.get("applianceData", {}).get("modelName") == "DW"
        }

        return self.async_show_form(
            step_id="select_appliance",
            data_schema=vol.Schema({
                vol.Required("appliance_id"): vol.In(options),
            }),
        )

    def _create_entry(self, appliance: dict):
        """Create config entry from appliance data."""
        appliance_id = appliance["applianceId"]
        name = appliance.get("applianceData", {}).get("applianceName", "Dishwasher")

        return self.async_create_entry(
            title=name,
            data={
                "email": self._email,
                "session_token": self._session_token,
                "appliance_id": appliance_id,
                "appliance_name": name,
            },
        )
