"""API client for Akuvox devices."""

from __future__ import annotations

import logging

import aiohttp

_LOGGER = logging.getLogger(__name__)


class AkuvoxApiClient:
    """HTTP client for controlling Akuvox devices via POST /api."""

    def __init__(
        self,
        device_ip: str,
        username: str | None,
        password: str | None,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client.

        Args:
            device_ip: IP address of the Akuvox device.
            username: API username (optional).
            password: API password (optional).
            session: aiohttp client session.
        """
        self._base_url = f"http://{device_ip}"
        self._session = session
        self._auth = (
            aiohttp.BasicAuth(username or "", password or "")
            if username
            else None
        )

    async def async_trigger_relay(
        self,
        relay_num: int,
        mode: int = 0,
        level: int = 0,
        delay: int = 3,
    ) -> bool:
        """Trigger a relay on the device.

        Args:
            relay_num: Relay number (1=A, 2=B, 3=C, 4=D).
            mode: 0=auto-close (relay re-latches after delay),
                  1=manual (stays open until toggled).
            level: 0=NC-COM (normally closed), 1=NO-COM (normally open).
            delay: Auto-close delay in seconds (0-65535). Only for mode=0.

        Returns:
            True if the API call succeeded.
        """
        url = f"{self._base_url}/api"
        payload = {
            "target": "relay",
            "action": "trig",
            "data": {
                "mode": mode,
                "num": relay_num,
                "level": level,
                "delay": delay,
            },
        }

        try:
            async with self._session.post(
                url, json=payload, auth=self._auth, ssl=False
            ) as resp:
                if resp.status == 200:
                    _LOGGER.debug(
                        "Relay %d triggered successfully (mode=%d, delay=%d)",
                        relay_num,
                        mode,
                        delay,
                    )
                    return True
                _LOGGER.error(
                    "Failed to trigger relay %d: HTTP %d", relay_num, resp.status
                )
                return False
        except aiohttp.ClientError as err:
            _LOGGER.error("Error communicating with Akuvox device: %s", err)
            return False
