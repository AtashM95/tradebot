# Ultimate Trading Bot v2 (US Stocks • Long-Only Swing • Alpaca)

Windows PC üzerinde (Python 3.10) çalışan, **yalnızca ABD hisseleri** için tasarlanmış **long-only swing** (1–2 hafta) trading botu.
Bot, 100–200 sembollük watchlist’i analiz eder; en iyi fırsatları seçer; fon/risk yönetimi uygular; Alpaca üzerinden **Paper** ve (kilitli) **Live** emir gönderir.

## Temel Özellikler
- **3 Mod:**
  - `backtest`: 5 yıl veri + **walk-forward**
  - `paper`: Alpaca paper trading (**varsayılan**)
  - `live`: Alpaca live (UI kilidi + PIN şart)
- **Analiz omurgası:** Price Action + Teknik onay + Sentiment filtre + Fundamentals güvenlik filtresi
- **Strateji kütüphanesi:** trend-following, breakout, pullback/retest, RSI momentum, candlestick patterns, Fibonacci pullback, volume confirmation
- **Çakışmasız mimari:** Setup Gate → Strategies(SignalIntent) → Ensemble(FinalSignal) → Risk(veto+sizing) → Execution(Alpaca) → Journal/Performance → UI
- **Fon Yönetimi:** 10–15 pozisyon, risk-per-trade, ATR/stop sizing, cash buffer %5–10, haftalık rebalance
- **“Para yok” senaryosu:** Funding Alert (panel + opsiyonel desktop) + swap/trim + partial entry + trade queue (TTL)
- **MLOps-lite:** drift monitor → retrain pipeline → model registry → shadow paper test → promote/rollback
- **Tek tık deneyim:** exe çalıştır → web panel açılır → Start/Stop/Pause + Dry-Run

---

# 1) Kurulum (Windows • Python 3.10)

## 1.1 Ön koşullar
- Windows 10/11
- Python 3.10
- Git (opsiyonel ama önerilir)

## 1.2 Repo’yu indir / klonla
```bash
git clone <REPO_URL>
cd <REPO_FOLDER>
```

## 1.3 Bağımlılıkları yükle
```bash
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

---

# 2) Çalıştırma
```bash
python -m src.app.main
```
Tarayıcıda `http://127.0.0.1:5000` adresini açın.

## 2.1 Konfigürasyon
- `.env.example` dosyasını `.env` olarak kopyalayın ve API anahtarlarını doldurun.
- `config/config.yaml` içindeki risk, circuit breaker, slippage ve alert ayarlarını projeye göre düzenleyin.

Örnek:
```bash
copy .env.example .env
```

## Start/Stop runner mantığı
- **Başlat:** Orkestratör arka planda döngüye girer ve `cycle_interval_seconds` (varsayılan 600 sn) aralığıyla analiz çalıştırır.
- **Duraklat:** Döngü beklemeye alınır, yeni analiz yapılmaz.
- **Durdur:** Döngü tamamen kapanır.

## Arayüz dili
- Arayüz dili varsayılan olarak **Türkçe**’dir.

---

# 3) Testler
```bash
pytest -q
```

---

# 4) Stress Test (CLI)
```bash
python scripts/run_stress_test.py --symbols AAPL,MSFT --shock -0.1
```

---

# 5) Anahtar Rotasyonu (Security Note)
- API anahtarlarınızı belirli aralıklarla değiştirin.
- Eski anahtarları Alpaca panelinden devre dışı bırakın.
- `.env` dosyasını **asla** commit etmeyin.
