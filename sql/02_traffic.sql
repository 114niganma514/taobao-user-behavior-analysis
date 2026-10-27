-- =====================================================================
-- 02 Traffic: overall scale, daily trend, 24-hour profile, bounce
-- Business question: when do users come, and how many leave without doing anything?
-- Standard SQL only, so it ports directly to MySQL 8 / Hive / Spark SQL
-- =====================================================================

-- @name overview
SELECT COUNT(*)                                                  AS total_events,
       COUNT(DISTINCT user_id)                                   AS uv,
       COUNT(DISTINCT item_id)                                   AS items,
       COUNT(DISTINCT category_id)                               AS categories,
       SUM(CASE WHEN behavior_type = 'pv'   THEN 1 ELSE 0 END)   AS pv,
       SUM(CASE WHEN behavior_type = 'cart' THEN 1 ELSE 0 END)   AS cart,
       SUM(CASE WHEN behavior_type = 'fav'  THEN 1 ELSE 0 END)   AS fav,
       SUM(CASE WHEN behavior_type = 'buy'  THEN 1 ELSE 0 END)   AS buy,
       COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) AS buyers,
       ROUND(SUM(CASE WHEN behavior_type = 'pv' THEN 1 ELSE 0 END) * 1.0
             / COUNT(DISTINCT user_id), 1)                       AS pv_per_user,
       ROUND(COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) * 1.0
             / COUNT(DISTINCT user_id), 4)                       AS pay_user_rate
FROM ub;

-- @name daily
SELECT dt, weekday,
       SUM(CASE WHEN behavior_type = 'pv'  THEN 1 ELSE 0 END) AS pv,
       COUNT(DISTINCT user_id)                                AS uv,
       SUM(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0 END) AS buy,
       COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) AS buyers,
       ROUND(SUM(CASE WHEN behavior_type = 'pv' THEN 1 ELSE 0 END) * 1.0 / COUNT(DISTINCT user_id), 2) AS pv_per_uv,
       ROUND(COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) * 1.0 / COUNT(DISTINCT user_id), 4) AS pay_user_rate
FROM ub
GROUP BY dt, weekday
ORDER BY dt;

-- @name hourly
-- 9-day totals by hour; buy_per_pv measures how valuable the traffic in that hour is
SELECT hr,
       SUM(CASE WHEN behavior_type = 'pv'   THEN 1 ELSE 0 END) AS pv,
       SUM(CASE WHEN behavior_type = 'cart' THEN 1 ELSE 0 END) AS cart,
       SUM(CASE WHEN behavior_type = 'fav'  THEN 1 ELSE 0 END) AS fav,
       SUM(CASE WHEN behavior_type = 'buy'  THEN 1 ELSE 0 END) AS buy,
       COUNT(DISTINCT user_id)                                 AS uv,
       ROUND(SUM(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0 END) * 1.0
             / SUM(CASE WHEN behavior_type = 'pv' THEN 1 ELSE 0 END), 4) AS buy_per_pv
FROM ub
GROUP BY hr
ORDER BY hr;

-- @name bounce
-- Two definitions:
--   strict bounce: exactly 1 event in 9 days and it is a pv
--   browse only:   only pv events in 9 days, never cart / fav / buy
WITH u AS (
    SELECT user_id,
           COUNT(*) AS n_all,
           SUM(CASE WHEN behavior_type = 'pv' THEN 1 ELSE 0 END) AS n_pv
    FROM ub GROUP BY user_id
)
SELECT COUNT(*) AS uv,
       SUM(CASE WHEN n_all = 1 AND n_pv = 1 THEN 1 ELSE 0 END) AS strict_bounce_users,
       ROUND(SUM(CASE WHEN n_all = 1 AND n_pv = 1 THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS strict_bounce_rate,
       SUM(CASE WHEN n_all = n_pv THEN 1 ELSE 0 END) AS pv_only_users,
       ROUND(SUM(CASE WHEN n_all = n_pv THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS pv_only_rate
FROM u;
