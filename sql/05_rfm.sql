-- =====================================================================
-- 05 RFM segmentation (R + F)
-- The dataset has no order value, so M is missing; a 2x2 split on R (days since last purchase)
-- and F (number of purchases) is used instead.
-- Reference date = 2017-12-04 (the day after the window, day_idx = 9)
-- Thresholds are the means: R <= mean R is "recent", F >= mean F is "frequent".
-- Medians or NTILE scores also work; explain the choice in the report.
-- =====================================================================

-- @name build_rfm
DROP TABLE IF EXISTS rfm;
CREATE TABLE rfm AS
WITH b AS (
    SELECT user_id,
           9 - MAX(day_idx) AS recency,      -- 1 = bought on the last day
           COUNT(*)         AS frequency
    FROM ub WHERE behavior_type = 'buy'
    GROUP BY user_id
),
avg_v AS (
    SELECT AVG(recency * 1.0) AS avg_r, AVG(frequency * 1.0) AS avg_f FROM b
)
SELECT b.user_id, b.recency, b.frequency,
       CASE WHEN b.recency <= a.avg_r AND b.frequency >= a.avg_f THEN 'Champions'
            WHEN b.recency >  a.avg_r AND b.frequency >= a.avg_f THEN 'At-risk loyal'
            WHEN b.recency <= a.avg_r AND b.frequency <  a.avg_f THEN 'Promising'
            ELSE 'Hibernating' END AS segment
FROM b CROSS JOIN avg_v a;

-- @name rfm_thresholds
SELECT ROUND(AVG(recency * 1.0), 2) AS avg_recency, ROUND(AVG(frequency * 1.0), 2) AS avg_frequency
FROM rfm;

-- @name rfm_summary
SELECT segment,
       COUNT(*)                                                  AS users,
       ROUND(COUNT(*) * 1.0 / (SELECT COUNT(*) FROM rfm), 4)     AS user_share,
       SUM(frequency)                                            AS buys,
       ROUND(SUM(frequency) * 1.0 / (SELECT SUM(frequency) FROM rfm), 4) AS buy_share,
       ROUND(AVG(recency * 1.0), 2)                              AS avg_recency,
       ROUND(AVG(frequency * 1.0), 2)                            AS avg_frequency
FROM rfm
GROUP BY segment
ORDER BY buys DESC;
