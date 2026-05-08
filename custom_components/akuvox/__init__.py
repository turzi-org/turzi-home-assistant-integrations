"""The Akuvox integration."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web
from homeassistant.components import webhook
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .api_client import AkuvoxApiClient
from .const import (
    CONF_API_PASSWORD,
    CONF_API_USERNAME,
    CONF_DEVICE_IP,
    CONF_MAC_ADDRESS,
    CONF_MODEL,
    DOMAIN,
    MODEL_REGISTRY,
    PLATFORMS,
    WEBHOOK_ID_PREFIX,
)

_LOGGER = logging.getLogger(__name__)

# Dispatcher signal format for entity state updates
SIGNAL_AKUVOX_EVENT = f"{DOMAIN}_event_{{entry_id}}"


def _webhook_id(mac: str) -> str:
    """Build the webhook ID from a normalized MAC address."""
    return f"{WEBHOOK_ID_PREFIX}{mac}"


def _signal(entry_id: str) -> str:
    """Build the dispatcher signal name for an entry."""
    return SIGNAL_AKUVOX_EVENT.format(entry_id=entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Akuvox from a config entry."""
    mac = entry.data[CONF_MAC_ADDRESS]
    model_id = entry.data[CONF_MODEL]
    model_spec = MODEL_REGISTRY[model_id]
    device_ip = entry.data[CONF_DEVICE_IP]
    username = entry.data.get(CONF_API_USERNAME)
    password = entry.data.get(CONF_API_PASSWORD)

    session = aiohttp_client.async_get_clientsession(hass)
    api_client = AkuvoxApiClient(device_ip, username, password, session)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "api_client": api_client,
        "model_spec": model_spec,
        "model_id": model_id,
        "mac": mac,
        "device_ip": device_ip,
    }

    # Register webhook to receive events from the device
    wh_id = _webhook_id(mac)
    webhook.async_register(
        hass,
        DOMAIN,
        f"Akuvox {model_spec['name']}",
        wh_id,
        _build_webhook_handler(hass, entry.entry_id),
    )
    _LOGGER.info(
        "Registered Akuvox webhook: /api/webhook/%s for %s (%s)",
        wh_id,
        model_spec["name"],
        mac,
    )

    # Forward setup to entity platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Akuvox config entry."""
    mac = entry.data[CONF_MAC_ADDRESS]
    webhook.async_unregister(hass, _webhook_id(mac))

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


def _build_webhook_handler(hass: HomeAssistant, entry_id: str):
    """Build a webhook handler closure for a specific config entry."""

    async def _handle_webhook(
        hass_: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle incoming webhook from an Akuvox device."""
        # Parse query parameters (GET) or form body (POST)
        if request.method == "POST":
            try:
                params = await request.post()
            except Exception:
                params = request.query
        else:
            params = request.query

        entity = params.get("entity", "")
        state_raw = params.get("state", "")
        mac = params.get("mac", "")
        ip_addr = params.get("ip", "")

        # Access event params
        card = params.get("card", "")
        invalid_card = params.get("invalid_card", "")
        code = params.get("code", "")
        invalid_code = params.get("invalid_code", "")
        face = params.get("face", "")
        invalid_face = params.get("invalid_face", "")
        qr = params.get("qr", "")
        invalid_qr = params.get("invalid_qr", "")

        _LOGGER.debug(
            "Akuvox webhook received: entity=%s, state=%s, mac=%s, ip=%s, "
            "card=%s, code=%s, face=%s",
            entity,
            state_raw,
            mac,
            ip_addr,
            card or invalid_card,
            code or invalid_code,
            face or invalid_face,
        )

        # Parse state to bool
        try:
            state = int(state_raw) == 1 if state_raw else None
        except (ValueError, TypeError):
            state = None

        # Build event data for dispatcher
        event_data: dict[str, Any] = {
            "entity": entity,
            "state": state,
            "mac": mac,
            "ip": ip_addr,
        }

        # Determine event type from entity prefix and params
        if entity.startswith("relay"):
            event_data["type"] = "relay"
            event_data["entity_key"] = entity  # e.g., "relay1"
        elif entity.startswith("input"):
            event_data["type"] = "input"
            event_data["entity_key"] = entity  # e.g., "input1"
        elif entity == "tamper":
            event_data["type"] = "tamper"
            event_data["entity_key"] = "tamper"
        elif entity == "access":
            event_data["type"] = "access"
            event_data["entity_key"] = "access"
            # Determine access event subtype
            if card:
                event_data["access_type"] = "valid_card"
                event_data["access_data"] = card
            elif invalid_card:
                event_data["access_type"] = "invalid_card"
                event_data["access_data"] = invalid_card
            elif code:
                event_data["access_type"] = "valid_code"
                event_data["access_data"] = code
            elif invalid_code:
                event_data["access_type"] = "invalid_code"
                event_data["access_data"] = invalid_code
            elif face:
                event_data["access_type"] = "valid_face"
                event_data["access_data"] = face
            elif invalid_face:
                event_data["access_type"] = "invalid_face"
                event_data["access_data"] = invalid_face
            elif qr:
                event_data["access_type"] = "valid_qr"
                event_data["access_data"] = qr
            elif invalid_qr:
                event_data["access_type"] = "invalid_qr"
                event_data["access_data"] = invalid_qr
        elif entity.startswith("breakin"):
            event_data["type"] = "breakin"
            event_data["entity_key"] = entity  # e.g., "breakin1"
        else:
            _LOGGER.warning("Unknown entity in webhook: %s", entity)
            return web.Response(text="Unknown entity", status=400)

        # Dispatch to all entities listening for this entry's events
        async_dispatcher_send(hass_, _signal(entry_id), event_data)

        return web.Response(text="OK", status=200)

    return _handle_webhook
