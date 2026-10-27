-- =====================================================================
-- 06 Categories and items
-- Business question: which categories have high traffic but poor conversion (fix first)?
--                    Are purchases concentrated in a few top items?
-- Category conversion = users who viewed AND bought in the category / users who viewed it
-- =====================================================================

-- @name category_matrix
-- Many purchases in this dataset have no matching view record, so "buyers / viewers" can exceed 100%.
-- Aggregate to user-category first, then conversion = viewed-and-bought users / viewed users (always <= 100%).
-- Only categories with >= 50 viewers are kept, to avoid noise from tiny samples.
WITH uc AS (
    SELECT category_id, user_id,
           SUM(CASE WHEN behavior_type = 'pv'   THEN 1 ELSE 0 END) AS pv,
           SUM(CASE WHEN behavior_type = 'cart' THEN 1 ELSE 0 END) AS cart,
           SUM(CASE WHEN behavior_type = 'buy'  THEN 1 ELSE 0 END) AS buy
    FROM ub GROUP BY category_id, user_id
)
SELECT category_id,
       SUM(CASE WHEN pv > 0 THEN 1 ELSE 0 END)              AS pv_users,
       SUM(CASE WHEN buy > 0 THEN 1 ELSE 0 END)             AS buy_users,
       SUM(CASE WHEN pv > 0 AND buy > 0 THEN 1 ELSE 0 END)  AS pv_buy_users,
       SUM(pv) AS pv, SUM(cart) AS cart, SUM(buy) AS buy,
       ROUND(SUM(CASE WHEN pv > 0 AND buy > 0 THEN 1 ELSE 0 END) * 1.0
             / SUM(CASE WHEN pv > 0 THEN 1 ELSE 0 END), 4) AS user_conv
FROM uc
GROUP BY category_id
HAVING SUM(CASE WHEN pv > 0 THEN 1 ELSE 0 END) >= 50
ORDER BY pv_users DESC;

-- @name item_concentration
-- Purchase concentration: share of purchases made by the top 1% / top 10% of items
WITH it AS (
    SELECT item_id, SUM(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0 END) AS buys
    FROM ub GROUP BY item_id
),
r AS (
    SELECT item_id, buys,
           ROW_NUMBER() OVER (ORDER BY buys DESC) AS rk,
           COUNT(*) OVER ()                        AS n_items
    FROM it
)
SELECT MAX(n_items)                                                        AS items_viewed,
       SUM(CASE WHEN buys > 0 THEN 1 ELSE 0 END)                           AS items_with_buy,
       ROUND(SUM(CASE WHEN rk <= n_items * 0.01 THEN buys ELSE 0 END) * 1.0 / SUM(buys), 4) AS top1pct_buy_share,
       ROUND(SUM(CASE WHEN rk <= n_items * 0.10 THEN buys ELSE 0 END) * 1.0 / SUM(buys), 4) AS top10pct_buy_share
FROM r;
