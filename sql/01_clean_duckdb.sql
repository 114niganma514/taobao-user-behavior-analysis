-- =====================================================================
-- 01 Load and clean (DuckDB version, recommended: handles 100M rows / 3.4GB on a laptop)
-- {csv} is replaced with the real file path by src/run_analysis.py
-- Time conversion: 1511539200 = Unix seconds of 2017-11-25 00:00:00 Beijing time (UTC+8)
-- =====================================================================

-- @name load_raw
-- A view, so the 3.4GB source file is not copied into the database a second time
CREATE OR REPLACE VIEW raw AS
SELECT * FROM read_csv('{csv}', header = false, delim = ',',
    columns = {'user_id': 'BIGINT', 'item_id': 'BIGINT', 'category_id': 'BIGINT',
               'behavior_type': 'VARCHAR', 'ts': 'BIGINT'});

-- @name build_clean
-- Cleaning rules: (1) drop exact duplicate rows (2) keep only 11-25 to 12-03 Beijing time (9 days)
--                 (3) keep only the 4 valid behaviour types (4) derive day_idx / hr / dt / weekday
CREATE OR REPLACE TABLE ub AS
WITH d AS (
    SELECT DISTINCT user_id, item_id, category_id, behavior_type, ts FROM raw
    WHERE behavior_type IN ('pv', 'cart', 'fav', 'buy')
      AND ts >= 1511539200 AND ts < 1511539200 + 9 * 86400
)
SELECT user_id, item_id, category_id, behavior_type, ts,
       CAST((ts - 1511539200) // 86400 AS INTEGER)          AS day_idx,  -- 0..8
       CAST(((ts - 1511539200) % 86400) // 3600 AS INTEGER) AS hr,       -- 0..23 Beijing time
       DATE '2017-11-25' + CAST((ts - 1511539200) // 86400 AS INTEGER) AS dt,
       dayname(DATE '2017-11-25' + CAST((ts - 1511539200) // 86400 AS INTEGER)) AS weekday
FROM d;

-- @name clean_log
SELECT (SELECT COUNT(*) FROM raw) AS raw_rows,
       (SELECT COUNT(*) FROM ub)  AS clean_rows,
       (SELECT COUNT(*) FROM raw) - (SELECT COUNT(*) FROM ub) AS removed_rows;
