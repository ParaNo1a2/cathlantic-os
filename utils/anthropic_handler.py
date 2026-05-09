import json
import os
from pathlib import Path
import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

_client = None

def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key == "your_anthropic_api_key_here":
            raise ValueError("ANTHROPIC_API_KEY .env dosyasında tanımlı değil.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


SECTOR_EXPANSION_PROMPT = """Sen B2B soğuk e-posta kampanyaları için sektör araştırması yapan uzman bir growth hacker'sın.

Ana sektör: "{sector}"
Sunulan otomasyon/hizmet: "{automation}"

Görevin: Bu sektörle doğrudan veya dolaylı olarak ilişkili, Türkiye'deki B2B müşteri adayı bulmaya uygun niş alt-sektörleri ve yan sektörleri belirle.
Öncelik: Sunulan otomasyon/hizmetten en fazla fayda sağlayacak alt-sektörleri öne çıkar.

KURALLAR:
- En az 8, en fazla 15 alt/yan sektör listele
- Her sektör gerçekten B2B potansiyeli taşımalı (karar vericilere ulaşılabilir olmalı)
- Hedef: Türkiye'de faaliyet gösteren işletmeler
- keywords_tr: Türkiye'deki şirketlerin Türkçe LinkedIn/web profillerinde kullandığı terimler — sunulan otomasyon ile alakalı kavramları da dahil et
- keywords_en: Aynı şirketlerin İngilizce profillerinde veya uluslararası piyasada kullandığı terimler
- Her dilde 3-5 keyword — spesifik ve arama motoruna uyumlu olmalı, genel değil
- İki dilde keyword seti birbirini tamamlamalı, birebir çeviri olmamalı

Yanıtını YALNIZCA aşağıdaki JSON formatında ver. Başka hiçbir metin ekleme:

{{
  "sectors": [
    {{
      "sector_name": "Sektör adı (Türkçe)",
      "reason": "Neden bu sektör ve bu otomasyon uyumlu (1-2 cümle, net ve satış odaklı)",
      "keywords_tr": ["türkçe keyword1", "türkçe keyword2", "türkçe keyword3"],
      "keywords_en": ["english keyword1", "english keyword2", "english keyword3"]
    }}
  ]
}}"""


def expand_sectors(sector: str, automation: str = "") -> list[dict]:
    """
    Verilen ana sektör için niş alt-sektörler ve keywordler üretir.
    Returns: [{"sector_name": str, "reason": str, "keywords": [str]}]
    """
    client = get_client()

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": SECTOR_EXPANSION_PROMPT.format(
                        sector=sector,
                        automation=automation or "Yapay Zeka & Otomasyon çözümleri"
                    )
                }
            ]
        )
    except anthropic.AuthenticationError:
        raise ValueError("Anthropic API anahtarı geçersiz. .env dosyasını kontrol et.")
    except anthropic.NotFoundError as e:
        raise ValueError(f"Model bulunamadı. API erişim izinlerini kontrol et: {e}")
    except anthropic.RateLimitError:
        raise RuntimeError("Anthropic API rate limit aşıldı. Bir süre bekle.")
    except anthropic.APIConnectionError:
        raise RuntimeError("Anthropic API'ye bağlanılamadı. İnternet bağlantını kontrol et.")
    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API hatası: {e}")

    raw_text = response.content[0].text.strip()

    # JSON bloğu içindeyse temizle
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)
        sectors = data["sectors"]
        # keywords_tr + keywords_en → birleşik keywords listesi (Apify için)
        for s in sectors:
            s["keywords_tr"] = s.get("keywords_tr", [])
            s["keywords_en"] = s.get("keywords_en", [])
            s["keywords"] = s["keywords_tr"] + s["keywords_en"]
        return sectors
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Model yanıtı parse edilemedi: {e}\nHam yanıt: {raw_text[:300]}")


JOB_TITLE_PROMPT = """Sen B2B soğuk e-posta kampanyaları için hedef kitle belirleyen uzman bir growth hacker'sın.

Ana sektör: "{sector}"
Hedeflenen alt-sektörler: {sub_sectors}

Görevin: Bu sektörlerdeki şirketlerde GERÇEK SATIN ALMA YETKİSİ veya KARAR VERME GÜCÜ olan pozisyonları belirle.

KRİTİK KURALLAR:
- SADECE şu profilleri dahil et:
  * C-Level: CEO, COO, CMO, CFO, CTO, Genel Müdür, Kurucu, Ortak
  * Director/VP level: Satış Direktörü, Pazarlama Direktörü, Satın Alma Direktörü, İş Geliştirme Direktörü
  * Manager level: Satış Müdürü, Pazarlama Müdürü, Satın Alma Müdürü, Operasyon Müdürü
  * Sahip/Ortak profili: İşletme Sahibi, Yönetici Ortak
- KESINLIKLE DAHIL ETME: İK, İnsan Kaynakları, HR, Muhasebe (CFO hariç), IT Destek, Sekreter, Asistan
- Her unvan hem Türkçe hem İngilizce olmalı (iki dilli — Apify her iki dilde de arama yapacak)
- Sektöre özel ve gerçekçi unvanlar üret — genel geçer değil
- Toplam 20-35 adet benzersiz unvan üret

Yanıtını YALNIZCA aşağıdaki JSON formatında ver. Başka hiçbir metin ekleme:

{{
  "job_titles": [
    {{
      "tr": "Türkçe Unvan",
      "en": "English Title",
      "authority_level": "C-Level|Director|Manager|Owner",
      "why": "Bu unvanın satın alma/karar yetkisi neden var (tek cümle)"
    }}
  ]
}}"""


def generate_job_titles(sector: str, sub_sectors: list[str]) -> list[dict]:
    """
    Sektöre özel karar verici job title'ları üretir (TR + EN).
    Returns: [{"tr": str, "en": str, "authority_level": str, "why": str}]
    """
    client = get_client()
    sub_sectors_str = ", ".join(sub_sectors[:10])

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            messages=[
                {
                    "role": "user",
                    "content": JOB_TITLE_PROMPT.format(
                        sector=sector,
                        sub_sectors=sub_sectors_str
                    )
                }
            ]
        )
    except anthropic.AuthenticationError:
        raise ValueError("Anthropic API anahtarı geçersiz. .env dosyasını kontrol et.")
    except anthropic.NotFoundError as e:
        raise ValueError(f"Model bulunamadı: {e}")
    except anthropic.RateLimitError:
        raise RuntimeError("Anthropic API rate limit aşıldı. Bir süre bekle.")
    except anthropic.APIConnectionError:
        raise RuntimeError("Anthropic API'ye bağlanılamadı.")
    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API hatası: {e}")

    raw_text = response.content[0].text.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)
        return data["job_titles"]
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"Job title yanıtı parse edilemedi: {e}\nHam yanıt: {raw_text[:300]}")


LEAD_ANALYSIS_PROMPT = """Sen B2B soğuk e-posta kampanyaları için lead kalite kontrolü yapan bir analistsin.

Hedef sektör: "{target_sector}"
Sunulan otomasyon/hizmet: "{automation}"
Yetkili adı (first_name): "{first_name}"
Şirketin web sitesi ana sayfa metni:
---
{website_text}
---

Görevin iki parçadan oluşuyor:

1. RELEVANCE (Alaka Düzeyi): Bu şirket hem hedef sektörde hem sunulan otomasyon/hizmetten faydalanabilecek profilde mi?
   - "Doğrudan İlişkili": Sektör uyumlu VE otomasyon bu şirkete somut değer katabilir
   - "Belki": Sektör uyumlu ama otomasyon uyumu belirsiz, ya da tam tersi
   - "Alakası Yok": Tamamen farklı sektör veya otomasyon hiç uymuyor

2. UNVAN (Hitap): Yetkilinin adı Türkçe bir isim mi?
   - Türkçe erkek ismi → "Bey"
   - Türkçe kadın ismi → "Hanım"
   - Yabancı isim, cinsiyet belirsiz veya web metni yoksa → "" (boş string)

Web sitesi metni boşsa veya site açılmadıysa: relevance="Belki", unvan="" döndür.

Yanıtını YALNIZCA şu JSON formatında ver:
{{"relevance": "Doğrudan İlişkili|Belki|Alakası Yok", "reason": "Tek cümle neden", "unvan": "Bey|Hanım|"}}"""


def analyze_lead(first_name: str, website_text: str, target_sector: str, automation: str = "") -> dict:
    """
    Tek bir lead'i web sitesi metni üzerinden analiz eder.
    Returns: {"relevance": str, "reason": str, "unvan": str}
    """
    client = get_client()

    prompt = LEAD_ANALYSIS_PROMPT.format(
        target_sector=target_sector,
        automation=automation or "Yapay Zeka & Otomasyon çözümleri",
        first_name=first_name or "Bilinmiyor",
        website_text=website_text[:2000] if website_text else "(Web sitesi metni alınamadı)"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
    except anthropic.APIError as e:
        return {"relevance": "Belki", "reason": f"API hatası: {e}", "unvan": ""}

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        result = json.loads(raw)
        return {
            "relevance": result.get("relevance", "Belki"),
            "reason": result.get("reason", ""),
            "unvan": result.get("unvan", ""),
        }
    except json.JSONDecodeError:
        return {"relevance": "Belki", "reason": "Parse hatası", "unvan": ""}


# ---------------------------------------------------------------------------
# ŞİRKET BÜYÜKLÜĞÜ ÖNERİSİ
# ---------------------------------------------------------------------------

COMPANY_SIZE_OPTIONS = [
    {"label": "🏠 Mikro (1–10 çalışan)",        "value": "1-10"},
    {"label": "🏪 Küçük (11–50 çalışan)",        "value": "11-50"},
    {"label": "🏢 Orta-Küçük (51–200 çalışan)",  "value": "51-200"},
    {"label": "🏬 Orta-Büyük (201–500 çalışan)", "value": "201-500"},
    {"label": "🏛️ Büyük (501–1.000 çalışan)",    "value": "501-1000"},
    {"label": "🏗️ Kurumsal (1.001–5.000)",        "value": "1001-5000"},
    {"label": "🌐 Büyük Kurumsal (5.001–10.000)", "value": "5001-10000"},
    {"label": "🌍 Dev Şirket (10.000+)",           "value": "10000+"},
]

COMPANY_SIZE_PROMPT = """Sen B2B satış stratejisti ve growth hacker'sın.

Hedef sektör: "{sector}"
Sunulan otomasyon/hizmet: "{automation}"

Görevin: Bu sektöre bu otomasyon/hizmeti satmak için hangi şirket büyüklüklerini hedeflemek en mantıklı?
Türkiye pazarı bağlamında düşün.

Seçenekler ve value'ları:
{size_options}

KURALLAR:
- 2 ile 4 arasında büyüklük seç — fazlası odak kaybı, azı lead sayısını kısar
- "recommended" listesinde sadece value'ları yaz (örn: "1-10")
- Her seçim için kısa ve somut neden yaz (satış stratejisi açısından)
- Çok büyük şirketlere satmak genellikle satış döngüsünü uzatır — küçük KOBİ'ler daha hızlı karar verir

Yanıtını YALNIZCA JSON formatında ver:
{{
  "recommended": ["value1", "value2"],
  "reasoning": {{
    "value1": "Neden bu büyüklük ideal (1 cümle)",
    "value2": "Neden bu büyüklük ideal (1 cümle)"
  }}
}}"""


def recommend_company_sizes(sector: str, automation: str) -> dict:
    """
    Sektör + otomasyon kombinasyonuna göre ideal şirket büyüklüklerini önerir.
    Returns: {"recommended": [str], "reasoning": {value: str}}
    """
    client = get_client()

    size_options_str = "\n".join(
        f'- label: "{o["label"]}", value: "{o["value"]}"'
        for o in COMPANY_SIZE_OPTIONS
    )

    prompt = COMPANY_SIZE_PROMPT.format(
        sector=sector,
        automation=automation or "Yapay Zeka & Otomasyon çözümleri",
        size_options=size_options_str,
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}]
        )
    except anthropic.APIError as e:
        return {"recommended": ["11,50", "51,200"], "reasoning": {}}

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"recommended": ["11,50", "51,200"], "reasoning": {}}


# ---------------------------------------------------------------------------
# ADIM 4 — E-POSTA SEKANS YAZIMI
# ---------------------------------------------------------------------------

SECTOR_KNOWLEDGE = """
Sattığımız hizmet: Yapay Zeka & Otomasyon çözümleri (WhatsApp bot, CRM entegrasyonu,
içerik üretimi, lead üretimi, raporlama otomasyonu, scraping, randevu sistemleri vb.)

Hedef sektör bazlı acı noktaları ve sunulan çözümler:

SAĞLIK (Klinikler, diş, estetik, diyetisyen, psikolog):
- Acı: randevu kaosu, no-show oranı, Google yorum yönetimi, sekreter iş yükü
- Çözüm: WhatsApp randevu botu, otomatik hatırlatma & iptal doldurma, yorum otomasyonu
- Fiyat: 13.500–22.500 TL/ay | Karar: hızlı, dijitalleşmeye açık

E-TİCARET (Trendyol satıcıları, Shopify/ikas mağazaları):
- Acı: ürün açıklaması yazma yükü, rakip fiyat takibi, kargo/iade/stok destek yükü, yorum analizi
- Çözüm: AI ürün açıklaması, rakip fiyat botu, destek chatbot, yorum analitik
- Fiyat: 15.000–22.500 TL/ay | Retainer kaybı düşük, upsell kolay

SERBEST MESLEK (Avukat, mali müşavir, mimar, danışman):
- Acı: onboarding kaosu, belge toplama, rutin iletişim zaman kaybı
- Çözüm: onboarding otomasyonu, belge toplama botu, rutin e-posta/WhatsApp akışları
- Fiyat: 15.000–22.500 TL/ay | Fiyat hassasiyeti düşük, güçlü referans ağı

EMLAK (Ofisler, bağımsız danışmanlar, müteahhitler):
- Acı: ilan takibi zaman kaybı, lead kalifikasyonu, sosyal medya içerik üretimi
- Çözüm: Sahibinden/Hepsiemlak scraping, WhatsApp ön eleme, CRM entegrasyonu, Instagram içerik
- Fiyat: 15.000–22.500 TL/ay | ROI hızlı görülür, satış süreci kısa

YEREL İŞLETMELER (Restoran, cafe, berber, kuaför, fitness, güzellik):
- Acı: Google yorumlarına cevap verme, sosyal medya içerik üretimi, rezervasyon kaosu
- Çözüm: Google Business otomasyonu, yorum cevaplama botu, Instagram içerik, WhatsApp rezervasyon
- Fiyat: 13.500–18.000 TL/ay | Referansla büyüyor, volume iş

EĞİTİM & KOÇLUK (Online kurs, özel ders, koçlar):
- Acı: kurs satış funnel'i yönetimi, öğrenci onboarding, içerik üretim yükü
- Çözüm: satış funnel otomasyonu, onboarding akışı, içerik reuse (canlı ders → reels/blog/email)
- Fiyat: 15.000–22.500 TL/ay | "Bu bana da lazım" diyerek satın alan kitle

AJANSLAR & PAZARLAMA (Dijital ajans, sosyal medya, performans):
- Acı: manuel raporlama (Meta+Google+GA4), içerik üretim darboğazı, brief kaosu
- Çözüm: birleşik raporlama dashboard'u, AI içerik hattı, brief otomasyonu
- Fiyat: 18.000–22.500 TL/ay | B2B dil ortak, 1-2 meeting'de kapanıyor

İNŞAAT & SANAYİ (KOBİ üretici, ihracatçı):
- Acı: teklif hazırlama saatleri, yabancı dil katalog üretimi, ihracat lead'i bulma
- Çözüm: AI teklif hazırlama, çok dilli katalog, Alibaba/fuar takibi, soğuk outreach
- Fiyat: 18.000–22.500 TL/ay | Fiyat hassasiyeti çok düşük, yıllık ciro milyonlar

FİNANS & SİGORTA (Acente, broker, kredi danışmanı):
- Acı: poliçe yenileme takibi, teklif toplama yükü, cross-sell fırsatı kaçırma
- Çözüm: yenileme hatırlatma botu, teklif toplama otomasyonu, WhatsApp destek, cross-sell akışı
- Fiyat: 15.000–22.500 TL/ay | Retainer kaybı çok düşük, düzenli işlem hacmi

OTOMOTİV (Galeri, servis, yedek parça, oto kiralama):
- Acı: ilan takibi (Sahibinden/Arabam), lead nitelendirme, servis randevu yönetimi
- Çözüm: scraping botu, WhatsApp lead botu, servis randevu sistemi, kasko/muayene hatırlatma
- Fiyat: 15.000–22.500 TL/ay | Satış döngüsü kısa, cash akışı iyi
"""

EMAIL_SEQUENCE_PROMPT = """Sen 10+ yıllık deneyimli bir B2B soğuk e-posta uzmanısın. Yüksek açılma ve dönüşüm oranı yaratmak için yazıyorsun.

BAĞLAM:
{sector_knowledge}

HEDEF SEKTÖR: {target_sector}
ALT SEKTÖRLER: {sub_sectors}
SUNULAN OTOMASYON/HİZMET: {automation}

ÖNEMLİ: Tüm e-postalar yukarıdaki otomasyon/hizmete odaklanmalı. Acı noktaları, rakamlar ve CTA'lar bu otomasyon/hizmet üzerinden kurulmalı.

YAZIM KURALLARI (BUNLARA KESİNLİKLE UY):
1. Hitap: Her zaman "Merhaba {{{{first_name}}}} {{{{unvan}}}}," ile başla (çift süslü parantez — template değişkeni)
2. Uzunluk: İlk mail max 80 kelime, follow-up'lar max 50 kelime
3. Ton: Samimi, direkt, kurumsal değil — sanki tanıdık biri gibi yaz
4. YASAK ifadeler: "Umarım", "saygılarımla", "ihtiyaç var mı", "hizmetlerimiz", "sunmaktayız", "iletişime geçebilirsiniz"
5. Her mail TEK bir CTA içermeli — soru formatında, evet/hayır cevabı mümkün olmamalı
6. Acı noktasından başla — çözümü ikinci cümlede ver
7. Sunulan otomasyona özel somut rakam veya örnek ekle (zaman tasarrufu, gelir artışı, vb.) — gerçekçi tahminler yeterli
8. Konu satırı max 7 kelime, merak uyandıran veya sorular içeren

E-POSTA SEKANS YAPISI:
- email_1_a: Acı Noktası odaklı (Pain) — bu otomasyonun çözdüğü somut problemi öne çıkar
- email_1_b: Sosyal Kanıt odaklı (Proof) — "X sektöründen başka firmalar bunu yapıyor" açısı
- email_1_c: Merak uyandıran (Curiosity) — ürünü/hizmeti direkt söyleme, soru sor
- followup_1: 2. gün — değer katan kısa içerik (ipucu, vaka, rakam)
- followup_2: 2. gün sonra — farklı açı, farklı acı noktası
- followup_3: 4. gün — break-up maili, demo teklifi, net aksiyon

Yanıtını YALNIZCA aşağıdaki JSON formatında ver. Türkçe yaz:

{{
  "email_1_a": {{"subject": "...", "body": "..."}},
  "email_1_b": {{"subject": "...", "body": "..."}},
  "email_1_c": {{"subject": "...", "body": "..."}},
  "followup_1": {{"subject": "...", "body": "..."}},
  "followup_2": {{"subject": "...", "body": "..."}},
  "followup_3": {{"subject": "...", "body": "..."}}
}}"""


def generate_email_sequences(target_sector: str, sub_sectors: list[str], automation: str = "") -> dict:
    """
    Hedef sektöre özel soğuk e-posta sekansı üretir.
    Returns: {
      "email_1_a": {"subject": str, "body": str},
      "email_1_b": ..., "email_1_c": ...,
      "followup_1": ..., "followup_2": ..., "followup_3": ...
    }
    """
    client = get_client()

    prompt = EMAIL_SEQUENCE_PROMPT.format(
        sector_knowledge=SECTOR_KNOWLEDGE,
        target_sector=target_sector,
        sub_sectors=", ".join(sub_sectors[:8]),
        automation=automation or "Yapay Zeka & Otomasyon çözümleri",
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
    except anthropic.AuthenticationError:
        raise ValueError("Anthropic API anahtarı geçersiz.")
    except anthropic.RateLimitError:
        raise RuntimeError("Rate limit aşıldı.")
    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API hatası: {e}")

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"E-posta sekansı parse edilemedi: {e}\nHam: {raw[:400]}")
