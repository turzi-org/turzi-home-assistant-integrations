"""Lock platform for Akuvox relays configured as locks."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import _signal
from .const import (
    CONF_RELAY_IS_LOCK,
    CONF_RELAY_LOCK_DELAY,
    CONF_RELAY_LOCK_LEVEL,
    CONF_RELAY_NAME,
    CONF_RELAYS,
    DEFAULT_LOCK_DELAY,
    DEFAULT_RELAY_LEVEL,
    DOMAIN,
    RELAY_LETTERS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Akuvox lock entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    api_client = data["api_client"]
    mac = data["mac"]
    model_id = data["model_id"]
    model_spec = data["model_spec"]
    relays_config = entry.data.get(CONF_RELAYS, [])

    entities: list[AkuvoxLock] = []
    for i, relay_cfg in enumerate(relays_config):
        if not relay_cfg.get(CONF_RELAY_IS_LOCK, False):
            continue

        relay_num = i + 1
        name = relay_cfg.get(CONF_RELAY_NAME, f"Lock {RELAY_LETTERS[i]}")
        delay = relay_cfg.get(CONF_RELAY_LOCK_DELAY, DEFAULT_LOCK_DELAY)
        level = relay_cfg.get(CONF_RELAY_LOCK_LEVEL, DEFAULT_RELAY_LEVEL)

        entities.append(
            AkuvoxLock(
                entry_id=entry.entry_id,
                mac=mac,
                model_id=model_id,
                model_spec=model_spec,
                api_client=api_client,
                relay_num=relay_num,
                name=name,
                delay=delay,
                level=level,
            )
        )

    async_add_entities(entities)


class AkuvoxLock(LockEntity):
    """Represents an Akuvox relay configured as a lock."""

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
        delay: int,
        level: int,
    ) -> None:
        """Initialize the lock."""
        self._entry_id = entry_id
        self._mac = mac
        self._model_id = model_id
        self._model_spec = model_spec
        self._api_client = api_client
        self._relay_num = relay_num
        self._delay = delay
        self._level = level
        self._attr_name = name
        self._attr_unique_id = f"akuvox_{mac}_lock_{relay_num}"
        self._attr_is_locked = True
        self._entity_key = f"relay{relay_num}"

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
        """Handle a webhook event for the relay this lock wraps."""
        if event_data.get("entity_key") != self._entity_key:
            return
        if event_data.get("type") != "relay":
            return

        state = event_data.get("state")
        if state is not None:
            # Relay triggered (state=True) means unlocked
            # Relay closed (state=False) means locked
            self._attr_is_locked = not state
            self.async_write_ha_state()
            _LOGGER.debug(
                "Lock %s state updated to %s via webhook",
                self._entity_key,
                "UNLOCKED" if not self._attr_is_locked else "LOCKED",
            )

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock (trigger relay with auto-relock)."""
        await self._api_client.async_trigger_relay(
            relay_num=self._relay_num,
            mode=0,  # Auto-close after delay
            level=self._level,
            delay=self._delay,
        )

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock.

        With auto-relock (mode=0), this is typically a no-op since
        the device re-latches automatically. We send a trigger with
        mode=1 to force the relay closed if needed.
        """
        # The device auto-relocks when mode=0, but if the user
        # explicitly locks, we trigger with mode=1 to close
        await self._api_client.async_trigger_relay(
            relay_num=self._relay_num,
            mode=1,  # Manual mode to toggle state
            level=self._level,
            delay=0,
        )
