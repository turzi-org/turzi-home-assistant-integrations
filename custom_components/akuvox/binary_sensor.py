"""Binary sensor platform for Akuvox inputs, tamper, and break-in alarms."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import _signal
from .const import (
    CONF_INPUT_DEVICE_CLASS,
    CONF_INPUT_NAME,
    CONF_INPUTS,
    CONF_MAC_ADDRESS,
    CONF_MODEL,
    DOMAIN,
    MODEL_REGISTRY,
    RELAY_LETTERS,
)

_LOGGER = logging.getLogger(__name__)

# Map string device class names to BinarySensorDeviceClass enum
_DEVICE_CLASS_MAP: dict[str, BinarySensorDeviceClass] = {
    "door": BinarySensorDeviceClass.DOOR,
    "window": BinarySensorDeviceClass.WINDOW,
    "motion": BinarySensorDeviceClass.MOTION,
    "garage_door": BinarySensorDeviceClass.GARAGE_DOOR,
    "opening": BinarySensorDeviceClass.OPENING,
    "safety": BinarySensorDeviceClass.SAFETY,
    "tamper": BinarySensorDeviceClass.TAMPER,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Akuvox binary sensor entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    mac = data["mac"]
    model_id = data["model_id"]
    model_spec = data["model_spec"]
    inputs_config = entry.data.get(CONF_INPUTS, [])

    entities: list[BinarySensorEntity] = []

    # Input sensors
    for i in range(model_spec["inputs"]):
        input_num = i + 1
        input_cfg = inputs_config[i] if i < len(inputs_config) else {}
        name = input_cfg.get(CONF_INPUT_NAME, f"Input {RELAY_LETTERS[i]}")
        device_class_str = input_cfg.get(CONF_INPUT_DEVICE_CLASS, "door")

        entities.append(
            AkuvoxInputSensor(
                entry_id=entry.entry_id,
                mac=mac,
                model_id=model_id,
                model_spec=model_spec,
                input_num=input_num,
                name=name,
                device_class_str=device_class_str,
            )
        )

    # Tamper sensor
    if model_spec.get("tamper"):
        entities.append(
            AkuvoxTamperSensor(
                entry_id=entry.entry_id,
                mac=mac,
                model_id=model_id,
                model_spec=model_spec,
            )
        )

    # Break-in alarm sensors (for models that support break-in events)
    if "breakin" in model_spec.get("events", []):
        for i in range(model_spec["inputs"]):
            input_num = i + 1
            entities.append(
                AkuvoxBreakinSensor(
                    entry_id=entry.entry_id,
                    mac=mac,
                    model_id=model_id,
                    model_spec=model_spec,
                    input_num=input_num,
                )
            )

    async_add_entities(entities)


class AkuvoxInputSensor(BinarySensorEntity):
    """Represents an Akuvox dry-contact input as a binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry_id: str,
        mac: str,
        model_id: str,
        model_spec: dict[str, Any],
        input_num: int,
        name: str,
        device_class_str: str,
    ) -> None:
        """Initialize the input sensor."""
        self._entry_id = entry_id
        self._mac = mac
        self._model_id = model_id
        self._model_spec = model_spec
        self._input_num = input_num
        self._attr_name = name
        self._attr_unique_id = f"akuvox_{mac}_input_{input_num}"
        self._attr_is_on = False
        self._entity_key = f"input{input_num}"
        self._attr_device_class = _DEVICE_CLASS_MAP.get(device_class_str)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name=self._model_spec["name"],
            manufacturer="Akuvox",
            model=self._model_id,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to dispatcher signals."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, _signal(self._entry_id), self._handle_event
            )
        )

    @callback
    def _handle_event(self, event_data: dict[str, Any]) -> None:
        """Handle a webhook event."""
        if event_data.get("entity_key") != self._entity_key:
            return
        if event_data.get("type") != "input":
            return

        state = event_data.get("state")
        if state is not None:
            self._attr_is_on = state
            self.async_write_ha_state()


class AkuvoxTamperSensor(BinarySensorEntity):
    """Represents the Akuvox device tamper alarm."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.TAMPER

    def __init__(
        self,
        entry_id: str,
        mac: str,
        model_id: str,
        model_spec: dict[str, Any],
    ) -> None:
        """Initialize the tamper sensor."""
        self._entry_id = entry_id
        self._mac = mac
        self._model_id = model_id
        self._model_spec = model_spec
        self._attr_name = "Tamper"
        self._attr_unique_id = f"akuvox_{mac}_tamper"
        self._attr_is_on = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name=self._model_spec["name"],
            manufacturer="Akuvox",
            model=self._model_id,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to dispatcher signals."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, _signal(self._entry_id), self._handle_event
            )
        )

    @callback
    def _handle_event(self, event_data: dict[str, Any]) -> None:
        """Handle a webhook event."""
        if event_data.get("type") != "tamper":
            return
        state = event_data.get("state")
        if state is not None:
            self._attr_is_on = state
            self.async_write_ha_state()


class AkuvoxBreakinSensor(BinarySensorEntity):
    """Represents a break-in alarm for an Akuvox input."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.TAMPER

    def __init__(
        self,
        entry_id: str,
        mac: str,
        model_id: str,
        model_spec: dict[str, Any],
        input_num: int,
    ) -> None:
        """Initialize the break-in sensor."""
        self._entry_id = entry_id
        self._mac = mac
        self._model_id = model_id
        self._model_spec = model_spec
        self._input_num = input_num
        self._attr_name = f"Break-in Alarm {chr(64 + input_num)}"
        self._attr_unique_id = f"akuvox_{mac}_breakin_{input_num}"
        self._attr_is_on = False
        self._entity_key = f"breakin{input_num}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name=self._model_spec["name"],
            manufacturer="Akuvox",
            model=self._model_id,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to dispatcher signals."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, _signal(self._entry_id), self._handle_event
            )
        )

    @callback
    def _handle_event(self, event_data: dict[str, Any]) -> None:
        """Handle a webhook event."""
        if event_data.get("entity_key") != self._entity_key:
            return
        if event_data.get("type") != "breakin":
            return
        state = event_data.get("state")
        if state is not None:
            self._attr_is_on = state
            self.async_write_ha_state()
