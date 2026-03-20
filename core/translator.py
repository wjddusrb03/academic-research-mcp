import os
import httpx


def is_available() -> bool:
    return bool(os.environ.get("NAVER_CLIENT_ID") and os.environ.get("NAVER_CLIENT_SECRET"))


def translate(text: str, source: str = "en", target: str = "ko") -> str:
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError(
            "Naver API key not set. Translation is optional. "
            "Get your free key at https://developers.naver.com"
        )
    url = "https://openapi.naver.com/v1/papago/n2mt"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    data = {"source": source, "target": target, "text": text}
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, headers=headers, data=data)
        resp.raise_for_status()
    return resp.json()["message"]["result"]["translatedText"]
