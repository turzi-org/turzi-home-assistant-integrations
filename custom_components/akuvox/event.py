"""Event platform for Akuvox access events (card, code, face, QR)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import _signal
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# All possible access event types
ALL_ACCESS_EVENT_TYPES = [
    "valid_card",
    "invalid_card",
    "valid_code",
    "invalid_code",
    "valid_face",
    "invalid_face",
    "valid_qr",
    "invalid_qr",
]

# Map model event capabilities to access event types
_EVENT_MAP: dict[str, list[str]] = {
    "card": ["valid_card", "invalid_card"],
    "code": ["valid_code", "invalid_code"],
    "face": ["valid_face", "invalid_face"],
    "qr": ["valid_qr", "invalid_qr"],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Akuvox event entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    mac = data["mac"]
    model_id = data["model_id"]
    model_spec = data["model_spec"]

    # Determine which event types this model supports
    supported_event_types: list[str] = []
    for event_cap in model_spec.get("events", []):
        if event_cap in _EVENT_MAP:
            supported_event_types.extend(_EVENT_MAP[event_cap])

    if not supported_event_types:
        return  # Model doesn't support any access events

    async_add_entities(
        [
            AkuvoxAccessEvent(
                entry_id=entry.entry_id,
                mac=mac,
                model_id=model_id,
                model_spec=model_spec,
                event_types=supported_event_types,
            )
        ]
    )


class AkuvoxAccessEvent(EventEntity):
    """Represents access events from an Akuvox device."""

    _attr_has_entity_name = True
    _attr_device_class = EventDeviceClass.DOORBELL
    _attr_name = "Access Event"

    def __init__(
        self,
        entry_id: str,
        mac: str,
        model_id: str,
        model_spec: dict[str, Any],
        event_types: list[str],
    ) -> None:
        """Initialize the access event entity."""
        self._entry_id = entry_id
        self._mac = mac
        self._model_id = model_id
        self._model_spec = model_spec
        self._attr_unique_id = f"akuvox_{mac}_access_event"
        self._attr_event_types = event_types

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
        if event_data.get("type") != "access":
            return

        access_type = event_data.get("access_type", "")
        access_data = event_data.get("access_data", "")

        if access_type not in self._attr_event_types:
            _LOGGER.debug(
                "Ignoring unsupported access event type: %s", access_type
            )
            return

        # Build event data dict
        event_attrs: dict[str, Any] = {}
        if access_data:
            # Determine the key based on event type
            if "card" in access_type:
                event_attrs["card_sn"] = access_data
            elif "code" in access_type:
                event_attrs["code"] = access_data
            elif "face" in access_type:
                event_attrs["unlock_type"] = access_data
            elif "qr" in access_type:
                event_attrs["qr_code"] = access_data

        self._trigger_event(access_type, event_attrs)
        self.async_write_ha_state()
        _LOGGER.debug(
            "Access event fired: type=%s, data=%s", access_type, event_attrs
        )
