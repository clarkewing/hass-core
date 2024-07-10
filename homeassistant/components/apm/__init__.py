"""The APM CrewConnect integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from apm_crewconnect import Apm

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.util import Throttle

from .const import CONF_APM_TOKEN, CONF_OKTA_TOKEN, DOMAIN
from .services import async_register_services

PLATFORMS: list[Platform] = [Platform.CALENDAR]
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=300)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up APM CrewConnect from a config entry."""
    host = entry.data[CONF_HOST]

    data = ApmData(hass, entry, host)

    await data.update()

    hass.data[DOMAIN] = data

    # await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN)
    return unload_ok


class ApmData:
    """Handle getting the latest data from APM so platforms can use it.

    Also handle refreshing tokens and updating config entry with refreshed tokens.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        host: str,
    ) -> None:
        """Initialize the APM data object."""
        self._hass = hass
        self.entry = entry
        self.apm = self._hass.async_add_executor_job(
            lambda: Apm(host=host, token_manager=TokenManager(hass, entry))
        )

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update(self):
        """Get the latest data from APM."""
        await self._hass.async_add_executor_job(self.apm.update)


class TokenManager:
    """Token Manager implementation for APM CrewConnect."""

    _tokens: dict[str, dict[str, Any]] = {}

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the Token Manager."""
        self.hass = hass
        self.config_entry = config_entry
        self._retrieve()

    def set(self, **kwargs) -> None:
        """Set a token."""
        if "key" in kwargs:
            self._tokens[kwargs["key"]] = kwargs["value"]
        else:
            self._tokens = kwargs["value"]

        self._store()

    def get(
        self, key: str | None = None
    ) -> dict[str, Any] | dict[str, dict[str, Any]] | None:
        """Get a token."""
        if key is None:
            return self._tokens

        return self._tokens.get(key)

    def has(self, key: str) -> bool:
        """Determine if a specific token is held."""
        return self.get(key) is not None

    def _store(self) -> None:
        data = dict(self.config_entry.data)
        data[CONF_APM_TOKEN] = self._tokens["apm"]
        data[CONF_OKTA_TOKEN] = self._tokens["okta"]

        self.hass.config_entries.async_update_entry(self.config_entry, data=data)

    def _retrieve(self) -> None:
        self._tokens = {}

        if self.config_entry.data.get(CONF_APM_TOKEN):
            self._tokens["apm"] = self.config_entry.data[CONF_APM_TOKEN]

        if self.config_entry.data.get(CONF_OKTA_TOKEN):
            self._tokens["okta"] = self.config_entry.data[CONF_OKTA_TOKEN]
