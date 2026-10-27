-- =====================================================================
-- 01 Clean (SQLite fallback; table raw is bulk-loaded in chunks by Python)
-- Fine for the sample or a few million rows; use the DuckDB version for the full 100M rows
-- =====================================================================

-- @name build_clean
DROP TABLE IF EXISTS ub;
CREATE TABLE ub AS
WITH d AS (
    SELECT DISTINCT user_id, item_id, category_id, behavior_type, ts FROM raw
    WHERE behavior_type IN ('pv', 'cart', 'fav', 'buy')
      AND ts >= 1511539200 AND ts < 1511539200 + 9 * 86400
)
SELECT user_id, item_id, category_id, behavior_type, ts,
       (ts - 1511539200) / 86400          AS day_idx,   -- integer division in SQLite
       ((ts - 1511539200) % 86400) / 3600 AS hr,
       date('2017-11-25', '+' || ((ts - 1511539200) / 86400) || ' days') AS dt,
       CASE strftime('%w', date('2017-11-25', '+' || ((ts - 1511539200) / 86400) || ' days'))
            WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday'
            WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday'
            ELSE 'Saturday' END AS weekday
FROM d;
CREATE INDEX idx_ub_user ON ub(user_id);
CREATE INDEX idx_ub_ui ON ub(user_id, item_id);

-- @name clean_log
SELECT (SELECT COUNT(*) FROM raw) AS raw_rows,
       (SELECT COUNT(*) FROM ub)  AS clean_rows,
       (SELECT COUNT(*) FROM raw) - (SELECT COUNT(*) FROM ub) AS removed_rows;
