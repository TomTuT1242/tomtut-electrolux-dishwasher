"""Sensor platform for Electrolux Dishwasher."""

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import ElectroluxCoordinator

STATE_LABELS = {
    "OFF": "Aus",
    "IDLE": "Bereit",
    "READY_TO_START": "Startbereit",
    "RUNNING": "Läuft",
    "PAUSED": "Pausiert",
    "DELAYED_START": "Zeitvorwahl",
    "END_OF_CYCLE": "Fertig",
    "ALARM": "Alarm",
}

PHASE_LABELS = {
    "PREWASH": "Vorwäsche",
    "MAINWASH": "Hauptwäsche",
    "HOTRINSE": "Heißspülen",
    "COLDRINSE": "Kaltspülen",
    "EXTRARINSE": "Nachspülen",
    "DRYING": "Trocknung",
    "ADO_DRYING": "Türtrocknung",
    "UNAVAILABLE": "—",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ElectroluxCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DishwasherStateSensor(coordinator, entry),
        DishwasherPhaseSensor(coordinator, entry),
        DishwasherProgramSensor(coordinator, entry),
        DishwasherTimeToEndSensor(coordinator, entry),
        DishwasherFinishTimeSensor(coordinator, entry),
        DishwasherSpokenStatusSensor(coordinator, entry),
        DishwasherAlertsSensor(coordinator, entry),
        DishwasherWifiSensor(coordinator, entry),
    ]
    async_add_entities(entities)


class DishwasherBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for dishwasher."""

    def __init__(self, coordinator: ElectroluxCoordinator, entry: ConfigEntry, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.data['appliance_id']}_{key}"
        self._attr_name = f"{entry.data.get('appliance_name', 'Dishwasher')} {name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["appliance_id"])},
            "name": entry.data.get("appliance_name", "Geschirrspülmaschine"),
            "manufacturer": "AEG/Electrolux",
            "model": "GI8700B2SC 8000 XXL",
            "sw_version": coordinator.reported.get("networkInterface", {}).get("swVersion"),
        }


class DishwasherStateSensor(DishwasherBaseSensor):
    """Appliance state sensor with German label."""

    _attr_icon = "mdi:dishwasher"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "state", "Status")

    @property
    def native_value(self) -> str:
        return self.coordinator.appliance_state

    @property
    def extra_state_attributes(self) -> dict:
        state = self.coordinator.appliance_state
        phase = self.coordinator.cycle_phase
        door = self.coordinator.door_state

        # Detect ADO drying: door open but state still RUNNING or END_OF_CYCLE
        is_ado_drying = phase == "ADO_DRYING" or (door == "OPEN" and state in ("RUNNING", "END_OF_CYCLE"))

        return {
            "state_label": STATE_LABELS.get(state, state),
            "remote_control": self.coordinator.remote_control,
            "connection_state": self.coordinator.connection_state,
            "door_state": door,
            "is_ado_drying": is_ado_drying,
        }


class DishwasherPhaseSensor(DishwasherBaseSensor):
    """Cycle phase sensor with German label."""

    _attr_icon = "mdi:progress-clock"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "cycle_phase", "Phase")

    @property
    def native_value(self) -> str:
        return self.coordinator.cycle_phase

    @property
    def extra_state_attributes(self) -> dict:
        phase = self.coordinator.cycle_phase
        return {
            "phase_label": PHASE_LABELS.get(phase, phase),
        }


class DishwasherProgramSensor(DishwasherBaseSensor):
    """Selected program sensor."""

    _attr_icon = "mdi:format-list-bulleted"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "program", "Programm")

    @property
    def native_value(self) -> str:
        return self.coordinator.program

    @property
    def extra_state_attributes(self) -> dict:
        selections = self.coordinator.reported.get("userSelections", {})
        return {
            k: v for k, v in selections.items()
            if k != "programUID"
        }


class DishwasherTimeToEndSensor(DishwasherBaseSensor):
    """Time to end sensor in minutes."""

    _attr_icon = "mdi:timer-outline"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "time_to_end", "Restzeit")

    @property
    def native_value(self) -> int | None:
        seconds = self.coordinator.time_to_end
        if seconds is None:
            return None
        return round(seconds / 60)

    @property
    def extra_state_attributes(self) -> dict:
        seconds = self.coordinator.time_to_end
        if not seconds:
            return {}
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        if hours > 0:
            formatted = f"{hours}h {mins:02d}min"
        else:
            formatted = f"{mins} min"
        return {
            "seconds": seconds,
            "formatted": formatted,
        }


class DishwasherFinishTimeSensor(DishwasherBaseSensor):
    """Estimated finish time as timestamp."""

    _attr_icon = "mdi:clock-check-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "finish_time", "Fertig um")

    @property
    def native_value(self) -> datetime | None:
        seconds = self.coordinator.time_to_end
        state = self.coordinator.appliance_state
        if seconds is None or state not in ("RUNNING", "DELAYED_START", "PAUSED"):
            return None
        return dt_util.now() + timedelta(seconds=seconds)

    @property
    def extra_state_attributes(self) -> dict:
        seconds = self.coordinator.time_to_end
        state = self.coordinator.appliance_state
        if seconds is None or state not in ("RUNNING", "DELAYED_START", "PAUSED"):
            return {}
        finish = dt_util.now() + timedelta(seconds=seconds)
        return {
            "finish_time_formatted": finish.strftime("%H:%M"),
        }


class DishwasherSpokenStatusSensor(DishwasherBaseSensor):
    """Spoken status for Alexa / voice assistants."""

    _attr_icon = "mdi:microphone-message"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "spoken_status", "Sprachstatus")

    @property
    def native_value(self) -> str:
        state = self.coordinator.appliance_state
        phase = self.coordinator.cycle_phase
        door = self.coordinator.door_state
        seconds = self.coordinator.time_to_end

        if state == "OFF":
            return "Die Spülmaschine ist aus."

        if state == "IDLE":
            return "Die Spülmaschine ist bereit."

        if state == "READY_TO_START":
            return "Die Spülmaschine ist startbereit."

        if state == "DELAYED_START":
            if seconds:
                h, m = divmod(seconds // 60, 60)
                return f"Die Spülmaschine startet in {h} Stunden und {m} Minuten." if h else f"Die Spülmaschine startet in {m} Minuten."
            return "Die Spülmaschine hat eine Zeitvorwahl."

        if state == "RUNNING":
            phase_label = PHASE_LABELS.get(phase, phase)
            if phase == "ADO_DRYING":
                return "Die Spülmaschine ist fertig und trocknet mit offener Tür."
            if seconds:
                finish = dt_util.now() + timedelta(seconds=seconds)
                h, m = divmod(seconds // 60, 60)
                time_str = f"{h} Stunden und {m} Minuten" if h else f"{m} Minuten"
                return f"Die Spülmaschine läuft gerade. Phase: {phase_label}. Noch {time_str}, fertig um {finish.strftime('%H:%M')} Uhr."
            return f"Die Spülmaschine läuft gerade. Phase: {phase_label}."

        if state == "PAUSED":
            return "Die Spülmaschine ist pausiert."

        if state == "END_OF_CYCLE":
            if door == "OPEN":
                return "Die Spülmaschine ist fertig. Die Tür ist offen zum Trocknen."
            return "Die Spülmaschine ist fertig."

        if state == "ALARM":
            return "Die Spülmaschine hat einen Alarm!"

        return f"Spülmaschine Status: {STATE_LABELS.get(state, state)}."


class DishwasherAlertsSensor(DishwasherBaseSensor):
    """Alerts sensor."""

    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "alerts", "Warnungen")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.alerts)

    @property
    def extra_state_attributes(self) -> dict:
        alerts = self.coordinator.alerts
        alert_labels = {
            "DISH_ALARM_SALT_MISSING": "Salz fehlt",
            "DISH_ALARM_RINSE_AID_LOW": "Klarspüler niedrig",
        }
        return {
            "alerts": [
                {
                    "code": a.get("code"),
                    "severity": a.get("severity"),
                    "label": alert_labels.get(a.get("code"), a.get("code")),
                }
                for a in alerts
            ],
            "salt_missing": any(a.get("code") == "DISH_ALARM_SALT_MISSING" for a in alerts),
            "rinse_aid_low": any(a.get("code") == "DISH_ALARM_RINSE_AID_LOW" for a in alerts),
        }


class DishwasherWifiSensor(DishwasherBaseSensor):
    """WiFi quality sensor."""

    _attr_icon = "mdi:wifi"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "wifi", "WLAN")

    @property
    def native_value(self) -> str:
        return self.coordinator.reported.get("networkInterface", {}).get(
            "linkQualityIndicator", "UNKNOWN"
        )
