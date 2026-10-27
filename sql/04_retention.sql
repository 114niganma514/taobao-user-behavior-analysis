-- =====================================================================
-- 04 Retention and repurchase
-- Business question: do new users come back on day N? Do buyers buy again?
-- Note: the data covers only 9 days, so "first seen day" is not a true sign-up date.
--       These are "first-seen-day cohorts"; state this limitation in the report.
-- =====================================================================

-- @name cohort_retention
WITH act AS (
    SELECT DISTINCT user_id, day_idx FROM ub
),
first_day AS (
    SELECT user_id, MIN(day_idx) AS cohort FROM act GROUP BY user_id
),
size AS (
    SELECT cohort, COUNT(*) AS cohort_users FROM first_day GROUP BY cohort
)
SELECT f.cohort,
       s.cohort_users,
       a.day_idx - f.cohort                                   AS day_n,
       COUNT(*)                                               AS retained_users,
       ROUND(COUNT(*) * 1.0 / s.cohort_users, 4)              AS retention
FROM act a
JOIN first_day f ON a.user_id = f.user_id
JOIN size s      ON f.cohort = s.cohort
GROUP BY f.cohort, s.cohort_users, a.day_idx - f.cohort
ORDER BY f.cohort, day_n;

-- @name repurchase
-- Repurchase = bought on 2 or more different days (several orders on one day count once)
WITH b AS (
    SELECT user_id, COUNT(DISTINCT day_idx) AS buy_days, COUNT(*) AS buy_events
    FROM ub WHERE behavior_type = 'buy' GROUP BY user_id
)
SELECT COUNT(*)                                                     AS buyers,
       SUM(CASE WHEN buy_days >= 2 THEN 1 ELSE 0 END)               AS repeat_buyers,
       ROUND(SUM(CASE WHEN buy_days >= 2 THEN 1 ELSE 0 END) * 1.0 / COUNT(*), 4) AS repurchase_rate,
       ROUND(AVG(buy_events * 1.0), 2)                              AS avg_buys_per_buyer
FROM b;

-- @name buy_freq_dist
WITH b AS (
    SELECT user_id, COUNT(*) AS buy_events FROM ub WHERE behavior_type = 'buy' GROUP BY user_id
)
SELECT CASE WHEN buy_events >= 10 THEN 10 ELSE buy_events END AS buy_events_capped,
       COUNT(*) AS users
FROM b GROUP BY 1 ORDER BY 1;
