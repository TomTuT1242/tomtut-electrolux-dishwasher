"""Data update coordinator for Electrolux Dishwasher."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ElectroluxApi
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ElectroluxCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from the Electrolux OCP API."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ElectroluxApi,
        appliance_id: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self.api = api
        self.appliance_id = appliance_id

    async def _async_update_data(self) -> dict:
        """Fetch data from API."""
        try:
            data = await self.api.get_appliance(self.appliance_id)
            return data
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    @property
    def reported(self) -> dict:
        """Get reported properties."""
        if not self.data:
            return {}
        return self.data.get("properties", {}).get("reported", {})

    @property
    def appliance_state(self) -> str:
        """Get appliance state."""
        return self.reported.get("applianceState", "UNKNOWN")

    @property
    def cycle_phase(self) -> str:
        return self.reported.get("cyclePhase", "UNAVAILABLE")

    @property
    def door_state(self) -> str:
        return self.reported.get("doorState", "UNKNOWN")

    @property
    def time_to_end(self) -> int | None:
        val = self.reported.get("timeToEnd")
        return val if val and val > 0 else None

    @property
    def program(self) -> str:
        return self.reported.get("userSelections", {}).get("programUID", "UNKNOWN")

    @property
    def remote_control(self) -> str:
        return self.reported.get("remoteControl", "UNKNOWN")

    @property
    def connection_state(self) -> str:
        return self.reported.get("connectivityState", "unknown")

    @property
    def alerts(self) -> list:
        return self.reported.get("alerts", [])

    @property
    def is_running(self) -> bool:
        return self.appliance_state == "RUNNING"

    async def send_command(self, command: str) -> None:
        """Send command and refresh data."""
        await self.api.send_command(self.appliance_id, command)
        await asyncio.sleep(2)
        await self.async_request_refresh()
