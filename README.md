# Taobao User Behaviour Analysis (Tianchi UserBehavior, 100M rows)

SQL analysis of about 100 million Taobao app behaviour events. It builds a metric system covering **traffic -> funnel -> retention -> user segments -> categories**, locates where conversion is lost, and turns the findings into quantified recommendations.

## 1. Business questions

| # | Question | Method | SQL |
|---|---|---|---|
| Q1 | When do users come, and how many leave without acting? | PV/UV, daily and hourly trends, bounce rate | `02_traffic.sql` |
| Q2 | Where is traffic lost? Is add-to-cart or favourite the better purchase signal? | User-level funnel + user-item-pair path conversion | `03_funnel.sql` |
| Q3 | Do users come back, and do buyers buy again? | Cohort retention matrix, repurchase rate | `04_retention.sql` |
| Q4 | Which users matter most, and how should each group be handled? | RFM (R+F; the data has no order value) | `05_rfm.sql` |
| Q5 | Which categories should be fixed first? | Traffic x conversion quadrant + sized opportunity | `06_category.sql` |

## 2. Data

- Source: Alibaba Tianchi [User Behavior Data from Taobao for Recommendation](https://tianchi.aliyun.com/dataset/649) (Tianchi login required; `UserBehavior.csv.zip`, about 3.4 GB unzipped)
- Scope: 2017-11-25 to 2017-12-03 (Beijing time), about 1 million users, 100,150,807 events
- Columns (no header): `user_id, item_id, category_id, behavior_type (pv/cart/fav/buy), timestamp (Unix seconds)`
- Cleaning: drop exact duplicates, drop timestamps outside the 9-day window, keep only the 4 valid behaviour types, convert to Beijing time

Put the download in `data/` (or next to the project folder). `data/generate_sample.py` creates synthetic data in the same format for testing the code.

## 3. How to run

**Windows:** double-click `run_windows.bat`. It finds Anaconda/Python, installs DuckDB if missing, unzips the data if needed and runs everything. Log: `output/run_log_main.txt`.

**Command line:**
```bash
pip install duckdb pandas matplotlib

# Full real data (DuckDB processes 100M rows on a single laptop in about 3 minutes)
python src/run_analysis.py --engine duckdb

# Synthetic data / no DuckDB
python data/generate_sample.py
python src/run_analysis.py --csv data/UserBehavior_sample.csv --engine sqlite
```

Outputs: `output/tables/*.csv` (one file per query), `output/charts/*.png`, `output/report.md` (report filled in automatically from the results).

### Porting to Hive / Spark SQL / MySQL
`02` to `06` use standard SQL only (CTEs, CASE WHEN, window functions) and port as-is. Only `01_clean` needs engine-specific time functions, e.g. Hive:
`from_unixtime(ts, 'yyyy-MM-dd')`, `hour(from_unixtime(ts))` (the cluster time zone must be Asia/Shanghai).

## 4. Project structure

```
data/generate_sample.py     synthetic data generator (same format as the real data)
sql/01_clean_duckdb.sql     load + clean (DuckDB)
sql/01_clean_sqlite.sql     clean (SQLite fallback)
sql/02_traffic.sql ... 06_category.sql   five analysis modules
src/run_analysis.py         runs all SQL and exports the results
src/make_report.py          charts + report
run_windows.bat             one-click runner for Windows
output/                     result tables, charts, report
```

## 5. Metric definitions

- **Paying-user rate** = users with a purchase / UV (9-day total)
- **User-level funnel**: view -> cart or fav -> purchase, de-duplicated by user so repeat clicks do not inflate the denominator
- **Path conversion**: unit is the user-item pair; compares the final purchase rate of "view only / fav only / cart only / cart+fav"
- **Bounce rate**: strict = users with exactly one pv; broad = users with only pv events
- **Retention**: cohorts by first day seen inside the window (not true sign-up date, see limitations)
- **Repurchase rate** = buyers who bought on 2+ different days / buyers
- **RFM**: R = days from last purchase to 2017-12-04, F = number of purchases, 2x2 split at the means
- **Category conversion** = users who viewed and bought in the category / users who viewed it; categories with >= 50 viewers only

## 6. Key findings (full dataset)

See `output/report.md` for the complete numbers. Highlights:

1. Adding an item to the cart raises its purchase rate about 7x compared with only viewing it, yet about three quarters of purchases skip the cart entirely. The cart is a strong signal but not the main purchase route.
2. Views peak at 21:00 while purchases per view peak at 10:00, so the best hours for reach and for conversion are different.
3. Champions (recent and frequent buyers) are about 31% of buyers but make about 56% of purchases.
4. The top 1% of items take about 46% of purchases; most viewed items never sell.
5. The apparent retention jump on 12-02/03 is a sampling artefact of the dataset, not real user return.

## 7. Limitations
- No order value -> RFM has no M; GMV and average order value cannot be computed
- Only 9 days right before Double 12 -> strong seasonality; cohorts are not true new users
- Quantified recommendations rest on correlations; causality needs A/B testing
