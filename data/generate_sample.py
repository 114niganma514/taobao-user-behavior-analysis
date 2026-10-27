"""
Generates SYNTHETIC data in exactly the same format as Tianchi UserBehavior.csv, so the whole
pipeline can be tested before the real data is available.

Real data format (no header, comma-separated):
    user_id, item_id, category_id, behavior_type, timestamp
    behavior_type in {pv, cart, fav, buy}; timestamp is Unix seconds (UTC);
    business window is 2017-11-25 00:00 to 2017-12-03 23:59 Beijing time (9 days).

Note: synthetic data is for debugging only; every conclusion must be re-run on the real data.
Usage: python data/generate_sample.py --users 20000 --out data/UserBehavior_sample.csv
"""
import argparse
import numpy as np
import pandas as pd

START_CN = pd.Timestamp("2017-11-25")       # midnight of day 1, Beijing time
N_DAYS = 9
UTC_OFFSET = 8 * 3600

# activity weight per Beijing hour 0-23: night trough, midday bump, 19:00-23:00 peak
HOUR_W = np.array([3, 1.6, 1, .7, .6, .8, 1.5, 3, 4.5, 5.5, 6, 6.2,
                   6, 6.3, 6.1, 6, 6, 5.8, 6.5, 8, 9.5, 10.5, 10, 6.5])
# daily weight 11-25 to 12-03: 12-02/03 is a weekend plus the Double 12 run-up
DAY_W = np.array([1, 1, .95, .95, .97, .98, 1, 1.25, 1.28])


def main(n_users: int, out: str, seed: int):
    rng = np.random.default_rng(seed)
    n_items, n_cats = n_users * 6, 600

    # item -> category; categories differ in purchase propensity (some are browsed more than bought)
    item_cat = rng.integers(0, n_cats, n_items)
    cat_buy_mult = rng.lognormal(0, 0.45, n_cats)
    item_pop = 1 / np.arange(1, n_items + 1) ** 0.9          # long-tail popularity
    item_pop /= item_pop.sum()

    # users differ in activity, retention and purchase propensity
    lam = rng.lognormal(2.2, 0.7, n_users)                  # mean views per active day
    p_stay = rng.beta(4, 2.2, n_users)                      # probability of being active the next day
    buy_prop = rng.lognormal(0, 0.6, n_users)
    first_day = rng.choice(N_DAYS, n_users, p=np.r_[.55, np.full(8, .45 / 8)])

    rows = []
    for u in range(n_users):
        active = np.zeros(N_DAYS, bool)
        active[first_day[u]] = True
        for d in range(first_day[u] + 1, N_DAYS):
            active[d] = rng.random() < p_stay[u] * DAY_W[d] / 1.1
        days = np.flatnonzero(active)
        n_pv = rng.poisson(lam[u] * DAY_W[days]) + 1
        rows.append(np.column_stack([np.full(n_pv.sum(), u), np.repeat(days, n_pv)]))
    pv = np.vstack(rows)
    n = len(pv)

    hour = rng.choice(24, n, p=HOUR_W / HOUR_W.sum())
    sec = pv[:, 1] * 86400 + hour * 3600 + rng.integers(0, 3600, n)
    items = rng.choice(n_items, n, p=item_pop)
    users = pv[:, 0]

    df_pv = pd.DataFrame({"u": users, "i": items, "b": "pv", "s": sec})

    # derive cart / fav / buy from pv (later than the matching pv)
    cmult = cat_buy_mult[item_cat[items]] * buy_prop[users]
    cart = rng.random(n) < 0.058 * np.sqrt(cmult)
    fav = rng.random(n) < 0.031
    buy_from_cart = cart & (rng.random(n) < np.clip(0.15 * cmult, 0, .9))
    buy_from_fav = fav & ~cart & (rng.random(n) < 0.08)
    buy_direct = ~cart & ~fav & (rng.random(n) < np.clip(0.0055 * cmult, 0, .5))
    # small time lag for follow-up events
    lag = lambda m: rng.exponential(1800, m.sum()).astype(int)

    parts = [df_pv]
    for mask, b in [(cart, "cart"), (fav, "fav")]:
        parts.append(pd.DataFrame({"u": users[mask], "i": items[mask], "b": b, "s": sec[mask] + lag(mask)}))
    buy_mask = buy_from_cart | buy_from_fav | buy_direct
    parts.append(pd.DataFrame({"u": users[buy_mask], "i": items[buy_mask], "b": "buy",
                               "s": sec[buy_mask] + lag(buy_mask) + 600}))
    df = pd.concat(parts, ignore_index=True)

    # dirty rows that also exist in the real data: out-of-window timestamps, exact duplicates
    bad = df.sample(frac=0.0005, random_state=seed).copy()
    bad["s"] = bad["s"] + rng.choice([-40, 30], len(bad)) * 86400
    dup = df.sample(frac=0.0003, random_state=seed + 1)
    df = pd.concat([df, bad, dup], ignore_index=True)

    start_utc = int(START_CN.timestamp()) - UTC_OFFSET
    out_df = pd.DataFrame({
        "user_id": df["u"] + 1_000_001,
        "item_id": df["i"] + 2_000_001,
        "category_id": item_cat[df["i"].to_numpy()] + 3_000_001,
        "behavior_type": df["b"],
        "timestamp": df["s"] + start_utc,
    }).sort_values(["user_id", "timestamp"])
    out_df.to_csv(out, header=False, index=False)          # same as the real file: no header
    print(f"wrote {len(out_df):,} rows, {n_users:,} users -> {out}")
    print(out_df["behavior_type"].value_counts(normalize=True).round(4).to_dict())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=20000)
    ap.add_argument("--out", default="data/UserBehavior_sample.csv")
    ap.add_argument("--seed", type=int, default=2017)
    a = ap.parse_args()
    main(a.users, a.out, a.seed)
