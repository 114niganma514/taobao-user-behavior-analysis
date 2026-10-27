"""
Reads output/tables/*.csv -> writes output/charts/*.png and output/report.md
Can be run on its own: python src/make_report.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---- Style: fixed colour order (blue = main series, orange = contrast / highlight) ----
plt.rcParams.update({
    "font.sans-serif": ["Segoe UI", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.unicode_minus": False, "figure.dpi": 150, "savefig.bbox": "tight",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#8a8984", "axes.labelcolor": "#52514e",
    "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": .6, "axes.axisbelow": True,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlecolor": "#0b0b0b",
})
BLUE, ORANGE, MUTED = "#2a78d6", "#eb6834", "#b9b8b2"
pct = lambda x, d=1: f"{x * 100:.{d}f}%"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def big(v, ref):
    """Axis label in millions/thousands when numbers are large."""
    if ref >= 1e6:
        return f"{v / 1e6:,.1f}M"
    if ref >= 1e4:
        return f"{v / 1e3:,.0f}K"
    return f"{v:,.0f}"


def _t(out, name):
    return pd.read_csv(out / "tables" / f"{name}.csv")


def _save(fig, out, name):
    fig.savefig(out / "charts" / name, facecolor=fig.get_facecolor())
    plt.close(fig)


def build(out: Path):
    T = {n: _t(out, n) for n in ["overview", "clean_log", "daily", "hourly", "bounce", "user_funnel",
                                 "path_table", "buy_source", "cohort_retention", "repurchase",
                                 "rfm_summary", "rfm_thresholds", "category_matrix", "item_concentration"]}
    ov = T["overview"].iloc[0]
    (out / "charts").mkdir(exist_ok=True)

    # 1 Daily trend: two stacked panels instead of a dual axis
    d = T["daily"]
    d["label"] = pd.to_datetime(d["dt"]).dt.strftime("%m-%d") + "\n" + d["weekday"].str[:3]
    fig, ax = plt.subplots(2, 1, figsize=(8, 5.2), sharex=True)
    ax[0].bar(d["label"], d["uv"], color=BLUE, width=.6)
    ax[0].set_title("Daily active users (UV)")
    ax[0].yaxis.set_major_formatter(lambda v, _: big(v, d.uv.max()))
    ax[1].plot(d["label"], d["pay_user_rate"], color=BLUE, lw=2, marker="o", ms=5)
    ax[1].yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    ax[1].set_title("Daily paying-user rate (buyers / UV)")
    _save(fig, out, "01_daily.png")

    # 2 Hourly: traffic peak vs. "traffic value" peak
    h = T["hourly"]
    fig, ax = plt.subplots(2, 1, figsize=(8, 5.2), sharex=True)
    ax[0].bar(h["hr"], h["pv"], color=BLUE, width=.7)
    ax[0].set_title("Page views by hour (Beijing time, 9-day total)")
    ax[0].yaxis.set_major_formatter(lambda v, _: big(v, h.pv.max()))
    ax[1].plot(h["hr"], h["buy_per_pv"], color=BLUE, lw=2, marker="o", ms=4)
    ax[1].yaxis.set_major_formatter(lambda v, _: pct(v, 1))
    ax[1].set_title("Purchases per page view by hour")
    ax[1].set_xticks(range(0, 24, 2))
    ax[1].set_xlabel("Hour of day")
    _save(fig, out, "02_hourly.png")

    # 3 User-level funnel
    uf = T["user_funnel"].iloc[0]
    steps = ["Viewed", "Carted or favourited", "Purchased"]
    vals = [uf.pv_users, uf.intent_users, uf.buy_users]
    fig, ax = plt.subplots(figsize=(7, 2.6))
    ax.barh(steps[::-1], vals[::-1], color=BLUE, height=.55)
    for i, v in enumerate(vals[::-1]):
        ax.text(v, i, f"  {int(v):,} ({pct(v / vals[0])})", va="center", color="#0b0b0b", fontsize=9)
    ax.set_xlim(0, vals[0] * 1.4)
    ax.xaxis.set_major_formatter(lambda v, _: big(v, vals[0]))
    ax.grid(axis="y", visible=False)
    ax.set_title("User-level conversion funnel")
    _save(fig, out, "03_user_funnel.png")

    # 4 Purchase rate of user-item pairs by intent path
    p = T["path_table"].copy()
    p["name"] = p["intent_path"].str.split("_", n=1).str[1]
    fig, ax = plt.subplots(figsize=(7, 3))
    colors = [MUTED, BLUE, ORANGE, BLUE]
    ax.bar(p["name"], p["buy_rate"], color=colors[:len(p)], width=.55)
    for i, r in p.iterrows():
        ax.text(i, r.buy_rate, pct(r.buy_rate), ha="center", va="bottom", fontsize=9, color="#0b0b0b")
    ax.yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    ax.grid(axis="x", visible=False)
    ax.set_title("Final purchase rate by intent path (user-item pairs)")
    _save(fig, out, "04_path_conversion.png")

    # 5 Retention heatmap (single-hue sequential scale)
    cr = T["cohort_retention"]
    piv = cr.pivot(index="cohort", columns="day_n", values="retention")
    fig, ax = plt.subplots(figsize=(8, 4))
    im = ax.imshow(piv.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    for (i, j), v in np.ndenumerate(piv.values):
        if not np.isnan(v):
            ax.text(j, i, f"{v * 100:.0f}", ha="center", va="center", fontsize=8,
                    color="white" if v > .55 else "#0b0b0b")
    dates = pd.date_range("2017-11-25", periods=9).strftime("%m-%d")
    ax.set_yticks(range(len(piv)), [f"{dates[c]} ({n:,} users)" for c, n in
                                    cr.groupby("cohort")["cohort_users"].first().items()])
    ax.set_xticks(range(piv.shape[1]), [f"D{c}" for c in piv.columns])
    ax.grid(False)
    ax.set_title("Day-N retention by first-seen-day cohort (%)\n"
                 "The jump on 12-02/03 is a sampling artefact of the dataset", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=.03, format=lambda v, _: pct(v, 0))
    _save(fig, out, "05_retention.png")

    # 6 RFM: share of users vs share of purchases
    order = ["Champions", "At-risk loyal", "Promising", "Hibernating"]
    r = T["rfm_summary"].set_index("segment").reindex([s for s in order if s in set(T["rfm_summary"].segment)])
    r = r.reset_index()
    x = np.arange(len(r))
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.bar(x - .2, r["user_share"], .38, color=BLUE, label="Share of buyers")
    ax.bar(x + .2, r["buy_share"], .38, color=ORANGE, label="Share of purchases")
    ax.set_xticks(x, r["segment"])
    ax.yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False)
    ax.set_title("RFM (R+F) segments: share of buyers vs share of purchases")
    _save(fig, out, "06_rfm.png")

    # 7 Category quadrant: traffic x conversion; bottom-right (high traffic, low conversion) = priority
    cm = T["category_matrix"]
    med_uv, med_cv = cm["pv_users"].median(), cm["user_conv"].median()
    opp = cm[(cm.pv_users >= med_uv) & (cm.user_conv < med_cv)].copy()
    opp["gap_buyers"] = (opp.pv_users * (med_cv - opp.user_conv)).round()
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    rest = cm.drop(opp.index)
    ax.scatter(rest.pv_users, rest.user_conv, s=12, color=BLUE, alpha=.45, label="Other categories", linewidths=0)
    ax.scatter(opp.pv_users, opp.user_conv, s=14, color=ORANGE, alpha=.85, label="High traffic, low conversion",
               linewidths=0)
    ax.axvline(med_uv, color="#8a8984", lw=1, ls="--")
    ax.axhline(med_cv, color="#8a8984", lw=1, ls="--")
    ax.set_xscale("log")
    ax.set_ylim(0, min(1, cm.user_conv.quantile(.995) * 1.1))
    ax.set_xlabel("Users who viewed the category (log scale)")
    ax.set_ylabel("View-to-purchase user conversion")
    ax.yaxis.set_major_formatter(lambda v, _: pct(v, 0))
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("Category traffic x conversion (dashed lines = medians)")
    _save(fig, out, "07_category_quadrant.png")
    opp.sort_values("gap_buyers", ascending=False).to_csv(
        out / "tables" / "category_opportunity.csv", index=False, encoding="utf-8")

    # ---------------- Report ----------------
    cl, b, rp, ic = T["clean_log"].iloc[0], T["bounce"].iloc[0], T["repurchase"].iloc[0], T["item_concentration"].iloc[0]
    rate = dict(zip(p["name"], p["buy_rate"]))
    pairs_browse = int(p.loc[p["name"] == "View only", "user_item_pairs"].iloc[0])
    total_bought = int(p["bought_pairs"].sum())
    gain_cart = 0.01 * pairs_browse * (rate["Cart only"] - rate["View only"])
    src = dict(zip(T["buy_source"]["path"], T["buy_source"]["share"]))
    peak_pv = int(h.loc[h.pv.idxmax(), "hr"])
    peak_val = int(h.loc[h.buy_per_pv.idxmax(), "hr"])
    c0 = cr[cr.cohort == 0]
    d1_c0 = c0.loc[c0.day_n == 1, "retention"].iloc[0]
    d26_c0 = c0.loc[c0.day_n.between(2, 6), "retention"].mean()
    rs = r.set_index("segment")
    top_day = d.loc[d.uv.idxmax()]
    wd = d[d.weekday.isin(WEEKDAYS)]
    we = d[~d.weekday.isin(WEEKDAYS)]
    if d.uv.iloc[-1] / ov.uv > .9:          # last two days are a sampling artefact: leave them out
        we = we[we.dt < d.dt.iloc[-2]]
    last_share = d.uv.iloc[-1] / ov.uv
    is_real = cl.raw_rows >= 5_000_000
    th = T["rfm_thresholds"].iloc[0]

    def seg(name, col):
        return rs.loc[name, col] if name in rs.index else 0

    champ_ratio = seg("Champions", "buy_share") / max(seg("Champions", "user_share"), 1e-9)
    worse_step = "intent -> purchase" if uf.intent_to_buy < uf.pv_to_intent else "view -> intent"
    traffic_note = (
        f"On the last day UV reaches {pct(last_share, 0)} of all users. This is mainly caused by **how the dataset "
        f"was sampled** (almost every sampled user is active on 12-02/03), on top of the weekend and the run-up to "
        f"Double 12. It must not be read as real traffic growth."
        if last_share > .9 else
        "12-02/03 is a weekend close to the Double 12 sale; mention this external factor instead of calling it a "
        "pure weekend effect.")

    md = f"""# Taobao User Behaviour Analysis

> Data: {"Tianchi UserBehavior, full dataset" if is_real else "WARNING: synthetic sample, for testing the pipeline only. Re-run on the real data before quoting any number."}
> Raw {int(cl.raw_rows):,} rows -> {int(cl.clean_rows):,} rows after cleaning ({int(cl.removed_rows):,} duplicate, out-of-window or invalid rows removed)

## 0. Executive summary

| Area | Key numbers | Interpretation |
|---|---|---|
| Scale | UV {int(ov.uv):,}; PV {int(ov.pv):,}; {ov.pv_per_user} PV per user | Context for everything below |
| Paying users | {pct(ov.pay_user_rate)} of users bought within 9 days | {pct(1 - ov.pay_user_rate)} of users made no purchase |
| Funnel | View -> cart/fav {pct(uf.pv_to_intent)}; intent -> purchase {pct(uf.intent_to_buy)} | Larger drop-off: {worse_step} |
| Intent path | Purchase rate: cart {pct(rate["Cart only"])}, fav {pct(rate["Fav only"])}, view only {pct(rate["View only"])} | Carting lifts purchase rate {rate["Cart only"] / rate["View only"]:.1f}x vs viewing only, yet {pct(src.get("Direct", 0), 0)} of purchases skip cart/fav entirely; only {pct(src.get("Cart", 0) + src.get("Cart+Fav", 0), 0)} go through the cart |
| Timing | Views peak at {peak_pv}:00; purchases per view peak at {peak_val}:00 | Best hours for reach and for conversion differ |
| Retention | 11-25 cohort: D1 {pct(d1_c0)}, D2-D6 average {pct(d26_c0)} | The jump on 12-02/03 is a sampling artefact (section 3) |
| Repurchase | {pct(rp.repurchase_rate)} of buyers bought on 2+ different days | |
| Segments | Champions are {pct(seg("Champions", "user_share"))} of buyers and make {pct(seg("Champions", "buy_share"))} of purchases | Purchase share is {champ_ratio:.1f}x their headcount share |
| Items | Top 1% of items take {pct(ic.top1pct_buy_share)} of purchases; only {int(ic.items_with_buy):,} of {int(ic.items_viewed):,} viewed items sold | Strong long tail |

## 1. Traffic
- Peak daily UV was {top_day["dt"]} ({top_day["weekday"]}) at {int(top_day.uv):,}; weekday average {wd.uv.mean():,.0f}. {traffic_note}
- Paying-user rate averages {pct(wd.pay_user_rate.mean())} on weekdays vs {pct(we.pay_user_rate.mean())} on {len(we)} unaffected weekend day(s){" (12-02/03 excluded as a sampling artefact)" if d.uv.iloc[-1] / ov.uv > .9 else ""}. With so few weekend days this is a hint, not a finding: weekend visitors may browse more and buy less.
- Strict bounce rate (a single page view only) {pct(b.strict_bounce_rate, 2)}; "browse only" users (never cart, fav or buy) {pct(b.pv_only_rate)}.

![daily](charts/01_daily.png)
![hourly](charts/02_hourly.png)

## 2. Conversion
![funnel](charts/03_user_funnel.png)
![path](charts/04_path_conversion.png)

**Recommendation 1: push add-to-cart.** There are {pairs_browse:,} "view only" user-item pairs. If a better add-to-cart button or a cart coupon moved 1% of them into the cart,
the purchase-rate gap ({pct(rate["Cart only"])} - {pct(rate["View only"])}) implies about **{gain_cart:,.0f} extra purchases (+{pct(gain_cart / total_bought)})**.
This is an upper-bound estimate from observational data; the real effect has to be confirmed with an A/B test.

## 3. Retention and repurchase
![retention](charts/05_retention.png)
- **How to read this chart (raise it in interviews):** every cohort jumps above 95% in the 12-02/03 columns. This is fake retention created by how the dataset was sampled (almost all sampled users are active on the last two days), not users actually returning. Only the part before 12-02 is meaningful: the 11-25 cohort keeps {pct(d1_c0)} on D1 and about {pct(d26_c0, 0)} on D2-D6.
- Second limitation: the window is only 9 days, so "first seen day" is not a real sign-up date and early cohorts contain many existing users.

## 4. User segments (RFM with R+F only; the data has no order value)
![rfm](charts/06_rfm.png)

| Segment | Buyers | Share of buyers | Share of purchases | Avg R (days) | Avg F (purchases) | Action |
|---|---|---|---|---|---|---|
""" + "\n".join(
        f"| {s} | {int(rs.loc[s, 'users']):,} | {pct(rs.loc[s, 'user_share'])} | {pct(rs.loc[s, 'buy_share'])} | "
        f"{rs.loc[s, 'avg_recency']} | {rs.loc[s, 'avg_frequency']} | {act} |"
        for s, act in [("Champions", "Member perks, early access to new items; prevent churn"),
                       ("At-risk loyal", "Bought often but not recently -> win-back coupons"),
                       ("Promising", "Bought recently but rarely -> cross-sell to build repeat purchases"),
                       ("Hibernating", "Low-cost reach only; cap marketing spend")] if s in rs.index) + f"""

Thresholds: mean R = {th.avg_recency} days, mean F = {th.avg_frequency} purchases.

## 5. Categories
![category](charts/07_category_quadrant.png)

**Recommendation 2: fix high-traffic, low-conversion categories first.** {len(opp)} categories have more viewers than the median ({med_uv:,.0f}) but a conversion rate below the median ({pct(med_cv)}).
Lifting them to the median conversion would add about **{opp.gap_buyers.sum():,.0f} user-category purchases** (details in `tables/category_opportunity.csv`).
Things to check: price band, product-page quality, reviews, stock.

## 6. Limitations and next steps
1. No order value or item attributes -> RFM has no M; GMV and average order value cannot be computed
2. 9-day window right before Double 12 -> strong seasonality; do not generalise the findings
3. The recommendations rest on correlations; causality needs A/B testing
4. Next: user-item features + logistic regression / LightGBM to predict purchase after add-to-cart, for targeted reminders
"""
    (out / "report.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1] / "output")
