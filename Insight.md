# Insight.md — Analisis & Integrasi Capstone-Tempa
> Dibuat: 28 Mei 2026
> Tujuan: Memberikan pemahaman utuh tentang pipeline, model, dan arsitektur integrasi

---

## DAFTAR ISI

1. [Gambaran Proyek](#1-gambaran-proyek)
2. [⚠️ KEKURANGAN KRITIS: Tidak Ada Data Cost (HPP)](#2-⚠️-kekurangan-kritis-tidak-ada-data-cost-hpp)
3. [Analisis File Per File](#3-analisis-file-per-file)
4. [Model yang Ada (K-Means)](#4-model-yang-ada-k-means)
5. [Model yang Akan Datang (XGBoost & Apriori)](#5-model-yang-akan-datang-xgboost--apriori)
6. [Cara Integrasi Model](#6-cara-integrasi-model)
7. [Rekomendasi App yang Bisa Dibuat](#7-rekomendasi-app-yang-bisa-dibuat)
8. [Catatan Penting](#8-catatan-penting)

---

## 1. Gambaran Proyek

**G Coffee Shop** — jaringan kedai kopi di Malaysia (Kuala Lumpur, Selangor, Putrajaya) dengan:
- **10 gerai**, **8 menu minuman**
- ~14,6 juta transaksi (Juli 2023 – Juni 2025)
- ~2,2 juta pengguna terdaftar
- Total Revenue ~RM 444 juta (~Rp 1,55 triliun)
- Mata uang asli: **Ringgit Malaysia (RM)**

**Tujuan Akhir:** Membangun **Voucher & Bundling Recommendation System** yang memberikan rekomendasi voucher dan bundling TEPAT SASARAN.

**3 Model Utama:**
1. **Segmen pelanggan** (siapa) → K-Means Clustering ✅ SUDAH
2. **Asosiasi produk** (apa) → Apriori ⏳ MENUNGGU
3. **Forecasting permintaan** (kapan) → XGBoost ⏳ MENUNGGU

---

## 2. ⚠️ KEKURANGAN KRITIS: Tidak Ada Data Cost (HPP)

### 2.1 Masalah Utama

Dataset hanya memiliki kolom `price` (harga jual) di tabel `menu_items`. **Tidak ada kolom `cost` (Harga Pokok Produksi/HPP)** untuk satu pun dari 8 item menu.

**Akibatnya:**
```
Margin Riil = (Price - Cost) / Price ← ❌ TIDAK BISA DIHITUNG
```

Tanpa data margin riil:
- **Risiko kanibalisasi**: Diskon 25% pada item dengan margin asli 20% → **margin NEGATIF 5%** — artinya kafe RUGI di setiap transaksi.
- **Tidak bisa validasi profitabilitas**: Rekomendasi voucher tidak bisa diverifikasi dampaknya terhadap profit, hanya terhadap revenue.
- **Scoring komponen `S_margin` menjadi estimatif**, bukan berdasarkan data aktual.

### 2.2 Dampak ke Seluruh Sistem

| Area | Dampak Ketiadaan Data Cost |
|------|---------------------------|
| **Margin Safety Check** | Tidak bisa menghitung margin riil → pakai COGS proxy (estimasi industri) |
| **Diskon Maksimal** | Batas 25% membantu tapi tidak menjamin keamanan margin (contoh: diskon 25% di item margin 20% tetap rugi) |
| **Item Tiering** | Tidak bisa validasi apakah tier pricing sesuai dengan struktur biaya |
| **Revenue vs Profit** | App hanya optimalkan **revenue**, bukan **profit** — riskan untuk bisnis |
| **A/B Testing** | Tidak ada baseline profit untuk mengukur keberhasilan |

### 2.3 Solusi Sementara: COGS Proxy

Karena tidak ada data cost aktual, digunakan **estimasi berbasis standar industri** (dari `ANALISIS_LANJUTAN_REKOMENDASI.md`):

| Kategori Item | Rentang HPP (% dari Price) | Asumsi Default |
|--------------|---------------------------|---------------|
| **Coffee-based** (Espresso, Americano, Latte, dll) | 12% – 22% | **18%** |
| **Non-Coffee** (Hot Chocolate, Matcha Latte) | 18% – 30% | **24%** |

```python
COGS_PROXY = {
    "coffee": {"min": 0.12, "default": 0.18, "max": 0.22},
    "non-coffee": {"min": 0.18, "default": 0.24, "max": 0.30}
}
```

**Contoh Simulasi Risiko:**
| Item | Harga (RM) | Estimasi Cost (18%) | Diskon 25% | Harga Jual Efektif | Margin Efektif |
|------|-----------|--------------------|-----------|-------------------|----------------|
| Latte | 9.0 | 1.62 | 25% (2.25) | 6.75 | **-8.6%** 🔴 RUGI |
| Matcha Latte | 10.0 | 2.40 | 25% (2.50) | 7.50 | **-6.7%** 🔴 RUGI |
| Espresso | 6.0 | 1.08 | 15% (0.90) | 5.10 | **+17.6%** 🟢 AMAN |

> ⚠️ **Peringatan:** Diskon 25% pada item coffee (asumsi margin 18%) SUDAH MENGHASILKAN KERUGIAN. Inilah mengapa guard mechanism (voting system) sangat penting.

### 2.4 Prioritas ke Depan

**Kumpulkan data cost aktual** dari operasional kafe adalah **prioritas #1** untuk meningkatkan akurasi sistem. Tanpa ini:
- Semua rekomendasi diskon didasarkan pada estimasi
- Risiko kerugian tidak bisa diukur secara presisi
- Sistem hanya bisa optimasi **revenue**, BUKAN **profit**

> **Rekomendasi:** Jika memungkinkan, lakukan pendekatan ke pemilik kafe untuk mendapatkan data HPP riil per item. Data ini biasanya tersedia di sistem inventory atau purchasing.

---

## 3. Analisis File Per File

### 3.1 Notebook Pipeline (Urutan Eksekusi)

| No | File | Tujuan | Output Penting |
|----|------|--------|----------------|
| 1 | `01-LoadData.ipynb` | Load 7 CSV dari Kaggle, optimasi memori | `.parquet` files (raw) |
| 2 | `02-DataValidation.ipynb` | Standardisasi tipe data, validasi FK/PK, cek umur/tanggal | Validated `.parquet` |
| 3 | `03-DataCleaning.ipynb` | Hapus duplikat, rekonsiliasi amount, capping outlier P99, koreksi diskon | `transactions_capping.parquet`, `transaction_items_cleaned.parquet` |
| 4 | `03-DataCleaning-Rev.ipynb` | Sama + audit trail (`original_amount_header`) + deterministic dedup | Sama + kolom backup |
| 5 | `04-JoinData.ipynb` | LEFT JOIN semua tabel → Master denormalized | `df_Master_Final.parquet` |
| 6 | `04-JoinData-Rev.ipynb` | Sama + rename columns lebih rapi | Sama |
| 7 | `05-FeatureEngineering.ipynb` | Fitur temporal, member_status, is_voucher_used, agregasi transaksi, RFM, Apriori basket, train/test split | `df_Master_FE.parquet`, `df_transaction_features.parquet`, `df_rfm.parquet`, `df_basket_apriori.parquet`, `df_train.parquet`, `df_test.parquet` |
| 8 | `05-FeatureEngineering-Rev.ipynb` | Sama + **deterministic aggregation**, **scaled RFM**, **boolean encoding**, **temporal split 80/20** | Sama (lebih siap modeling) |
| 9 | `06-EDA.ipynb` & `06-EDA-Rev.ipynb` | Visualisasi & business insights | Charts & analysis |

### 3.2 File Model

| File | Tujuan | Status |
|------|--------|--------|
| `Model-KMeans.ipynb` | K-Means clustering pada RFM → 4 segmen pelanggan | ✅ SELESAI |
| `model_kmeans_rfm.joblib` | Saved model K-Means (pickle) | ✅ READY |
| **XGBoost model** | Forecasting transaksi (belum ada file) | ⏳ DIKEMBANGKAN |
| **Apriori model** | Association rules (belum ada file) | ⏳ DIKEMBANGKAN |

### 3.3 File Data Utama (Parquet)

| File | Baris | Kegunaan |
|------|-------|----------|
| `df_Master_Final.parquet` | 26.885.688 | Master item-level (40 kolom) — sumber utama analisis |
| `df_Master_FE.parquet` | 26.885.688 | Master + fitur engineering (hour, month, dll) |
| `df_transaction_features.parquet` | 14.623.691 | 1 baris/transaksi — siap untuk ML (XGBoost) |
| `df_rfm.parquet` | 2.196.257 | RFM per user + scaled features — siap K-Means |
| `df_basket_apriori.parquet` | 9.064.669 | Matriks biner 8 item — siap Apriori |
| `df_train.parquet` | 11.698.952 | Train set temporal (80%) |
| `df_test.parquet` | 2.924.739 | Test set temporal (20%) |

> **Catatan:** Tidak ada satupun file di atas yang mengandung kolom `cost` atau `hpp`. Semua nilai adalah harga jual (`price`, `final_amount`, `original_amount`).

### 3.4 File Pendukung

| File | Kegunaan |
|------|----------|
| `function.py` | Class `CleaningData` + fungsi optimasi memori |
| `README.md` | Dokumentasi pipeline lengkap |
| `SourceOfTruth.md` | Data dictionary, ERD, lineage, governance |
| `ANALISIS_LANJUTAN_REKOMENDASI.md` | Strategi implementasi voucher engine (3 fase) — **berisi solusi COGS proxy** |
| `Rekomendasi_Strategi_Kafe.xlsx` | Prototipe rekomendasi voucher |

---

## 4. Model yang Ada (K-Means)

### 4.1 Detail K-Means

- **Input:** RFM dari `df_rfm.parquet` (Recency, Frequency, Monetary)
- **Transformasi terbaik:** **QuantileTransformer** (Silhouette: 0.4555, DBI: 0.7952)
- **Jumlah cluster optimal:** K=4
- **Saved model:** `model_kmeans_rfm.joblib` (via `joblib.dump`)

### 4.2 Hasil Segmentasi (4 Cluster)

| Cluster | Label | R_Mean (hari) | F_Mean (kali) | M_Mean (RM) | Jumlah | Strategi Voucher |
|---------|-------|--------------|--------------|-------------|--------|------------------|
| 0 | **Champions** | 138.6 | 3.0 | 88.2 | ~6.018 (sampel) | Non-monetary (size upgrade, double points) |
| 1 | **Lost Customers** | 86.9 | 1.0 | 30.9 | ~6.602 (sampel) | Diskon agresif 20-25% + SMS blast |
| 2 | **New Customers** | 27.2 | 3.1 | 94.9 | ~5.199 (sampel) | Bundle hemat (10-15%) + push notif |
| 3 | **At Risk** | 84.7 | 7.8 | 248.0 | ~4.144 (sampel) | Diskon moderat 12-15% + reaktivasi |

> **Catatan:** Jumlah di atas adalah hasil sampling 10%, bukan populasi penuh. Proporsi segmen di populasi penuh:
> - Champions: 494.866 (22,5%)
> - Loyal: 334.852 (15,2%)
> - At Risk: 549.064 (25,0%)
> - Regular: 817.475 (37,2%)

### 4.3 Cara Load & Pakai Model K-Means

```python
import joblib
import pandas as pd

# Load model
kmeans = joblib.load('model_kmeans_rfm.joblib')

# Load RFM data
rfm = pd.read_parquet('df_rfm.parquet')
# Note: model expects Quantile-transformed input
# You need to re-apply QuantileTransformer before predicting
```

---

## 5. Model yang Akan Datang (XGBoost & Apriori)

### 5.1 XGBoost Forecasting

**Tujuan:** Memprediksi volume transaksi harian per cabang untuk menentukan **KAPAN** diskon perlu diberikan.

**Data yang sudah siap:**
- `df_train.parquet` & `df_test.parquet` — temporal split 80/20
- Kolom siap pakai: `basket_size`, `final_amount`, `hour`, `month_name`, `day_name`, `city`, `member_status`, `is_weekend_bool`, `is_voucher_used_bool`

**Target variable (yang perlu didefinisikan):**
- `transaction_count` per hari per cabang (regression)
- Atau `demand_tier` (classification: low/medium/high)

**Feature engineering tambahan yang mungkin diperlukan:**
- Lag features (transaksi kemarin, seminggu lalu)
- Rolling averages (7-day, 30-day)
- Day-of-week, month-of-year encoding
- Holiday calendar Malaysia

### 5.2 Apriori Association Rules

**Tujuan:** Menemukan aturan asosiasi antar item untuk menentukan **APA** yang perlu di-bundle.

**Data yang sudah siap:**
- `df_basket_apriori.parquet` — matriks biner 9.064.669 transaksi × 8 item
- Sparsity: 70,59% — artinya 29,41% sel bernilai 1

**Cara pakai (template):**
```python
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules

df_basket = pd.read_parquet('df_basket_apriori.parquet')
# df_basket index = transaction_id, columns = item names, values = 0/1

frequent_itemsets = apriori(df_basket, min_support=0.01, use_colnames=True)
rules = association_rules(frequent_itemsets, metric="lift", min_threshold=1.2)
```

**Yang perlu ditentukan:**
- `min_support` threshold (default sering 0.01 - 0.05)
- `min_threshold` untuk lift (1.2 - 2.0)
- Metric untuk sorting (lift, confidence, atau conviction)

---

## 6. Cara Integrasi Model

### 6.1 Arsitektur Integrasi (3 Model → 1 Output)

```
                        ┌─────────────────────┐
                        │   INPUT DATA SOURCE  │
                        │  (df_Master_FE.parquet) │
                        └──────────┬──────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                ▼                  ▼                  ▼
        ┌───────────────┐ ┌──────────────┐ ┌──────────────┐
        │   K-MEANS      │ │   APRIORI    │ │   XGBOOST    │
        │   (Segmen)     │ │  (Asosiasi)  │ │ (Forecast)   │
        │                │ │              │ │              │
        │ Output:        │ │ Output:      │ │ Output:      │
        │ user_id →      │ │ rules:       │ │ Prediksi     │
        │ segment_label  │ │ {A}→{B} dgn  │ │ volume per   │
        │                │ │ lift, support│ │ (branch,day) │
        └───────┬───────┘ └──────┬───────┘ └──────┬───────┘
                │                │                │
                └────────────────┼────────────────┘
                                 ▼
                    ┌─────────────────────────────────┐
                    │   VOUCHER ENGINE                 │
                    │   (Scoring & Decision)           │
                    │                                  │
                    │   ⚠️ TANPA DATA COST (HPP):      │
                    │   Komponen S_margin menggunakan  │
                    │   COGS proxy (estimasi industri) │
                    │   BUKAN data aktual.             │
                    │                                  │
                    │   Score = w₁·S_segment           │
                    │         + w₂·S_time              │
                    │         + w₃·S_bundle            │
                    │         + w₄·S_margin (PROXY ⚠️) │
                    │         - w₅·P_cannibal          │
                    └─────────────┬────────────────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │   OUTPUT:                │
                    │   Rekomendasi Voucher    │
                    │   {branch, day, hour,    │
                    │    segment, discount%,   │
                    │    bundle_items,         │
                    │    incentive_type,       │
                    │    ⚠️ MARGIN: ESTIMASI}  │
                    └─────────────────────────┘
```

### 6.2 Dampak Ketiadaan Data Cost pada Scoring

**Komponen `S_margin`** — yang seharusnya mengukur keamanan margin — menjadi **estimatif** karena:

```python
def score_margin_safety(item_name, price, proposed_discount, item_tier_map):
    """
    ⚠️ FUNGSI INI MENGGUNAKAN ESTIMASI, BUKAN DATA AKTUAL.
    """
    # Guard 1: COGS Proxy (ESTIMASI INDUSTRI, BUKAN DATA RIIL)
    cogs_result = estimate_margin(item_name, price, proposed_discount)
    cogs_safe = cogs_result['is_safe']  # ← Based on assumption, not fact!
    
    # Guard 2: Item Tier (berdasarkan harga & popularitas, bukan biaya)
    tier_info = item_tier_map.get(item_name, {})
    
    # Guard 3: Discount Reasonableness (rule of thumb)
    
    # Hasil: score estimatif — TIDAK bisa menggantikan data cost aktual
    final_score = min(cogs_score, tier_score, reason_score)
    return {"score": final_score, "safety_level": safety, ...}
```

**Implikasi:**
- Jika COGS proxy terlalu rendah (misal margin aktual cuma 10%, bukan 18%): sistem akan **merekomendasikan diskon yang merugikan**.
- Jika COGS proxy terlalu tinggi: sistem akan **terlalu konservatif** dan kehilangan opportunity revenue.

### 6.3 Scoring Logic

**Rumus Skor:**
```
Score = w₁ × S_segment + w₂ × S_time + w₃ × S_bundle + w₄ × S_margin(ESTIMASI ⚠️) - w₅ × P_cannibal
```

**Bobot per Fase:**

| Komponen | Fase 1 (MVP) | Fase 2 (+Apriori) | Fase 3 (+Forecast) |
|----------|-------------|------------------|-------------------|
| S_segment (w₁) | 0.45 | 0.35 | 0.25 |
| S_time (w₂) | 0.30 | 0.20 | 0.15 |
| S_bundle (w₃) | 0.00 | 0.25 | 0.20 |
| S_margin (w₄) — ⚠️ ESTIMASI | 0.15 | 0.15 | 0.15 |
| P_cannibal (w₅) | 0.10 | 0.05 | 0.25 |

### 6.4 Integrasi dengan Data yang Ada

#### Step 1: Mapping K-Means ke Transaksi
```python
# df_rfm sudah punya: user_id, Recency, Frequency, Monetary, Cluster (dari K-Means)
# Gabungkan dengan df_transaction_features untuk mapping user → segment
df_trans = pd.read_parquet('df_transaction_features.parquet')
df_rfm = pd.read_parquet('df_rfm.parquet')

# Transaksi yang punya user_id (member)
df_member_trans = df_trans[df_trans['user_id'].notna()].merge(
    df_rfm[['user_id', 'Cluster']], on='user_id', how='left'
)
```

#### Step 2: Integrasi Apriori (setelah model selesai)
```python
# rules_df punya kolom: antecedents, consequents, lift, confidence, support
# Gabungkan rules dengan tier item dari ANALISIS_LANJUTAN

def get_bundle_recommendation(bought_items, rules_df, top_n=3):
    """Cari rule terbaik berdasarkan item yang sudah dibeli."""
    relevant = rules_df[rules_df['antecedents'].apply(
        lambda x: any(item in bought_items for item in x)
    )]
    return relevant.nlargest(top_n, 'lift')
```

#### Step 3: Integrasi Forecasting (setelah model selesai)
```python
# xgb_model.predict() → forecast_volume per (branch, date)
# Bandingkan dengan historical average untuk adjustment diskon

def adjust_discount(base_discount, forecast_volume, historical_avg):
    ratio = forecast_volume / historical_avg
    if ratio > 1.2:
        return max(0, base_discount - 0.05)  # Kurangi diskon
    elif ratio < 0.8:
        return min(0.25, base_discount + 0.05)  # Tambah diskon
    return base_discount
```

---

## 7. Rekomendasi App yang Bisa Dibuat

### 7.1 Nama Aplikasi

**"VoucherGen — G Coffee Smart Voucher & Bundling Recommender"**

### 7.2 Tipe App

**Recommendation Engine + Dashboard** — bisa berupa:
1. **Streamlit App** (cepat, interaktif) → Rekomendasi
2. **FastAPI Backend** (API endpoint) → Siap integrasi dengan POS/cashier system
3. **Dashboard** dengan Plotly/Dash → Visualisasi segmen & rekomendasi

### 7.3 Fitur Utama (3 Fase)

#### FASE 1 (Sekarang — Hanya K-Means ✅)
**App sudah bisa berjalan dengan K-Means saja!**

| Fitur | Deskripsi | Data yang Digunakan |
|-------|-----------|---------------------|
| **Segment Viewer** | Lihat distribusi segmen per cabang, per jam, per hari | `df_rfm.parquet`, `df_transaction_features.parquet` |
| **Segment-based Voucher Rule Engine** | Rekomendasi diskon berdasarkan aturan (rule-based): "IF segmen=Lost THEN diskon=20%" | Decision matrix (hardcoded) |
| **Peak Hour Detector** | Tentukan jam sibuk vs sepi per cabang | `df_transaction_features.parquet` |
| **Historical Voucher Impact** | Analisis dampak voucher historis terhadap basket_size | `df_transaction_features.parquet` |
| **Cluster Profiling** | Tabel & chart karakteristik tiap segmen | `df_rfm.parquet` |
| **⚠️ Margin Safety Warning** | Peringatan jika diskon melebihi estimasi margin aman | COGS proxy + Item tier |

**Contoh Output Fase 1 (dengan margin warning):**
| Cabang | Hari | Jam | Segmen | Diskon | Margin Check | Status |
|--------|------|-----|--------|--------|-------------|--------|
| G Coffee @ USJ | Weekend | 14-16 | At Risk | 15% | 🟢 SAFE (est.) | ✅ APPROVED |
| G Coffee @ KLCC | Weekday | 10-12 | Champions | 0% | 🟢 SAFE | ✅ APPROVED |
| G Coffee @ PJ | Weekday | 20-22 | Lost | 25% | 🔴 BLOCKED (est. margin -6.7%) | ❌ DITOLAK |
| G Coffee @ PJ | Weekday | 20-22 | Lost | 15% | 🟢 SAFE (est.) | ✅ APPROVED |

> ⚠️ **Catatan:** Status "SAFE" didasarkan pada **estimasi COGS proxy**, BUKAN data biaya aktual. Risiko kerugian tetap ada sampai data cost riil diperoleh.

#### FASE 2 (+ Apriori — setelah model selesai)
| Fitur Baru | Deskripsi |
|------------|-----------|
| **Bundle Recommender** | "Pelanggan yang membeli Latte juga sering membeli Matcha Latte" |
| **Smart Bundling Discount** | Diskon bundling berdasarkan lift rule (semakin tinggi lift, semakin besar diskon) |
| **Top Rules Viewer** | Network graph asosiasi produk |
| **⚠️ Bundle Margin Check** | Estimasi margin untuk bundle (apakah bundle ini profitabel?) |

#### FASE 3 (+ XGBoost — setelah model selesai)
| Fitur Baru | Deskripsi |
|------------|-----------|
| **Demand Forecast** | Prediksi volume transaksi 7 hari ke depan per cabang |
| **Dynamic Discount Timing** | Diskon otomatis disesuaikan: naik jika forecast turun, turun jika forecast naik |
| **What-If Simulation** | "Jika diskon 15% diberikan, berapa prediksi revenue uplift?" |
| **⚠️ Profit Simulation** | Simulasi dampak terhadap profit (dengan asumsi COGS proxy — tetap estimatif) |

### 7.4 Teknologi yang Direkomendasikan

| Komponen | Pilihan | Alasan |
|----------|---------|--------|
| **Frontend/App** | Streamlit | Cepat, Python-native, bagus untuk data apps |
| **Backend/API** | FastAPI | Performa tinggi, auto-docs, cocok untuk production |
| **Database** | DuckDB atau SQLite | Data sudah dalam parquet, DuckDB bisa query langsung parquet |
| **Visualisasi** | Plotly + Streamlit | Interaktif, support 3D, bagus untuk cluster viz |
| **Model Serving** | ONNX atau joblib | Model K-Means sudah joblib, XGBoost bisa ONNX |
| **Deployment** | Docker + Railway/Local | Portabel, mudah di-deploy |

### 7.5 Skenario User Flow (Fase 1)

```
User (Manajer Kafe) membuka App
    │
    ▼
Dashboard Utama:
├── [Overview] Total Revenue, ATV, Transaksi (hari ini vs kemarin)
├── [Segmen] Pie chart: Champions 22%, At Risk 25%, Lost 20%, New 33%
├── [Rekomendasi Voucher] Tabel rekomendasi per cabang + margin check (⚠️ ESTIMASI)
└── [Voucher Impact] Grafik: basket size dengan/sans voucher

User klik tab [Buat Rekomendasi Baru]
    │
    ▼
Form:
├── Pilih Cabang: [Dropdown 10 cabang]
├── Pilih Hari: [Weekday / Weekend / Specific Date]
├── Pilih Jam: [Range slider]
├── Pilih Target Segmen: [Checkbox: Champions, At Risk, Lost, New]
└── [Generate] button

    │
    ▼
Output:
├── Rekomendasi Voucher (tabel)
│   ├── Segmen: At Risk → Diskon 15%, Insentif: Potongan Harga
│   │   └── Margin Check: 🟢 SAFE (estimasi margin after discount: +12.5%)
│   ├── Segmen: Lost → Diskon 20%, Insentif: SMS Blast
│   │   └── Margin Check: 🟡 WARNING (estimasi margin after discount: +3.2%)
│   └── Segmen: Champions → Diskon 0%, Insentif: Double Points
│       └── Margin Check: 🟢 SAFE (no discount)
├── Estimated Impact (simulasi sederhana — hanya revenue, BUKAN profit)
├── ⚠️ Disclaimer: "Semua margin adalah ESTIMASI. Data cost (HPP) diperlukan untuk perhitungan profit yang akurat."
└── Export as CSV / Print
```

### 7.6 Quick Start untuk Streamlit App (Fase 1)

```python
# app.py — Streamlit MVP
import streamlit as st
import pandas as pd
import joblib
import plotly.express as px

# ⚠️ COGS PROXY — GANTI DENGAN DATA AKTUAL JIKA TERSEDIA
COGS_PROXY = {
    "coffee": 0.18,      # Estimasi HPP 18% dari harga jual
    "non-coffee": 0.24   # Estimasi HPP 24% dari harga jual
}

COFFEE_ITEMS = ['Espresso', 'Americano', 'Latte', 'Cappuccino', 'Flat White', 'Mocha']
NON_COFFEE_ITEMS = ['Hot Chocolate', 'Matcha Latte']

def estimate_margin(price, discount_rate, category='coffee'):
    """⚠️ ESTIMASI margin — BUKAN data aktual."""
    cogs_rate = COGS_PROXY[category]
    cost = price * cogs_rate
    effective_price = price * (1 - discount_rate)
    margin = (effective_price - cost) / effective_price
    return margin, cost

# Load data
df_trans = pd.read_parquet('df_transaction_features.parquet')
df_rfm = pd.read_parquet('df_rfm.parquet')
kmeans = joblib.load('model_kmeans_rfm.joblib')

st.title("☕ G Coffee — Voucher Recommendation System (MVP)")
st.warning("⚠️ SEMUA PERHITUNGAN MARGIN MENGGUNAKAN ESTIMASI COGS PROXY. Data cost (HPP) aktual diperlukan untuk akurasi profit.")

# Sidebar filters
branch = st.sidebar.selectbox("Pilih Cabang", df_trans['city'].unique())
day_type = st.sidebar.radio("Tipe Hari", ['Weekday', 'Weekend'])
hour_range = st.sidebar.slider("Jam", 0, 23, (10, 14))

# Filter data
filtered = df_trans[(df_trans['city'] == branch) & 
                     (df_trans['is_weekend'] == day_type) &
                     (df_trans['hour'].between(*hour_range))]

st.write(f"Transaksi terfilter: {len(filtered):,} transaksi")

# Simple rule-based recommendation with margin check
st.subheader("📋 Rekomendasi Voucher")
col1, col2 = st.columns(2)
with col1:
    st.info("**At Risk Segment** → Diskon 15%")
    # Cek margin untuk item rata-rata
    margin, cost = estimate_margin(8.0, 0.15, 'coffee')
    st.caption(f"Estimasi margin setelah diskon: {margin*100:.1f}% (cost est: RM{cost:.2f})")
with col2:
    st.info("**Lost Customers** → Diskon 20%")
    margin, cost = estimate_margin(8.0, 0.20, 'coffee')
    st.caption(f"Estimasi margin setelah diskon: {margin*100:.1f}% (cost est: RM{cost:.2f})")

st.caption("⚠️ Margin adalah ESTIMASI berdasarkan COGS proxy industri (coffee: 18%, non-coffee: 24%).")
```

---

## 8. Catatan Penting

### 8.1 ✅ Ringkasan yang SUDAH ADA

| Komponen | Status |
|----------|--------|
| Pipeline data lengkap (Load → Validate → Clean → Join → FE → EDA) | ✅ SELESAI |
| K-Means clustering (4 segmen: Champions, Lost, New, At Risk) | ✅ SELESAI |
| Model K-Means tersimpan (`model_kmeans_rfm.joblib`) | ✅ READY |
| RFM data + scaled features | ✅ READY |
| Train/test split temporal (80/20) | ✅ READY |
| Matriks Apriori (basket biner) | ✅ READY |
| Dokumentasi (README, SourceOfTruth, ANALISIS_LANJUTAN) | ✅ LENGKAP |
| Decision matrix & scoring logic | ✅ DIDEFINISIKAN |

### 8.2 ⏳ Yang Perlu Diselesaikan Teman

| Model | Data Input | File Output yang Diharapkan |
|-------|-----------|---------------------------|
| **XGBoost** | `df_train.parquet` (fitur) + `df_test.parquet` (target: volume transaksi) | Model file (`.pkl` / `.json`) + feature importance |
| **Apriori** | `df_basket_apriori.parquet` (matriks biner) | DataFrame rules: `antecedents`, `consequents`, `support`, `confidence`, `lift` |

### 8.3 ⚠️ YANG BELUM ADA (KEKURANGAN UTAMA)

| Kekurangan | Tingkat Keparahan | Dampak | Solusi Sementara |
|------------|------------------|--------|-----------------|
| **❌ Data Cost (HPP) per produk** | 🔴 **KRITIS** | Margin tidak bisa dihitung, risiko rugi | COGS proxy (estimasi industri: 18% coffee, 24% non-coffee) |
| ❌ Diskon maksimal 25% (constraint) | 🟡 SEDANG | Batasan dari stakeholder | Diterapkan sebagai global cap |
| ❌ XGBoost model | 🟡 SEDANG | Forecasting belum bisa | Rule-based peak hour detection |
| ❌ Apriori model | 🟢 RENDAH | Bundling belum data-driven | Heuristic bundling (populer + murah) |

### 8.4 Constraint Bisnis (WAJIB DIINGAT)

1. **Diskon maksimal 25%** — tidak boleh melebihi ini
2. **❌ Data Cost (HPP) BELUM ADA** — menggunakan COGS proxy (18% coffee, 24% non-coffee) — **INI ESTIMASI, BUKAN DATA AKTUAL**
3. **Nilai dalam RM** — konversi ke IDR (1 RM = Rp3.500) hanya untuk presentasi
4. **Voucher eksisting** di dataset: SALES77, SALES88, SALES99, SALES10, SALES11, MERDEKA, SALES66, SALES50

### 8.5 Item Tier (Dari ANALISIS_LANJUTAN_REKOMENDASI.md)

| Item | Harga (RM) | Kategori | Tier | Max Diskon | Estimasi Cost (18%/24%) | Margin Estimasi |
|------|-----------|----------|------|-----------|------------------------|----------------|
| Latte | 9.0 | Coffee | A (Signature) | 0% | RM 1.62 | 82.0% |
| Cappuccino | 8.0 | Coffee | A (Signature) | 0% | RM 1.44 | 82.0% |
| Mocha | 9.0 | Coffee | A (Signature) | 0% | RM 1.62 | 82.0% |
| Americano | 7.0 | Coffee | B (Commodity) | 10% | RM 1.26 | 82.0% |
| Espresso | 6.0 | Coffee | D (Low-Hanging) | 15% | RM 1.08 | 82.0% |
| Flat White | 8.0 | Coffee | D (Low-Hanging) | 15% | RM 1.44 | 82.0% |
| Matcha Latte | 10.0 | Non-coffee | C (Strategic) | 25% | RM 2.40 | 76.0% |
| Hot Chocolate | 8.0 | Non-coffee | C (Strategic) | 25% | RM 1.92 | 76.0% |

> ⚠️ Margin di atas adalah **ESTIMASI** berdasarkan COGS proxy. Margin aktual bisa berbeda signifikan.

### 8.6 Simulasi Risiko Diskon (Berdasarkan COGS Proxy)

| Item | Harga (RM) | Estimasi Cost | Diskon | Harga Efektif | Margin Efektif | Risiko |
|------|-----------|--------------|--------|--------------|---------------|--------|
| Latte | 9.0 | RM 1.62 | 25% | RM 6.75 | **-8.6%** 🔴 | **RUGI** |
| Matcha Latte | 10.0 | RM 2.40 | 25% | RM 7.50 | **-6.7%** 🔴 | **RUGI** |
| Matcha Latte | 10.0 | RM 2.40 | 15% | RM 8.50 | **+7.1%** 🟡 | WASPADA |
| Espresso | 6.0 | RM 1.08 | 15% | RM 5.10 | **+17.6%** 🟢 | AMAN |
| Espresso | 6.0 | RM 1.08 | 10% | RM 5.40 | **+20.0%** 🟢 | AMAN |

**Pelajaran:** Diskon 25% pada item coffee (asumsi HPP 18%) SUDAH MENGHASILKAN MARGIN NEGATIF. Item non-coffee dengan HPP lebih tinggi (24%) lebih rentan lagi.

### 8.7 Prioritas Pengembangan (Berdasarkan Impact)

1. **🔴 PRIORITAS #1: Kumpulkan data cost (HPP) aktual** — ini adalah single most impactful improvement. Tanpa ini sistem hanya bisa optimasi revenue, bukan profit.
2. 🟡 Selesaikan Apriori → bundling cerdas
3. 🟡 Selesaikan XGBoost → timing dinamis
4. 🟢 Bangun dashboard Fase 1 (MVP) sekarang — jangan menunggu semua model selesai

### 8.8 Referensi Lengkap

Baca dokumen berikut untuk detail lebih lanjut:
- **`README.md`** — Dokumentasi pipeline data (Load → Validate → Clean → Join → FE → EDA)
- **`SourceOfTruth.md`** — Data dictionary lengkap (47 kolom di df_Master_FE) — **tidak ada kolom cost**
- **`ANALISIS_LANJUTAN_REKOMENDASI.md`** — Arsitektur scoring engine, decision matrix, COGS proxy, margin guard, phased roadmap (886 baris)
- **`Model-KMeans.ipynb`** — Detail K-Means: transformasi, evaluasi, profiling segmen
- **`Rekomendasi_Strategi_Kafe.xlsx`** — Prototipe rekomendasi voucher (Excel)

---

> **Kesimpulan:** Dengan K-Means yang sudah selesai, kamu sudah bisa memulai Fase 1 (MVP) sekarang. **Namun, ketiadaan data cost (HPP) adalah kelemahan KRITIS** yang membuat semua perhitungan margin bersifat estimatif. Prioritaskan pengumpulan data cost aktual dari pemilik kafe sebelum sistem benar-benar diimplementasikan secara production. Sampaikan ke stakeholder: "Sistem ini saat ini hanya bisa mengoptimalkan **revenue**, bukan **profit** — data cost diperlukan agar kami bisa melindungi profit Anda."
