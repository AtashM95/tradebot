# AGENTS.md — Ultimate Trading Bot v2 (Codex Guidance)

## 0) Amaç
Bu repo, Windows PC üzerinde (Python 3.10) çalışan, **yalnızca ABD hisseleri** için tasarlanmış bir trading bot içerir:
- **Long-only swing** (tipik 1–2 hafta elde tutma)
- Evren: **100–200 sembol** (kullanıcı watchlist)
- Portföy: **10–15 eşzamanlı pozisyon** (tek hisseye sermaye kilitleme yok)
- Broker: **Alpaca** (Paper önce; Live kilitli)

Codex: Aşağıdaki kuralları **koru**. Zayıflatma veya kaldırma.

---

## 1) Değiştirilemez Ürün Gereksinimleri (Mutlaka Korunacak)
1) **Modlar (3):**
   - `backtest` (5 yıl + walk-forward)
   - `paper` (Alpaca paper; varsayılan)
   - `live` (Alpaca live; ekstra onay + PIN ile kilit)
2) **Sadece ABD hisseleri:** options/crypto/FX/short/leveraged trade YOK.
3) **Analiz önceliği:**
   - Price Action = omurga
   - Teknik analiz = onay/filtre
   - Sentiment = zamanlama/risk filtresi
   - Fundamentals = evren/safety filtresi (entry timing değil)
4) **Çakışmasız mimari:**
   - Setup Gate (Price Action şart)
   - Stratejiler sadece `SignalIntent` üretir
   - Ensemble Aggregator tek `FinalSignal` üretir
   - Risk Manager veto + position sizing otoritesidir
   - Execution adapter (Alpaca) emir gönderir
5) **Fon yönetimi:**
   - risk-per-trade + ATR/stop tabanlı sizing
   - market regime’e göre exposure
   - haftalık + eşik rebalance
   - cash buffer %5–10
6) **Para yok senaryosu:**
   - Panelde **Funding Alert** (opsiyonel desktop bildirim)
   - swap/trim → partial entry → trade queue (TTL)
7) **MLOps-lite:**
   - incremental data/feature update
   - drift monitor (data + concept/performance drift)
   - retrain pipeline (weekly / perf / drift triggers)
   - walk-forward validation
   - Optuna ile HPO
   - Model Registry (versioning)
   - Paper shadow test
   - Promote / Rollback
8) **Tek tık UX:**
   - exe aç → web panel açılır
   - Start/Stop/Pause + Dry-Run
   - watchlist bulk paste
   - tek/seçili/tüm analiz
   - Test Center + Logs + raporlar

---

## 2) Secrets & Konfigürasyon (Sıkı)
- Gerçek API key/secret **asla** repo’ya yazma.
- Repo’da yalnızca `.env.example` bulunacak.
- `.env` **.gitignore** içinde olacak.
- Uygulama `.env` okumak için `python-dotenv` kullanacak.
- **LIVE kilidi:**
  - UI: “LIVE aç” checkbox + PIN (configurable)
  - Bu doğrulanmadan LIVE emri kesinlikle yasak.

---

## 3) Tercih Edilen Teknoloji (Windows/Python 3.10)
- Python 3.10
- Web UI: minimal ama kullanışlı panel (FastAPI veya Flask)
- Depolama: SQLite + market data cache (Parquet + sıkıştırma)
- Paketleme: PyInstaller
  - Varsayılan **onedir** (performans için). onefile sadece istenirse.
- Log: yapılandırılmış log + UI’da görüntülenebilir.

---

## 4) Repo Yapısı (Rehber)
Önerilen modüler yapı:
- `src/app/`          API server + bootstrap
- `src/ui/`           web panel (server-rendered veya static)
- `src/core/`
  - `contracts/`      Pydantic kontratlar (aşağıda)
  - `data/`           Alpaca data fetch + cache
  - `features/`       indicator + price action feature set
  - `strategies/`     plugin benzeri modüler stratejiler (stateless)
  - `ensemble/`       tek FinalSignal üretir
  - `risk/`           veto + sizing + limitler + cash check
  - `portfolio/`      allocations + rebalance + exposure
  - `execution/`      Alpaca adapter (paper/live)
  - `backtest/`       walk-forward backtest
  - `ml/`             drift + retrain + registry + shadow test
  - `journal/`        trades/fills + metrics
  - `monitoring/`     health + alerts
- `tests/`
- `scripts/`
- `data/ models/ logs/` (runtime folders)

---

## 5) Kontratlar (Bozulmayacak)
Modüller arası iletişim **typed** kontratlarla yapılacak (Pydantic).
Minimum:
- `Bar`, `BarSeries`
- `Features` (+ schema/version)
- `SignalIntent` (symbol, direction=LONG, confidence, entry, stop, tp, reasons, ts)
- `FinalSignal` (single output per symbol per cycle)
- `RiskDecision` (approved/veto, size/shares, constraints, reasons)
- `OrderRequest`, `OrderResult`, `FillEvent`
- `FundingAlert` (missing_cash, proposed_actions: swap/partial/queue)
- `ModelVersionMeta` (id, trained_range, feature_schema, metrics)

Kurallar:
- Stratejiler ASLA emir göndermez.
- Stratejiler stateless; sadece `SignalIntent` üretir.
- Risk Manager tek sizing otoritesi.
- Execution adapter Alpaca ile konuşan tek yerdir.

---

## 6) Orchestrator Akışı (Tek otorite)
Tek orchestrator:
1) config load (mode, watchlist, risk, toggles)
2) data update (incremental)
3) feature compute
4) regime filter
5) setup gate (price action)
6) strategies → list[SignalIntent]
7) ensemble → FinalSignal
8) risk → RiskDecision (cash check dahil)
9) insufficient cash → FundingAlert; order YOK
10) approved → execution (paper/live)
11) journal + performance
12) UI refresh + alerts/logs

---

## 7) “Çalışıyor mu?” = Test Center PASS/FAIL
Panelde Test Center olmalı ve şu kontroller PASS/FAIL vermeli:
1) Account Check (paper): Alpaca account okunuyor
2) Data Check: AAPL bar çek → feature hesapla
3) Dry-Run: SignalIntent + RiskDecision üret (order yok)
4) Paper Order Check: min-size order gönder → status al
5) Funding Alert Check: nakit yetersiz + güçlü sinyal → FundingAlert üret
6) Backtest Check: küçük watchlist ile walk-forward raporu üret

Hata olursa net hata ve “ne yapmalıyım” yönlendirmesi göster.

---

## 8) Kod Standartları
- Deterministik, test edilebilir fonksiyonlar.
- Global state saklama; dependency injection tercih.
- Type hints + docstrings + anlamlı log.
- Feature hesaplaması tek yerde; strateji içinde tekrar hesaplama yok.
- Walk-forward zorunlu; son dönem holdout final doğrulama.

---

## 9) Komutlar (Codex bunları kullanmalı)
Windows PowerShell:
- venv:
  - `py -3.10 -m venv .venv`
  - `.venv\Scripts\Activate.ps1`
  - `python -m pip install -U pip`
  - `pip install -r requirements.txt`
- run:
  - `python -m src.app.main` (veya README’de tanımlı entrypoint)
- tests:
  - `pytest -q`
- build:
  - `python scripts/build_windows.py` (PyInstaller; panel otomatik açılmalı)

---

## 10) PR/Review Kuralları
- Secret/anahtar loglama yok.
- LIVE mod: kilitler ve PIN doğrulaması olmadan emir yok.
- Kontrat değişirse testleri güncelle.
- Yeni strateji eklenirse:
  - Strategy interface
  - required_features deklarasyonu
  - stateless
  - en az 1 unit test

END
