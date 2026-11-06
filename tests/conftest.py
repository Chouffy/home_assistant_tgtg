"""Dependency-light unit fixtures; no Home Assistant instance or API is contacted."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import threading
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture
def integration(monkeypatch):
    """Import actual integration modules with framework and network boundaries mocked."""
    component = Path(__file__).parents[1] / "custom_components" / "tgtg"

    class Entry:
        def __init__(self, data=None, options=None):
            self.entry_id = "test-entry"
            self.data = {
                "email": "test@example.invalid",
                "access_token": "test-access",
                "refresh_token": "test-refresh",
                "cookie": "test-cookie",
                **(data or {}),
            }
            self.options = dict(options or {})
            self.async_on_unload = Mock()
            self.add_update_listener = Mock(return_value=Mock())

    class Hass:
        def __init__(self):
            self.config_entries = SimpleNamespace(
                async_update_entry=self.update_entry,
                async_reload=AsyncMock(),
                async_forward_entry_setups=AsyncMock(),
            )

        def update_entry(self, entry, *, data):
            entry.data = data

        async def async_add_executor_job(self, function, *args):
            return await asyncio.to_thread(function, *args)

    class AuthFailed(Exception):
        pass

    class UpdateFailed(Exception):
        def __init__(self, *args, **kwargs):
            super().__init__(*args)
            self.retry_after = kwargs.get("retry_after")

    class Coordinator:
        def __init__(self, hass, logger, **kwargs):
            self.hass = hass
            self.update_interval = kwargs["update_interval"]
            self._retry_after = None

        async def _async_setup(self):
            pass

    class Flow:
        def __init_subclass__(cls, **kwargs):
            pass

        def __init__(self):
            self.context = {"source": "user"}
            self.flow_id = "test-flow"
            self.hass = Hass()

        async def async_set_unique_id(self, value):
            self.unique_id = value

        def _abort_if_unique_id_configured(self):
            pass

        def _get_reauth_entry(self):
            return self.entry

        def _get_reconfigure_entry(self):
            return self.entry

        def async_show_form(self, **kwargs):
            return {"type": "form", **kwargs}

        def async_show_progress_done(self, **kwargs):
            return {"type": "progress_done", **kwargs}

        def async_create_entry(self, **kwargs):
            return {"type": "create_entry", **kwargs}

        def async_update_reload_and_abort(self, entry, *, data_updates):
            entry.data = {**entry.data, **data_updates}
            return {"type": "abort", "reason": "updated"}

    class Options(Flow):
        @property
        def config_entry(self):
            return self._config_entry

    class APIError(Exception):
        pass

    class LoginError(Exception):
        pass

    class Client:
        instances = []

        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.thread_id = threading.get_ident()
            self.access_token = kwargs.get("access_token", "new-access")
            self.refresh_token = kwargs.get("refresh_token", "new-refresh")
            self.cookie = kwargs.get("cookie", "new-cookie")
            self.login = Mock()
            self.get_items = Mock(return_value=[])
            self.get_item = Mock()
            self.get_active = Mock(return_value={"orders": []})
            self.instances.append(self)

    notification = SimpleNamespace(async_create=Mock(), async_dismiss=Mock())
    attributes = {
        "homeassistant": {},
        "homeassistant.config_entries": {
            "ConfigEntry": Entry,
            "ConfigFlow": Flow,
            "ConfigFlowResult": dict,
            "OptionsFlow": Options,
            "SOURCE_REAUTH": "reauth",
            "SOURCE_RECONFIGURE": "reconfigure",
        },
        "homeassistant.const": {
            "CONF_EMAIL": "email",
            "CONF_ACCESS_TOKEN": "access_token",
            "Platform": SimpleNamespace(SENSOR="sensor"),
        },
        "homeassistant.core": {
            "HomeAssistant": Hass,
            "callback": lambda function: function,
        },
        "homeassistant.exceptions": {"ConfigEntryAuthFailed": AuthFailed},
        "homeassistant.helpers": {},
        "homeassistant.helpers.update_coordinator": {
            "DataUpdateCoordinator": Coordinator,
            "UpdateFailed": UpdateFailed,
        },
        "homeassistant.helpers.selector": {
            "TextSelector": lambda value: str,
            "TextSelectorConfig": lambda **kwargs: kwargs,
            "TextSelectorType": SimpleNamespace(EMAIL="email", TEXT="text"),
            "SelectSelector": lambda value: list,
            "SelectSelectorConfig": lambda **kwargs: kwargs,
            "SelectSelectorMode": SimpleNamespace(DROPDOWN="dropdown"),
        },
        "homeassistant.components": {"persistent_notification": notification},
        "tgtg": {
            "TgtgClient": Client,
            "TgtgAPIError": APIError,
            "TgtgLoginError": LoginError,
            "TgtgPollingError": LoginError,
            "AUTH_BY_EMAIL_ENDPOINT": "auth/email",
            "AUTH_BY_REQUEST_PIN_ENDPOINT": "auth/request-pin",
        },
    }
    for name, values in attributes.items():
        module = ModuleType(name)
        module.__path__ = []
        module.__dict__.update(values)
        monkeypatch.setitem(sys.modules, name, module)

    package_name = "tgtg_under_test"
    package = ModuleType(package_name)
    package.__path__ = [str(component)]
    monkeypatch.setitem(sys.modules, package_name, package)

    def load(name, filename=None):
        qualified = f"{package_name}.{name}"
        spec = importlib.util.spec_from_file_location(
            qualified, component / (filename or f"{name}.py")
        )
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, qualified, module)
        spec.loader.exec_module(module)
        return module

    const = load("const")
    captcha = load("captcha")
    coordinator = load("coordinator")
    flow = load("config_flow")
    setup = load("integration", "__init__.py")
    monkeypatch.setattr(coordinator, "asyncio", SimpleNamespace(sleep=AsyncMock()))

    def make_coordinator(data=None, options=None):
        return coordinator.TGTGUpdateCoordinator(Hass(), Entry(data, options))

    return SimpleNamespace(
        const=const,
        captcha=captcha,
        coordinator=coordinator,
        flow=flow,
        setup=setup,
        Entry=Entry,
        Hass=Hass,
        Client=Client,
        APIError=APIError,
        LoginError=LoginError,
        AuthFailed=AuthFailed,
        UpdateFailed=UpdateFailed,
        notifications=notification,
        make_coordinator=make_coordinator,
    )
