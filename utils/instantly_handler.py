import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

BASE_URL = "https://api.instantly.ai/api/v2"


def _headers(api_key: str = "") -> dict:
    key = api_key or os.getenv("INSTANTLY_API_KEY", "")
    if not key or key == "your_instantly_api_key_here":
        raise ValueError("INSTANTLY_API_KEY tanımlı değil.")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _raise_for(resp: requests.Response, context: str):
    if not resp.ok:
        try:
            msg = resp.json().get("message") or resp.json().get("error") or resp.text[:200]
        except Exception:
            msg = resp.text[:200]
        raise RuntimeError(f"Instantly API hatası [{context}] {resp.status_code}: {msg}")


# ---------------------------------------------------------------------------
# HESAPLAR
# ---------------------------------------------------------------------------
def list_email_accounts(api_key: str = "") -> list[dict]:
    """Sending email hesaplarını döner: [{"email": str, "id": str}]"""
    resp = requests.get(f"{BASE_URL}/accounts", headers=_headers(api_key), params={"limit": 100})
    _raise_for(resp, "list_accounts")
    items = resp.json().get("items", resp.json() if isinstance(resp.json(), list) else [])
    return [{"email": a.get("email", ""), "id": a.get("id", a.get("uuid", ""))} for a in items]


# ---------------------------------------------------------------------------
# KAMPANYALAR
# ---------------------------------------------------------------------------
def list_campaigns(api_key: str = "") -> list[dict]:
    """Mevcut kampanyaları döner: [{"id": str, "name": str, "status": str}]"""
    resp = requests.get(f"{BASE_URL}/campaigns", headers=_headers(api_key), params={"limit": 100})
    _raise_for(resp, "list_campaigns")
    data = resp.json()
    items = data.get("items", data if isinstance(data, list) else [])
    return [{"id": c.get("id", ""), "name": c.get("name", ""), "status": c.get("status", "")} for c in items]


def create_campaign(
    name: str,
    email_accounts: list[str],
    sequences: dict,
    daily_limit: int = 50,
    timezone: str = "Europe/Istanbul",
    api_key: str = "",
) -> str:
    """
    Yeni kampanya oluşturur ve campaign_id döner.

    sequences: {
      "email_1_a": {"subject": str, "body": str},
      "email_1_b": ..., "email_1_c": ...,
      "followup_1": ..., "followup_2": ..., "followup_3": ...
    }
    """
    # Instantly'de {{first_name}} → {{firstName}} built-in değişken
    def _fix_vars(text: str) -> str:
        text = re.sub(r"\{\{first_name\}\}", "{{firstName}}", text, flags=re.IGNORECASE)
        text = re.sub(r"\{\{last_name\}\}", "{{lastName}}", text, flags=re.IGNORECASE)
        text = re.sub(r"\{\{company_name\}\}", "{{companyName}}", text, flags=re.IGNORECASE)
        return text

    def _variant(seq_key: str) -> dict:
        seq = sequences.get(seq_key, {})
        body = _fix_vars(seq.get("body", ""))
        body = body.replace("\n\n", "<br><br>").replace("\n", "<br>")
        return {
            "subject": _fix_vars(seq.get("subject", "")),
            "body": body,
        }

    payload = {
        "name": name,
        "email_list": email_accounts,
        "daily_limit": daily_limit,
        "stop_on_reply": True,
        "open_tracking": True,
        "link_tracking": False,
        "provider_matching": True,
        "campaign_schedule": {
            "schedules": [
                {
                    "name": "Hafta içi 09-18",
                    "timing": {"from": "09:00", "to": "18:00"},
                    "days": {
                        "monday": True, "tuesday": True, "wednesday": True,
                        "thursday": True, "friday": True,
                        "saturday": False, "sunday": False,
                    },
                    "timezone": timezone,
                }
            ]
        },
        "sequences": [
            {
                "steps": [
                    # Adım 1 — İlk mail, 3 A/B/C varyant
                    {
                        "type": "email",
                        "delay": 0,
                        "variants": [
                            _variant("email_1_a"),
                            _variant("email_1_b"),
                            _variant("email_1_c"),
                        ],
                    },
                    # Adım 2 — Follow-up 1, 2. gün
                    {
                        "type": "email",
                        "delay": 2,
                        "variants": [_variant("followup_1")],
                    },
                    # Adım 3 — Follow-up 2, 2. gün sonra
                    {
                        "type": "email",
                        "delay": 2,
                        "variants": [_variant("followup_2")],
                    },
                    # Adım 4 — Break-up, 4. gün sonra
                    {
                        "type": "email",
                        "delay": 4,
                        "variants": [_variant("followup_3")],
                    },
                ]
            }
        ],
    }

    resp = requests.post(f"{BASE_URL}/campaigns", headers=_headers(api_key), json=payload)
    _raise_for(resp, "create_campaign")
    return resp.json().get("id", "")


# ---------------------------------------------------------------------------
# KAMPANYA BAŞLATMA
# ---------------------------------------------------------------------------
def launch_campaign(campaign_id: str, api_key: str = "") -> None:
    """Draft kampanyayı aktif hale getirir."""
    resp = requests.post(
        f"{BASE_URL}/campaigns/{campaign_id}/activate",
        headers=_headers(api_key),
        json={},
    )
    if not resp.ok:
        # Fallback: PATCH ile status güncelle
        resp2 = requests.patch(
            f"{BASE_URL}/campaigns/{campaign_id}",
            headers=_headers(api_key),
            json={"status": "active"},
        )
        _raise_for(resp2, "launch_campaign")


# ---------------------------------------------------------------------------
# LEAD YÜKLEME
# ---------------------------------------------------------------------------
def upload_leads(campaign_id: str, leads: list[dict], api_key: str = "") -> dict:
    """
    Lead'leri kampanyaya yükler (max 1000/istek).
    leads: [{"first_name", "last_name", "email", "company_name", "company_website", "unvan"}]
    Returns: {"uploaded": int, "failed": int}
    """
    BATCH = 1000
    total_uploaded = 0
    total_failed = 0

    for i in range(0, len(leads), BATCH):
        batch = leads[i: i + BATCH]
        payload_leads = []
        for lead in batch:
            obj = {
                "email": lead.get("email", "").strip().lower(),
                "first_name": lead.get("first_name", ""),
                "last_name": lead.get("last_name", ""),
                "company_name": lead.get("company_name", ""),
                "website": lead.get("company_website", ""),
                "personalization": "",
                # unvan özel değişken olarak
                "unvan": lead.get("unvan", ""),
            }
            if obj["email"]:
                payload_leads.append(obj)

        if not payload_leads:
            continue

        resp = requests.post(
            f"{BASE_URL}/leads/bulk",
            headers=_headers(api_key),
            json={"campaign_id": campaign_id, "leads": payload_leads},
        )

        if resp.ok:
            result = resp.json()
            total_uploaded += result.get("total_new_leads", len(payload_leads))
            total_failed += result.get("total_duplicate_leads", 0)
        else:
            total_failed += len(payload_leads)

    return {"uploaded": total_uploaded, "failed": total_failed}
