"""CAPTCHA links returned by the Too Good To Go API."""

import json
from urllib.parse import urlsplit

from homeassistant.components import persistent_notification


def get_captcha_url(error) -> str | None:
    if len(error.args) < 2 or error.args[0] != 403:
        return None
    try:
        payload = json.loads(error.args[1])
        url = payload.get("url") if isinstance(payload, dict) else None
        if not isinstance(url, str) or any(
            character.isspace()
            or ord(character) < 32
            or ord(character) == 127
            or character in '<>"'
            for character in url
        ):
            return None
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if (
            parsed.scheme != "https"
            or not (
                host == "captcha-delivery.com" or host.endswith(".captcha-delivery.com")
            )
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            return None
        return url
    except (ValueError, TypeError):
        return None


def show_captcha(hass, url: str, notification_id: str) -> None:
    persistent_notification.async_create(
        hass,
        "Too Good To Go requires manual verification.\n\n"
        f"[Solve CAPTCHA](<{url}>)\n\n"
        "Open the link on the same network as Home Assistant, then retry when ready. "
        "The link can expire, and completing it in a browser may not unlock the "
        "integration session. Do not share the challenge URL.",
        title="Too Good To Go: CAPTCHA required",
        notification_id=notification_id,
    )


def dismiss_captcha(hass, notification_id: str) -> None:
    persistent_notification.async_dismiss(hass, notification_id)
