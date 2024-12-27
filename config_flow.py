"""Config flow for acre Intrusion integration."""
from __future__ import annotations

import logging
from typing import Any

from pyspcwebgw import SpcWebGateway
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import (
    DOMAIN,
    CONF_WS_URL,
    CONF_API_URL,
    CONF_USERNAME,
    CONF_PIN,
    CONF_ADMIN_PIN,
)
from .storage import PinStorage

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_WS_URL): str,
    vol.Required(CONF_API_URL): str,
})

PIN_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_ADMIN_PIN): str,
})

USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_USERNAME): str,
    vol.Required(CONF_PIN): str,
})

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for acre Intrusion."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    def __init__(self):
        """Initialize the config flow."""
        self._config = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step - API configuration."""
        errors = {}

        if user_input is not None:
            try:
                # Test connection
                session = aiohttp_client.async_get_clientsession(self.hass)
                spc = SpcWebGateway(
                    loop=self.hass.loop,
                    session=session,
                    api_url=user_input[CONF_API_URL],
                    ws_url=user_input[CONF_WS_URL],
                    async_callback=None,
                )

                if await spc.async_load_parameters():
                    self._config.update(user_input)
                    # Proceed to admin PIN setup
                    return await self.async_step_admin_setup()
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_admin_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle admin PIN setup."""
        errors = {}

        if user_input is not None:
            pin = user_input[CONF_ADMIN_PIN]
            if len(pin) == 6 and pin.isdigit():
                pin_storage = PinStorage(self.hass)
                await pin_storage.async_load()
                await pin_storage.async_store_admin_pin(pin)
                return self.async_create_entry(
                    title="Acre Intrusion",
                    data=self._config
                )
            else:
                errors["base"] = "invalid_pin"

        return self.async_show_form(
            step_id="admin_setup",
            data_schema=PIN_DATA_SCHEMA,
            errors=errors,
        )

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for acre Intrusion."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._admin_verified = False
        self._selected_username = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Initial step - verify admin PIN."""
        if self._admin_verified:
            return await self.async_step_menu()

        errors = {}
        pin_storage = PinStorage(self.hass)
        await pin_storage.async_load()

        if user_input is not None:
            if pin_storage.verify_admin_pin(user_input[CONF_ADMIN_PIN]):
                self._admin_verified = True
                return await self.async_step_menu()
            errors["base"] = "invalid_admin_pin"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_ADMIN_PIN): str,
            }),
            errors=errors,
        )

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show menu for managing users and PINs."""
        pin_storage = PinStorage(self.hass)
        await pin_storage.async_load()
        users = pin_storage.get_users()
        user_list = [user for user in users if user != 'admin']
        user_display = f"Current users: {', '.join(user_list)}" if user_list else "No users configured"

        if user_input is not None:
            action = user_input.get("action")
            if action == "add_user":
                return await self.async_step_add_user()
            elif action == "modify_user":
                return await self.async_step_select_user()
            elif action == "remove_user":
                return await self.async_step_remove_user()
            elif action == "change_admin":
                return await self.async_step_change_admin()
            elif action == "exit":
                self._admin_verified = False
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="menu",
            data_schema=vol.Schema({
                vol.Required("action", default="add_user"): vol.In({
                    "add_user": "Add new user",
                    "modify_user": "Modify existing user" if user_list else "No users to modify",
                    "remove_user": "Remove user" if user_list else "No users to remove",
                    "change_admin": "Change admin PIN",
                    "exit": "Exit menu"
                }),
            }),
            description_placeholders={
                "existing_users": user_display
            },
        )

    async def async_step_add_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new user."""
        errors = {}

        if user_input is not None:
            pin = user_input[CONF_PIN]
            if len(pin) == 6 and pin.isdigit():
                pin_storage = PinStorage(self.hass)
                await pin_storage.async_load()
                await pin_storage.async_store_pin(user_input[CONF_USERNAME], pin)
                if user_input.get("add_another"):
                    return await self.async_step_add_user()
                return await self.async_step_menu()
            errors["base"] = "invalid_pin"

        return self.async_show_form(
            step_id="add_user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PIN): str,
                vol.Optional("add_another", default=False): bool,
            }),
            errors=errors,
        )

    async def async_step_select_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select user to modify."""
        pin_storage = PinStorage(self.hass)
        await pin_storage.async_load()
        users = pin_storage.get_user_pins()

        if not users:
            return await self.async_step_menu()

        if user_input is not None:
            return await self.async_step_modify_user(user_input[CONF_USERNAME])

        return self.async_show_form(
            step_id="select_user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): vol.In(list(users.keys())),
            }),
        )

    async def async_step_modify_user(
        self, username: str | None = None, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Modify selected user's PIN."""
        errors = {}

        if user_input is not None:
            pin = user_input[CONF_PIN]
            if len(pin) == 6 and pin.isdigit():
                pin_storage = PinStorage(self.hass)
                await pin_storage.async_load()
                await pin_storage.async_store_pin(username, pin)
                return await self.async_step_menu()
            errors["base"] = "invalid_pin"

        return self.async_show_form(
            step_id="modify_user",
            data_schema=vol.Schema({
                vol.Required(CONF_PIN): str,
            }),
            description_placeholders={"username": username},
            errors=errors,
        )

    async def async_step_remove_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Remove a user."""
        pin_storage = PinStorage(self.hass)
        await pin_storage.async_load()
        users = pin_storage.get_user_pins()

        if not users:
            return await self.async_step_menu()

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            await pin_storage.async_remove_user(username)
            return await self.async_step_menu()

        return self.async_show_form(
            step_id="remove_user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): vol.In(list(users.keys())),
            }),
            description_placeholders={
                "warning": "Warning: This action cannot be undone!"
            },
        )

    async def async_step_change_admin(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Change admin PIN."""
        errors = {}

        if user_input is not None:
            pin = user_input[CONF_ADMIN_PIN]
            if len(pin) == 6 and pin.isdigit():
                pin_storage = PinStorage(self.hass)
                await pin_storage.async_load()
                await pin_storage.async_store_admin_pin(pin)
                return await self.async_step_menu()
            errors["base"] = "invalid_pin"

        return self.async_show_form(
            step_id="change_admin",
            data_schema=vol.Schema({
                vol.Required(CONF_ADMIN_PIN): str,
            }),
            errors=errors,
        )

class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
