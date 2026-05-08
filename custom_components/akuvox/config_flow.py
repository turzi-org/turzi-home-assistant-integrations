"""Config flow for the Akuvox integration."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS, CONF_PASSWORD, CONF_USERNAME

from .const import (
    CONF_API_PASSWORD,
    CONF_API_USERNAME,
    CONF_DEVICE_IP,
    CONF_INPUT_DEVICE_CLASS,
    CONF_INPUT_NAME,
    CONF_INPUTS,
    CONF_MAC_ADDRESS,
    CONF_MODEL,
    CONF_RELAY_DEVICE_CLASS,
    CONF_RELAY_IS_LOCK,
    CONF_RELAY_LOCK_DELAY,
    CONF_RELAY_LOCK_LEVEL,
    CONF_RELAY_NAME,
    CONF_RELAYS,
    DEFAULT_LOCK_DELAY,
    DEFAULT_RELAY_LEVEL,
    DOMAIN,
    INPUT_DEVICE_CLASSES,
    MODEL_REGISTRY,
    RELAY_DEVICE_CLASSES,
    RELAY_LETTERS,
)


def _normalize_mac(mac: str) -> str:
    """Normalize a MAC address to lowercase without separators."""
    return re.sub(r"[:\-\.]", "", mac.strip()).lower()


class AkuvoxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Akuvox."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict[str, Any] = {}
        self._model_spec: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Device info (model, MAC, IP, credentials)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mac_normalized = _normalize_mac(user_input[CONF_MAC_ADDRESS])

            # Validate MAC format
            if len(mac_normalized) != 12 or not all(
                c in "0123456789abcdef" for c in mac_normalized
            ):
                errors[CONF_MAC_ADDRESS] = "invalid_mac"
            else:
                # Check uniqueness
                await self.async_set_unique_id(mac_normalized)
                self._abort_if_unique_id_configured()

                self._data = {
                    CONF_MODEL: user_input[CONF_MODEL],
                    CONF_MAC_ADDRESS: mac_normalized,
                    CONF_DEVICE_IP: user_input[CONF_DEVICE_IP],
                    CONF_API_USERNAME: user_input.get(CONF_API_USERNAME, ""),
                    CONF_API_PASSWORD: user_input.get(CONF_API_PASSWORD, ""),
                }
                self._model_spec = MODEL_REGISTRY[user_input[CONF_MODEL]]

                # Go to relay config if there are relays
                if self._model_spec["relays"] > 0:
                    return await self.async_step_relays()
                # Otherwise go to inputs
                if self._model_spec["inputs"] > 0:
                    return await self.async_step_inputs()
                # No relays or inputs — just create
                return self._create_entry()

        model_options = {
            model_id: spec["name"]
            for model_id, spec in MODEL_REGISTRY.items()
        }

        schema = vol.Schema(
            {
                vol.Required(CONF_MODEL): vol.In(model_options),
                vol.Required(CONF_MAC_ADDRESS): str,
                vol.Required(CONF_DEVICE_IP): str,
                vol.Optional(CONF_API_USERNAME, default="admin"): str,
                vol.Optional(CONF_API_PASSWORD, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_relays(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Configure relays (name, device class, lock option)."""
        num_relays = self._model_spec["relays"]

        if user_input is not None:
            relays_config = []
            for i in range(num_relays):
                idx = i + 1
                relay_cfg = {
                    CONF_RELAY_NAME: user_input.get(
                        f"relay_{idx}_name", f"Relay {RELAY_LETTERS[i]}"
                    ),
                    CONF_RELAY_DEVICE_CLASS: user_input.get(
                        f"relay_{idx}_device_class", "switch"
                    ),
                    CONF_RELAY_IS_LOCK: user_input.get(
                        f"relay_{idx}_is_lock", False
                    ),
                    CONF_RELAY_LOCK_DELAY: user_input.get(
                        f"relay_{idx}_lock_delay", DEFAULT_LOCK_DELAY
                    ),
                    CONF_RELAY_LOCK_LEVEL: user_input.get(
                        f"relay_{idx}_lock_level", DEFAULT_RELAY_LEVEL
                    ),
                }
                relays_config.append(relay_cfg)

            self._data[CONF_RELAYS] = relays_config

            # Go to inputs if there are any
            if self._model_spec["inputs"] > 0:
                return await self.async_step_inputs()
            return self._create_entry()

        # Build dynamic schema for relays
        schema_dict: dict[Any, Any] = {}
        for i in range(num_relays):
            idx = i + 1
            letter = RELAY_LETTERS[i]
            schema_dict[
                vol.Optional(f"relay_{idx}_name", default=f"Relay {letter}")
            ] = str
            schema_dict[
                vol.Optional(f"relay_{idx}_device_class", default="switch")
            ] = vol.In(RELAY_DEVICE_CLASSES)
            schema_dict[
                vol.Optional(f"relay_{idx}_is_lock", default=False)
            ] = bool
            schema_dict[
                vol.Optional(f"relay_{idx}_lock_delay", default=DEFAULT_LOCK_DELAY)
            ] = vol.All(vol.Coerce(int), vol.Range(min=0, max=65535))
            schema_dict[
                vol.Optional(f"relay_{idx}_lock_level", default=DEFAULT_RELAY_LEVEL)
            ] = vol.In({0: "NC-COM (Normally Closed)", 1: "NO-COM (Normally Open)"})

        return self.async_show_form(
            step_id="relays",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_inputs(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3: Configure inputs (name, device class)."""
        num_inputs = self._model_spec["inputs"]

        if user_input is not None:
            inputs_config = []
            for i in range(num_inputs):
                idx = i + 1
                input_cfg = {
                    CONF_INPUT_NAME: user_input.get(
                        f"input_{idx}_name", f"Input {RELAY_LETTERS[i]}"
                    ),
                    CONF_INPUT_DEVICE_CLASS: user_input.get(
                        f"input_{idx}_device_class", "door"
                    ),
                }
                inputs_config.append(input_cfg)

            self._data[CONF_INPUTS] = inputs_config
            return self._create_entry()

        # Build dynamic schema for inputs
        schema_dict: dict[Any, Any] = {}
        for i in range(num_inputs):
            idx = i + 1
            letter = RELAY_LETTERS[i]
            schema_dict[
                vol.Optional(f"input_{idx}_name", default=f"Input {letter}")
            ] = str
            schema_dict[
                vol.Optional(f"input_{idx}_device_class", default="door")
            ] = vol.In(INPUT_DEVICE_CLASSES)

        return self.async_show_form(
            step_id="inputs",
            data_schema=vol.Schema(schema_dict),
        )

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        model_spec = MODEL_REGISTRY[self._data[CONF_MODEL]]
        title = f"{model_spec['name']} ({self._data[CONF_MAC_ADDRESS]})"
        return self.async_create_entry(title=title, data=self._data)
