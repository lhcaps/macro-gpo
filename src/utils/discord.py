import os

import requests


def send_discord(webhook_url, message, file_path=None):
    if not webhook_url or not webhook_url.strip():
        return None

    payload = {"content": message}
    try:
        if file_path:
            abs_path = os.path.abspath(file_path)
            if os.path.exists(abs_path):
                with open(abs_path, "rb") as file:
                    response = requests.post(
                        webhook_url,
                        data=payload,
                        files={"file": ("match_finish.png", file, "image/png")},
                        timeout=10,
                    )
                    return response.status_code

        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code
    except Exception:
        return None
