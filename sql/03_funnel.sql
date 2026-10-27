-- =====================================================================
-- 03 Conversion funnel
-- Business question: where is traffic lost? Is add-to-cart or favourite the better purchase signal?
-- Event-count funnels are inflated by repeat clicks, so user-level and user-item-pair views are used too
-- =====================================================================

-- @name event_funnel
SELECT behavior_type, COUNT(*) AS events, COUNT(DISTINCT user_id) AS users
FROM ub
GROUP BY behavior_type
ORDER BY CASE behavior_type WHEN 'pv' THEN 1 WHEN 'fav' THEN 2 WHEN 'cart' THEN 3 ELSE 4 END;

-- @name user_funnel
-- User-level funnel: view -> purchase intent (cart or fav) -> purchase
WITH u AS (
    SELECT user_id,
           MAX(CASE WHEN behavior_type = 'pv' THEN 1 ELSE 0 END)                  AS has_pv,
           MAX(CASE WHEN behavior_type IN ('cart', 'fav') THEN 1 ELSE 0 END)     AS has_intent,
           MAX(CASE WHEN behavior_type = 'buy' THEN 1 ELSE 0 END)                 AS has_buy
    FROM ub GROUP BY user_id
)
SELECT SUM(has_pv)                                        AS pv_users,
       SUM(has_pv * has_intent)                           AS intent_users,
       SUM(has_pv * has_intent * has_buy)                 AS intent_buy_users,
       SUM(has_buy)                                       AS buy_users,
       ROUND(SUM(has_pv * has_intent) * 1.0 / SUM(has_pv), 4)                 AS pv_to_intent,
       ROUND(SUM(has_pv * has_intent * has_buy) * 1.0 / SUM(has_pv * has_intent), 4) AS intent_to_buy,
       ROUND(SUM(has_buy) * 1.0 / SUM(has_pv), 4)                             AS pv_to_buy
FROM u;

-- @name build_ui
-- User-item pairs: each pair is one complete decision of one user about one item
DROP TABLE IF EXISTS ui;
CREATE TABLE ui AS
SELECT user_id, item_id, category_id,
       MAX(CASE WHEN behavior_type = 'pv'   THEN 1 ELSE 0 END) AS has_pv,
       MAX(CASE WHEN behavior_type = 'cart' THEN 1 ELSE 0 END) AS has_cart,
       MAX(CASE WHEN behavior_type = 'fav'  THEN 1 ELSE 0 END) AS has_fav,
       MAX(CASE WHEN behavior_type = 'buy'  THEN 1 ELSE 0 END) AS has_buy
FROM ub
GROUP BY user_id, item_id, category_id;

-- @name path_table
-- Final purchase rate of viewed pairs, grouped by whether the item was carted / favourited
SELECT CASE WHEN has_cart = 1 AND has_fav = 1 THEN '3_Cart+Fav'
            WHEN has_cart = 1 THEN '2_Cart only'
            WHEN has_fav = 1  THEN '1_Fav only'
            ELSE '0_View only' END                       AS intent_path,
       COUNT(*)                                          AS user_item_pairs,
       SUM(has_buy)                                      AS bought_pairs,
       ROUND(SUM(has_buy) * 1.0 / COUNT(*), 4)           AS buy_rate
FROM ui
WHERE has_pv = 1
GROUP BY 1
ORDER BY 1;

-- @name buy_source
-- Which path every purchased pair came through (mix of purchase sources)
SELECT CASE WHEN has_cart = 1 AND has_fav = 1 THEN 'Cart+Fav'
            WHEN has_cart = 1 THEN 'Cart'
            WHEN has_fav = 1  THEN 'Fav'
            ELSE 'Direct' END AS path,
       COUNT(*) AS bought_pairs,
       ROUND(COUNT(*) * 1.0 / (SELECT COUNT(*) FROM ui WHERE has_buy = 1), 4) AS share
FROM ui
WHERE has_buy = 1
GROUP BY 1
ORDER BY bought_pairs DESC;
