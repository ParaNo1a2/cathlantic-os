import os
from pathlib import Path
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

ACTOR_ID = "T1XDXWc1L92AfIJtd"

# Scraper hard limits (input-schema'dan: totalResults 100-30000, arrays max 100)
MAX_INDUSTRY_KEYWORDS = 100
MAX_PERSON_TITLES     = 100

# Apollo'nun geçerli companyEmployeeSize değerleri (tam liste, boşluklu format zorunlu)
VALID_EMPLOYEE_SIZES = {
    "0 - 1", "2 - 10", "11 - 50", "51 - 200",
    "201 - 500", "501 - 1000", "1001 - 5000", "5001 - 10000", "10000+",
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
    api_key: str = "",
) -> tuple[list[dict], dict]:
    """
    Apify peakydev/leads-scraper actor'ını çalıştırır.

    Parametre isimleri ve değerleri aktörün input-schema'sına birebir uyar.
    totalResults: 100-30000 | personTitle: max 100 | industryKeywords: max 100
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

    # Temel filtreler — AND koşulları, Türkiye gibi küçük pazarlarda minimum tutulmalı
    country_list = list(dict.fromkeys(countries)) if countries else ["Turkey"]
    actor_input = {
        "totalResults":           max(fetch_count, 100),   # scraper minimum 100
        "personTitle":            titles_to_send,           # OR içinde, genişletici
        "personCountry":          country_list,             # kişinin bulunduğu ülke (companyCountry'den daha geniş veri)
        "includeEmails":          True,
        "skipLeadsWithoutEmails": True,
    }

    # industryKeywords — opsiyonel AND filtre, boşsa gönderme
    if keywords_to_send:
        actor_input["industryKeywords"] = keywords_to_send

    # Opsiyonel AND filtreler — sadece açıkça istenirseler eklenir
    if only_validated_emails:
        actor_input["contactEmailStatus"] = "verified"

    if valid_sizes:
        actor_input["companyEmployeeSize"] = valid_sizes

    meta = {
        "keywords_sent": len(keywords_to_send),
        "titles_sent":   len(titles_to_send),
        "sizes_sent":    len(valid_sizes),
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
    meta["raw_items"] = len(items)
    meta["valid_leads"] = len(leads)
    meta["actor_input"] = actor_input
    # İlk reddedilen item'ın field adlarını göster (hangi key'lerle geliyor)
    rejected = [item for item in items if not _is_valid_lead(item)]
    if rejected:
        sample = rejected[0]
        meta["rejected_sample_keys"] = list(sample.keys())
        meta["rejected_sample"] = {k: str(v)[:80] for k, v in sample.items()}
    return leads, meta


def _extract_email(item: dict) -> str:
    """Apollo farklı field adlarıyla email dönebilir — hepsini dene."""
    # Tekil string alanlar
    for field in ("email", "workEmail", "emailAddress", "email_address",
                  "primaryEmail", "personalEmail", "contactEmail"):
        val = item.get(field)
        if val and isinstance(val, str) and "@" in val:
            return val.strip().lower()
    # Dizi alanlar
    for field in ("emails",):
        arr = item.get(field)
        if isinstance(arr, list) and arr:
            first = arr[0]
            if isinstance(first, str) and "@" in first:
                return first.strip().lower()
            if isinstance(first, dict):
                for key in ("email", "address", "value", "emailAddress"):
                    val = first.get(key, "")
                    if val and "@" in str(val):
                        return str(val).strip().lower()
    return ""


_SYSTEM_MSG_PATTERNS = (
    "🟢", "Refer to the log", "exceeded", "monthly run limit",
    "upgrade", "Upgrade", "free plan", "Free Apify",
)

def _is_valid_lead(item: dict) -> bool:
    raw = str(item)
    if any(p in raw for p in _SYSTEM_MSG_PATTERNS):
        return False
    has_name = bool(item.get("firstName") or item.get("fullName") or item.get("name"))
    has_email = bool(_extract_email(item))
    return has_name and has_email


def _normalize_lead(item: dict) -> dict:
    email  = _extract_email(item)
    website = (
        item.get("organizationWebsite")
        or item.get("companyWebsite")
        or item.get("website", "")
    )
    if website and not website.startswith("http"):
        website = "https://" + website

    full_name = item.get("fullName") or item.get("name") or ""
    first_name = item.get("firstName") or (full_name.split()[0] if full_name else "")
    last_name  = item.get("lastName")  or (" ".join(full_name.split()[1:]) if full_name else "")

    return {
        "first_name":      first_name.strip(),
        "last_name":       last_name.strip(),
        "email":           email.strip().lower(),
        "company_name":    item.get("organizationName") or item.get("companyName") or "",
        "company_website": website,
        "job_title":       item.get("position") or item.get("title") or item.get("jobTitle") or "",
        "location":        item.get("city") or item.get("country") or "",
        "linkedin_url":    item.get("linkedinUrl") or item.get("linkedin") or "",
    }


# ---------------------------------------------------------------------------
# Yardımcı — Türkçe metin tespiti
# ---------------------------------------------------------------------------

_TURKISH_CHARS = set("ğüşıöçĞÜŞİÖÇ")
# Türkçe kelimeler — hem özel karakterli hem ASCII (tam kelime eşleşmesi ile kontrol edilir)
_TURKISH_WORDS = {
    # Özel karakterli
    "genel", "müdür", "satın", "alma", "satış", "pazarlama",
    "operasyon", "lojistik", "tedarik", "zinciri", "kurucu",
    "yönetici", "ortak", "sahibi", "mağaza", "giyim", "moda",
    "depolama", "kargo", "takip", "tedarikçi",
    # ASCII Türkçe (özel karakter yok ama İngilizce değil)
    "kozmetik", "mobilya", "toptan", "evcil", "hayvan",
    "ticaret", "ithalat", "ihracat", "bebek", "oyuncak",
    "gıda", "tekstil", "hizmet", "yazılım", "danışmanlık",
}


def _is_turkish(text: str) -> bool:
    if any(c in text for c in _TURKISH_CHARS):
        return True
    # Tam kelime eşleşmesi — substring değil ("son" → "person"'ı tutmamalı)
    words = set(text.lower().split())
    return bool(words & _TURKISH_WORDS)
