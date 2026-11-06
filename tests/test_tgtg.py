"""Regression tests for authentication, cooldowns, retired items and polling options."""

from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from unittest.mock import AsyncMock

import pytest
import voluptuous as vol


def prepare_update(integration, data=None, options=None):
    coordinator = integration.make_coordinator(data, options)
    coordinator._tgtg = integration.Client()
    coordinator._fetch_all_favorites = AsyncMock(return_value=[])
    return coordinator


@pytest.mark.asyncio
async def test_client_constructed_in_executor(integration):
    coordinator = integration.make_coordinator()
    assert not integration.Client.instances
    await coordinator._async_setup()
    client = coordinator._tgtg
    assert client.thread_id != threading.get_ident()
    assert client.kwargs["user_agent"] == integration.const.TGTG_USER_AGENT
    assert client.kwargs["refresh_token"] == "test-refresh"
    assert client.kwargs["cookie"] == "test-cookie"


@pytest.mark.asyncio
async def test_persist_rotated_credentials(integration):
    coordinator = prepare_update(integration)
    coordinator._tgtg.access_token = "rotated-access"
    coordinator._tgtg.refresh_token = "rotated-refresh"
    coordinator._tgtg.cookie = "rotated-cookie"
    await coordinator._async_update_data()
    assert coordinator.config_entry.data["access_token"] == "rotated-access"
    assert coordinator.config_entry.data["refresh_token"] == "rotated-refresh"
    assert coordinator.config_entry.data["cookie"] == "rotated-cookie"


@pytest.mark.asyncio
async def test_api_401_requests_reauthentication(integration):
    coordinator = prepare_update(integration)
    coordinator._tgtg.login.side_effect = integration.APIError(401, b"unauthorized")
    with pytest.raises(integration.AuthFailed):
        await coordinator._async_setup()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [403, 429])
async def test_rate_limit_survives_coordinator_recreation(integration, status):
    coordinator = prepare_update(integration)
    coordinator._tgtg.login.side_effect = integration.APIError(status, b"blocked")
    with pytest.raises(integration.UpdateFailed):
        await coordinator._async_setup()
    assert coordinator.update_interval.total_seconds() == 3600
    assert coordinator._retry_after is None
    deadline = coordinator.config_entry.data["api_retry_after"]
    assert deadline > datetime.now(timezone.utc).timestamp() + 3500
    recreated = integration.make_coordinator(coordinator.config_entry.data)
    count = len(integration.Client.instances)
    with pytest.raises(integration.UpdateFailed, match="Reconfigure"):
        await recreated._async_setup()
    assert len(integration.Client.instances) == count


@pytest.mark.asyncio
@pytest.mark.parametrize("saved", [None, 0, 1])
async def test_framework_retry_field_does_not_break_updates(integration, saved):
    coordinator = prepare_update(integration, {"api_retry_after": saved})
    for _ in range(3):
        coordinator._retry_after = None
        assert await coordinator._async_update_data() is True
        assert coordinator._retry_after is None


@pytest.mark.asyncio
async def test_gone_item_skipped_and_recovers_in_favorites(integration):
    coordinator = prepare_update(integration, {"item_ids": ["123"]})
    coordinator._tgtg.get_item.side_effect = integration.APIError(410, b"gone")
    assert await coordinator._async_update_data() is True
    assert await coordinator._async_update_data() is True
    coordinator._tgtg.get_item.assert_called_once_with("123")
    assert coordinator.config_entry.data["item_ids"] == ["123"]
    assert coordinator.config_entry.data["gone_item_ids"] == ["123"]
    recreated = prepare_update(integration, coordinator.config_entry.data)
    assert await recreated._async_update_data() is True
    recreated._tgtg.get_item.assert_not_called()
    recreated._fetch_all_favorites.return_value = [{"item": {"item_id": "123"}}]
    assert await recreated._async_update_data() is True
    assert recreated.config_entry.data["gone_item_ids"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 429])
async def test_optional_item_does_not_swallow_auth_errors(integration, status):
    coordinator = prepare_update(integration, {"item_ids": ["123"]})
    coordinator._tgtg.get_item.side_effect = integration.APIError(status, b"blocked")
    exception = integration.AuthFailed if status == 401 else integration.UpdateFailed
    with pytest.raises(exception):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_optional_orders_500_is_noncritical(integration):
    coordinator = prepare_update(integration)
    coordinator._tgtg.get_active.side_effect = integration.APIError(500, b"server")
    assert await coordinator._async_update_data() is True
    assert coordinator.tgtg_orders == []


def test_captcha_url_preserved_in_notification(integration):
    url = "https://geo.captcha-delivery.com/interstitial/?cid=abc~xyz&value=a+b%2Fc%3D&extra=(test)"
    error = integration.APIError(403, json.dumps({"url": url}).encode())
    assert integration.captcha.get_captcha_url(error) == url
    integration.captcha.show_captcha(None, url, "test-notification")
    args, kwargs = integration.notifications.async_create.call_args
    assert f"[Solve CAPTCHA](<{url}>)" in args[1]
    assert kwargs["notification_id"] == "test-notification"
    integration.captcha.dismiss_captcha(None, "test-notification")
    integration.notifications.async_dismiss.assert_called_once_with(
        None, "test-notification"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://geo.captcha-delivery.com/test",
        "https://captcha-delivery.com.evil.example/test",
        "https://user:pass@geo.captcha-delivery.com/test",
        "https://geo.captcha-delivery.com:8443/test",
        "https://geo.captcha-delivery.com/<script>",
        "https://geo.captcha-delivery.com/\x00",
        "https://geo.captcha-delivery.com/\n",
        "javascript:alert(1)",
    ],
)
def test_unsafe_captcha_url_rejected(integration, url):
    error = integration.APIError(403, json.dumps({"url": url}))
    assert integration.captcha.get_captcha_url(error) is None


@pytest.mark.parametrize("body", [b"invalid JSON", b"[]", b"{}", b'{"url":null}'])
def test_malformed_captcha_payload(integration, body):
    assert integration.captcha.get_captcha_url(integration.APIError(403, body)) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["reauth", "reconfigure"])
async def test_renewal_confirms_and_preserves_existing_entry(integration, source):
    flow = integration.flow.ConfigFlowHandler()
    flow.context = {"source": source}
    flow.entry = integration.Entry({"item_ids": ["123"], "api_retry_after": 123})
    flow.async_step_login = AsyncMock(return_value={"type": "login"})
    result = await (
        flow.async_step_reauth(flow.entry.data)
        if source == "reauth"
        else flow.async_step_reconfigure()
    )
    assert result["step_id"] == "reauth_confirm"
    assert not integration.Client.instances
    await flow.async_step_reauth_confirm({})
    assert flow._tgtg.thread_id != threading.get_ident()
    assert flow._tgtg.kwargs == {
        "email": "test@example.invalid",
        "user_agent": integration.const.TGTG_USER_AGENT,
    }
    result = await flow.async_step_login_complete()
    assert result == {"type": "abort", "reason": "updated"}
    assert flow.entry.data["item_ids"] == ["123"]
    assert flow.entry.data["api_retry_after"] == 0
    assert flow.entry.data["refresh_token"] == "new-refresh"


@pytest.mark.asyncio
async def test_pin_captcha_shows_link_without_retry(integration):
    flow = integration.flow.ConfigFlowHandler()
    url = "https://geo.captcha-delivery.com/test?cid=example"
    flow.hass.async_add_executor_job = AsyncMock(
        side_effect=integration.APIError(403, json.dumps({"url": url}))
    )
    flow.async_step_login = AsyncMock()
    result = await flow.async_step_pin({"pin": "test-pin"})
    assert result["step_id"] == "failed"
    assert result["errors"]["base"] == "captcha"
    assert url in result["description_placeholders"]["captcha_link"]
    flow.async_step_login.assert_not_called()


@pytest.mark.asyncio
async def test_options_defaults_and_validation(integration):
    flow = integration.flow.ConfigFlowHandler.async_get_options_flow(
        integration.Entry()
    )
    flow._config_entry = integration.Entry()
    schema = (await flow.async_step_init())["data_schema"]
    assert schema({}) == {"scan_interval": 60, "sales_scan_interval": 3}
    for options in (
        {"scan_interval": 0},
        {"scan_interval": 1441},
        {"sales_scan_interval": -1},
        {"sales_scan_interval": 1441},
    ):
        with pytest.raises(vol.Invalid):
            schema(options)
    result = await flow.async_step_init(
        schema({"scan_interval": 120, "sales_scan_interval": 0})
    )
    assert result["data"] == {"scan_interval": 120, "sales_scan_interval": 0}


@pytest.mark.asyncio
async def test_jitter_changes_on_each_update(integration, monkeypatch):
    jitter = iter([-30, -15, 12])
    monkeypatch.setattr(integration.coordinator, "uniform", lambda *_: next(jitter))
    coordinator = prepare_update(
        integration, options={"scan_interval": 120, "sales_scan_interval": 0}
    )
    assert coordinator.update_interval.total_seconds() == 7170
    await coordinator._async_update_data()
    assert coordinator.update_interval.total_seconds() == 7185
    await coordinator._async_update_data()
    assert coordinator.update_interval.total_seconds() == 7212


@pytest.mark.parametrize("sales_minutes,expected", [(0, 7200), (5, 300)])
def test_sales_window_polling_can_be_disabled(
    integration, monkeypatch, sales_minutes, expected
):
    monkeypatch.setattr(integration.coordinator, "uniform", lambda *_: 0)
    coordinator = integration.make_coordinator(
        options={"scan_interval": 120, "sales_scan_interval": sales_minutes}
    )
    monkeypatch.setattr(coordinator, "_any_item_in_sales_window", lambda: True)
    coordinator._set_polling_interval()
    assert coordinator.update_interval.total_seconds() == expected


@pytest.mark.asyncio
async def test_jitter_does_not_shorten_captcha_pause(integration, monkeypatch):
    monkeypatch.setattr(integration.coordinator, "uniform", lambda *_: -30)
    coordinator = prepare_update(integration)
    coordinator._fetch_all_favorites.side_effect = integration.APIError(403, b"blocked")
    with pytest.raises(integration.UpdateFailed):
        await coordinator._async_update_data()
    assert coordinator.update_interval.total_seconds() == 3600


@pytest.mark.asyncio
async def test_options_listener_ignores_saved_tokens(integration):
    coordinator = integration.make_coordinator()
    entry = coordinator.config_entry
    entry.runtime_data = coordinator
    entry.data["access_token"] = "rotated"
    await integration.setup.async_update_options(coordinator.hass, entry)
    coordinator.hass.config_entries.async_reload.assert_not_called()
    entry.options["scan_interval"] = 120
    await integration.setup.async_update_options(coordinator.hass, entry)
    coordinator.hass.config_entries.async_reload.assert_awaited_once_with(
        entry.entry_id
    )


def test_english_translation_matches_source():
    root = Path(__file__).parents[1] / "custom_components" / "tgtg"
    assert json.loads((root / "strings.json").read_text()) == json.loads(
        (root / "translations/en.json").read_text()
    )
