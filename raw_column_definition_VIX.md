---
source: https://raw.githubusercontent.com/wenchiehlee-money/VIX/refs/heads/main/raw_column_definition_VIX.md
destination: https://raw.githubusercontent.com/wenchiehlee-money/biztrends.TW/refs/heads/main/definitions/raw_column_definition_VIX.md
---

# VIX Raw Column Definitions

## raw_vix_merged.csv / global_vix_merged.csv (Global Volatility Index Data)
**No:** VIX-1
**Source:** Yahoo Finance `^VIX`, TAIFEX Taiwan VIX TXT files, optional local Japan VIX CSV
**Generator:** `collect_vix_data.py`
**Downstream Path:** `data/VIX/raw_vix_merged.csv`

### Columns

| Column | Type | Description | Source Field | Notes |
|--------|------|-------------|--------------|-------|
| `Date` | date | Trading date | Source date index | `YYYY-MM-DD` |
| `CNN_FG` | float | CNN Fear & Greed index value | Optional downstream/source enrichment | Nullable; retained for compatibility when available |
| `US_VIX` | float | CBOE US VIX close value | Yahoo Finance `^VIX` close | Nullable when US market is closed or fetch fails |
| `Taiwan_VIX` | float | Taiwan VIX value | TAIFEX / historical Taiwan VIX source | Nullable when Taiwan market is closed or source is unavailable |
| `Japan_VIX` | float | Japan Nikkei 225 volatility index close value | Optional local Japan VIX CSV close | Present only when local Japan VIX source is available |
| `download_timestamp` | datetime | Source data retrieval timestamp | System | CST `YYYY-MM-DD HH:MM:SS CST` |
| `process_timestamp` | datetime | CSV generation timestamp | System | CST `YYYY-MM-DD HH:MM:SS CST` |
