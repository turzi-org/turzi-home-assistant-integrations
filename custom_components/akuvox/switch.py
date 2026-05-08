"""Switch platform for Akuvox relays."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import _signal
from .const import (
    CONF_MAC_ADDRESS,
    CONF_MODEL,
    CONF_RELAY_DEVICE_CLASS,
    CONF_RELAY_NAME,
    CONF_RELAYS,
    DOMAIN,
    MODEL_REGISTRY,
    RELAY_LETTERS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Akuvox switch entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    api_client = data["api_client"]
    mac = data["mac"]
    model_id = data["model_id"]
    model_spec = data["model_spec"]
    relays_config = entry.data.get(CONF_RELAYS, [])

    entities: list[AkuvoxRelaySwitch] = []
    for i in range(model_spec["relays"]):
        relay_num = i + 1
        relay_cfg = relays_config[i] if i < len(relays_config) else {}
        name = relay_cfg.get(CONF_RELAY_NAME, f"Relay {RELAY_LETTERS[i]}")
        device_class = relay_cfg.get(CONF_RELAY_DEVICE_CLASS, "switch")

        entities.append(
            AkuvoxRelaySwitch(
                entry_id=entry.entry_id,
                mac=mac,
                model_id=model_id,
                model_spec=model_spec,
                api_client=api_client,
                relay_num=relay_num,
                name=name,
                device_class_str=device_class,
            )
        )

    async_add_entities(entities)


class AkuvoxRelaySwitch(SwitchEntity):
    """Represents an Akuvox relay as a switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry_id: str,
        mac: str,
        model_id: str,
        model_spec: dict[str, Any],
        api_client: Any,
        relay_num: int,
        name: str,
        device_class_str: str,
    ) -> None:
        """Initialize the relay switch."""
        self._entry_id = entry_id
        self._mac = mac
        self._model_id = model_id
        self._model_spec = model_spec
        self._api_client = api_client
        self._relay_num = relay_num
        self._attr_name = name
        self._attr_unique_id = f"akuvox_{mac}_relay_{relay_num}"
        self._attr_is_on = False
        self._entity_key = f"relay{relay_num}"

        # Map device class string to enum
        if device_class_str == "outlet":
            self._attr_device_class = SwitchDeviceClass.OUTLET
        else:
            self._attr_device_class = SwitchDeviceClass.SWITCH

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info to link this entity to the device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._mac)},
            name=self._model_spec["name"],
            manufacturer="Akuvox",
            model=self._model_id,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to dispatcher signals when added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, _signal(self._entry_id), self._handle_event
            )
        )

    @callback
    def _handle_event(self, event_data: dict[str, Any]) -> None:
        """Handle a webhook event for this entity."""
        if event_data.get("entity_key") != self._entity_key:
            return
        if event_data.get("type") != "relay":
            return

        state = event_data.get("state")
        if state is not None:
            self._attr_is_on = state
            self.async_write_ha_state()
            _LOGGER.debug(
                "Relay %s state updated to %s via webhook",
                self._entity_key,
                "ON" if state else "OFF",
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the relay on (manual mode, stays on)."""
        await self._api_client.async_trigger_relay(
            relay_num=self._relay_num, mode=1
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the relay off (manual mode, toggle back)."""
        await self._api_client.async_trigger_relay(
            relay_num=self._relay_num, mode=1
        )
