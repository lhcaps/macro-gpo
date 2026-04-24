"""
Discord webhook helper — supports both file_path (disk) and bytes_io (in-memory).

Used by:
- legacy BackendCallbacks.discord() with file_path (backward compat)
- discord_event_service.send_discord_event() with bytes_io (Phase 12.4)

Discord does NOT support data URI in file attachments, so in-memory bytes
must be sent as a multipart file upload.
"""

import io
import logging
import os

import requests

_log = logging.getLogger("zedsu.discord")


def send_discord(
    webhook_url: str,
    message: str,
    file_path: str | None = None,
    bytes_io: io.BytesIO | None = None,
    filename: str = "screenshot.png",
) -> int | None:
    """
    Send a Discord webhook notification.

    Args:
        webhook_url: Discord webhook URL.
        message: Plain-text content body.
        file_path: Optional path to a file on disk. Used for backward compatibility.
        bytes_io: Optional in-memory bytes buffer (e.g. from MSS screenshot).
                   Preferred over file_path when both are provided.
        filename: Filename to use for the bytes_io upload.

    Returns:
        HTTP status code on success, None on failure.
    """
    if not webhook_url or not webhook_url.strip():
        return None

    payload = {"content": message}
    try:
        # Prefer in-memory bytes over disk file
        if bytes_io is not None:
            # Reset cursor to start so the full buffer is sent
            bytes_data = bytes_io.getvalue()
            if not bytes_data:
                _log.warning("send_discord: bytes_io is empty, sending text only")
                response = requests.post(webhook_url, json=payload, timeout=10)
                return response.status_code

            response = requests.post(
                webhook_url,
                data=payload,
                files={"file": (filename, bytes_data, "image/png")},
                timeout=10,
            )
            return response.status_code

        if file_path:
            abs_path = os.path.abspath(file_path)
            if os.path.exists(abs_path):
                with open(abs_path, "rb") as fobj:
                    response = requests.post(
                        webhook_url,
                        data=payload,
                        files={"file": (os.path.basename(abs_path), fobj, "image/png")},
                        timeout=10,
                    )
                    return response.status_code

        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code
    except requests.exceptions.Timeout:
        _log.warning("send_discord: request timed out after 10s")
        return None
    except Exception as e:
        _log.warning("send_discord: failed — %s", e)
        return None
