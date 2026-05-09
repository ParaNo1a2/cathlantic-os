import os
from pathlib import Path
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

ACTOR_ID = "T1XDXWc1L92AfIJtd"


def get_client(api_key: str = "") -> ApifyClient:
    key = api_key or os.getenv("APIFY_API_KEY", "")
    if not key or key == "your_apify_api_key_here":
        raise ValueError("APIFY_API_KEY tanımlı değil.")
    return ApifyClient(key)


def run_leads_finder(
    keywords: list[str],
    job_titles: list[str],
    fetch_count: int = 100,
    only_validated_emails: bool = True,
    run_label: str = "LCadreon Run",
    countries: list[str] | None = None,
    company_sizes: list[str] | None = None,
    api_key: str = "",
) -> list[dict]:
    """
    Apify Leads Scraper actor'ını çalıştırır ve sonuçları döner.

    Returns:
        [{"first_name", "last_name", "email", "company_name",
          "company_website", "job_title", "location"}]
    """
    client = get_client(api_key)

    # Sadece EN unvanları gönder — Apollo verisi İngilizce, Türkçe unvanlar eşleşmiyor
    en_titles = [t for t in job_titles if not _is_turkish(t)]
    titles_to_send = en_titles if en_titles else job_titles

    actor_input = {
        "totalResults": max(fetch_count, 100),
        "personTitle": titles_to_send,
        "personCountry": countries if countries else ["Turkey"],
        "industryKeywords": keywords,
        "includeEmails": True,
    }

    if only_validated_emails:
        actor_input["contactEmailStatus"] = "verified"

    if company_sizes:
        actor_input["organizationNumEmployeesRanges"] = company_sizes

    try:
        run = client.actor(ACTOR_ID).call(run_input=actor_input, timeout_secs=600)
    except Exception as e:
        raise RuntimeError(f"Apify actor çalıştırılamadı: {e}")

    if run.get("status") not in ("SUCCEEDED", "TIMED-OUT"):
        raise RuntimeError(
            f"Apify run başarısız. Status: {run.get('status')} | "
            f"Mesaj: {run.get('statusMessage', '')}"
        )

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        raise RuntimeError("Apify dataset ID bulunamadı.")

    try:
        items = list(client.dataset(dataset_id).iterate_items())
    except Exception as e:
        raise RuntimeError(f"Dataset okunamadı: {e}")

    leads = [_normalize_lead(item) for item in items if _is_valid_lead(item)]
    return leads


def _is_valid_lead(item: dict) -> bool:
    has_email = bool(item.get("email"))
    has_name = bool(item.get("firstName") or item.get("fullName"))
    is_progress_msg = "🟢" in str(item.get("fullName", "")) or "Refer to the log" in str(item)
    return has_email and has_name and not is_progress_msg


_TURKISH_CHARS = set("ğüşıöçĞÜŞİÖÇ")
_TURKISH_WORDS = {
    "genel", "müdür", "direktörü", "satın", "alma", "satış", "pazarlama",
    "operasyon", "lojistik", "tedarik", "zinciri", "ürün", "kurucu",
    "yönetici", "ortak", "işletme", "sahibi", "e-ticaret",
}


def _is_turkish(text: str) -> bool:
    lower = text.lower()
    if any(c in text for c in _TURKISH_CHARS):
        return True
    return any(w in lower for w in _TURKISH_WORDS)


def _normalize_lead(item: dict) -> dict:
    website = item.get("organizationWebsite", "")
    if website and not website.startswith("http"):
        website = "https://" + website

    return {
        "first_name": item.get("firstName", "").strip(),
        "last_name": item.get("lastName", "").strip(),
        "email": item.get("email", "").strip().lower(),
        "company_name": item.get("organizationName", ""),
        "company_website": website,
        "job_title": item.get("position", ""),
        "location": item.get("city", "") or item.get("country", ""),
    }
