import requests
from pathlib import Path

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}


def fetch_homepage_text(url: str, max_chars: int = 2500, timeout: int = 10) -> str:
    """
    Verilen URL'nin ana sayfasından görünür metni çeker.
    Hata durumunda boş string döner (lead'i kesmez).
    """
    if not url:
        return ""

    if not url.startswith("http"):
        url = "https://" + url

    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return ""
        return _extract_text(resp.text)[:max_chars]
    except Exception:
        # Timeout, SSL hatası, 4xx/5xx — lead'i skip etme, boş döndür
        return ""


def _extract_text(html: str) -> str:
    """HTML'den görünür metni çıkarır — script/style/head taglarını atar."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "head", "nav", "footer", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Gereksiz boşlukları temizle
        import re
        text = re.sub(r"\s+", " ", text).strip()
        return text
    except Exception:
        return ""
