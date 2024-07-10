"""Config flow for APM CrewConnect integration."""

from __future__ import annotations

import logging
from typing import Any

from apm_crewconnect import Apm
from apm_crewconnect.exceptions import InvalidAuthRedirectException
from requests.exceptions import ConnectionError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .const import CONF_APM_TOKEN, CONF_AUTH_REDIRECT, CONF_OKTA_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ApmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for APM CrewConnect."""

    VERSION = 1

    _apm: Apm | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                self._apm: Apm = await self.hass.async_add_executor_job(
                    lambda: Apm(
                        host=user_input[CONF_HOST],
                        manual_auth=True,
                    )
                )
            except ConnectionError:
                errors["base"] = "cannot_connect"

            if self._apm is not None:
                return await self.async_step_authorize()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                }
            ),
            errors=errors,
        )

    async def async_step_authorize(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Present the user with the authorization URL to obtain a redirect URL and obtain tokens."""
        errors = {}

        assert isinstance(self._apm, Apm)

        if user_input is not None:
            # Attempt to obtain tokens from APM and finish the flow.
            try:
                await self.hass.async_add_executor_job(
                    self._apm.authenticate_from_redirect, user_input[CONF_AUTH_REDIRECT]
                )

                # Tokens obtained; create the config entry.
                return self.async_create_entry(
                    title=self._apm.user_id,
                    data={
                        CONF_HOST: self._apm.host,
                        CONF_APM_TOKEN: self._apm.client.token,
                        CONF_OKTA_TOKEN: self._apm.client.okta_client.token,
                    },
                )
            except InvalidAuthRedirectException:
                errors["base"] = "invalid_auth_redirect"

        auth_url = await self.hass.async_add_executor_job(self._apm.generate_auth_url)

        return self.async_show_form(
            step_id="authorize",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_AUTH_REDIRECT): str,
                }
            ),
            errors=errors,
            description_placeholders={"auth_url": auth_url},
        )
