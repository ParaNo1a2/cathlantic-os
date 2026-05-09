import os
from pathlib import Path
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

ACTOR_ID = "T1XDXWc1L92AfIJtd"

# Scraper hard limits (input-schema'dan)
MAX_INDUSTRY_KEYWORDS = 100
MAX_PERSON_TITLES     = 100
MAX_INDUSTRIES        = 20

# Apollo'nun geçerli companyEmployeeSize değerleri (tam liste)
VALID_EMPLOYEE_SIZES = {
    "1-10", "11-50", "51-200", "201-500",
    "501-1000", "1001-5000", "5001-10000", "10000+",
}


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
    industries: list[str] | None = None,
    api_key: str = "",
) -> tuple[list[dict], dict]:
    """
    Apify peakydev/leads-scraper actor'ını çalıştırır.

    Parametre isimleri ve değerleri aktörün input-schema'sına birebir uyar.
    Returns: (leads, meta) — meta: {"keywords_sent", "titles_sent", "truncated"}
    """
    client = get_client(api_key)

    # EN keyword'leri filtrele, deduplicate ve limitle
    en_keywords = list(dict.fromkeys(k for k in keywords if not _is_turkish(k)))
    keywords_to_send = (en_keywords if en_keywords else list(dict.fromkeys(keywords)))[:MAX_INDUSTRY_KEYWORDS]

    # EN unvanları filtrele, deduplicate ve limitle
    en_titles = list(dict.fromkeys(t for t in job_titles if not _is_turkish(t)))
    titles_to_send = (en_titles if en_titles else list(dict.fromkeys(job_titles)))[:MAX_PERSON_TITLES]

    # Geçerli company size değerlerini doğrula ve deduplicate et
    valid_sizes = list(dict.fromkeys(s for s in (company_sizes or []) if s in VALID_EMPLOYEE_SIZES))

    truncated = (
        len(en_keywords) > MAX_INDUSTRY_KEYWORDS
        or len(en_titles) > MAX_PERSON_TITLES
    )

    actor_input = {
        "totalResults":           max(fetch_count, 100),
        "personTitle":            titles_to_send,
        "personCountry":          list(dict.fromkeys(countries)) if countries else ["Turkey"],
        "industryKeywords":       keywords_to_send,
        "includeEmails":          True,
        "skipLeadsWithoutEmails": True,
    }

    # Apollo standart industry adları (deduplicate + limit)
    if industries:
        actor_input["industry"] = list(dict.fromkeys(industries))[:MAX_INDUSTRIES]

    # Sadece verified email toggle'ı açıksa ekle
    if only_validated_emails:
        actor_input["contactEmailStatus"] = "verified"

    # Şirket büyüklüğü (sadece geçerli değerler)
    if valid_sizes:
        actor_input["companyEmployeeSize"] = valid_sizes

    meta = {
        "keywords_sent": len(keywords_to_send),
        "titles_sent":   len(titles_to_send),
        "industries_sent": len(actor_input.get("industry", [])),
        "truncated":     truncated,
    }

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
    return leads, meta


def _is_valid_lead(item: dict) -> bool:
    # İlerleme mesajlarını filtrele
    if "🟢" in str(item.get("fullName", "")) or "Refer to the log" in str(item):
        return False
    has_name = bool(item.get("firstName") or item.get("fullName") or item.get("name"))
    # Email: tek alan veya dizi olabilir
    has_email = bool(
        item.get("email")
        or (isinstance(item.get("emails"), list) and item["emails"])
        or item.get("workEmail")
    )
    return has_name and has_email


def _normalize_lead(item: dict) -> dict:
    # Email: önce tekil alan, yoksa dizi ilk elemanı, yoksa workEmail
    email = (
        item.get("email")
        or (item.get("emails") or [""])[0]
        or item.get("workEmail", "")
    )

    website = (
        item.get("organizationWebsite")
        or item.get("companyWebsite")
        or item.get("website", "")
    )
    if website and not website.startswith("http"):
        website = "https://" + website

    # first_name: önce firstName, yoksa fullName'den ilk kelime
    full_name = item.get("fullName") or item.get("name") or ""
    first_name = item.get("firstName") or (full_name.split()[0] if full_name else "")
    last_name  = item.get("lastName")  or (" ".join(full_name.split()[1:]) if full_name else "")

    return {
        "first_name":    first_name.strip(),
        "last_name":     last_name.strip(),
        "email":         email.strip().lower(),
        "company_name":  item.get("organizationName") or item.get("companyName") or "",
        "company_website": website,
        "job_title":     item.get("position") or item.get("title") or item.get("jobTitle") or "",
        "location":      item.get("city") or item.get("country") or "",
        "linkedin_url":  item.get("linkedinUrl") or item.get("linkedin") or "",
    }


# ---------------------------------------------------------------------------
# Yardımcı — Türkçe metin tespiti
# ---------------------------------------------------------------------------

_TURKISH_CHARS = set("ğüşıöçĞÜŞİÖÇ")
_TURKISH_WORDS = {
    "genel", "müdür", "direktörü", "satın", "alma", "satış", "pazarlama",
    "operasyon", "lojistik", "tedarik", "zinciri", "ürün", "kurucu",
    "yönetici", "ortak", "işletme", "sahibi", "e-ticaret", "mağaza",
    "giyim", "kıyafet", "moda", "son", "mil", "depolama", "kargo",
    "takip", "stoksuz", "tedarikçi", "dropshipping",
}


def _is_turkish(text: str) -> bool:
    if any(c in text for c in _TURKISH_CHARS):
        return True
    lower = text.lower()
    return any(w in lower for w in _TURKISH_WORDS)
