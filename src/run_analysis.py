"""
One-click pipeline: load & clean -> run sql/02-06 -> save result tables to output/tables/ -> build charts and report.

Usage:
    # Full real dataset (DuckDB recommended; 100M rows run fine on a 16GB laptop)
    python src/run_analysis.py --csv data/UserBehavior.csv --engine duckdb
    # Synthetic sample / no DuckDB installed
    python src/run_analysis.py --csv data/UserBehavior_sample.csv --engine sqlite

SQL files are split into blocks with "-- @name xxx"; if the last statement of a block is a query,
its result is saved as output/tables/xxx.csv
"""
import argparse
import re
import shutil
import time
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR, OUT = ROOT / "sql", ROOT / "output"
COLS = ["user_id", "item_id", "category_id", "behavior_type", "ts"]


def parse_blocks(path: Path, **fmt):
    text = path.read_text(encoding="utf-8")
    for k, v in fmt.items():
        text = text.replace("{" + k + "}", v)
    for part in re.split(r"^-- @name\s+", text, flags=re.M)[1:]:
        name, body = part.split("\n", 1)
        body = "\n".join(l for l in body.splitlines() if not l.strip().startswith("--"))
        stmts = [s.strip() for s in body.split(";") if s.strip()]
        yield name.strip(), stmts


class Engine:
    def __init__(self, kind: str, db: str):
        self.kind = kind
        if kind == "duckdb":
            import duckdb
            self.con = duckdb.connect(db)
            self.con.execute(f"SET temp_directory='{Path(db).parent.as_posix()}/duckdb_tmp'")
            self.con.execute("SET preserve_insertion_order=false")
        else:
            import sqlite3
            self.con = sqlite3.connect(db)
            self.con.execute("PRAGMA journal_mode=OFF")
            self.con.execute("PRAGMA synchronous=OFF")

    def run(self, sql: str, fetch: bool):
        if self.kind == "duckdb":
            r = self.con.execute(sql)
            return r.df() if fetch else None
        if fetch:
            return pd.read_sql_query(sql, self.con)
        self.con.execute(sql)
        self.con.commit()


def load_sqlite_raw(eng: Engine, csv: str):
    eng.con.execute("DROP TABLE IF EXISTS raw")
    for chunk in pd.read_csv(csv, header=None, names=COLS, chunksize=2_000_000):
        chunk.to_sql("raw", eng.con, if_exists="append", index=False)


def run_file(eng: Engine, path: Path, **fmt):
    for name, stmts in parse_blocks(path, **fmt):
        t = time.time()
        res = None
        for s in stmts:
            is_query = s.lstrip().upper().startswith(("SELECT", "WITH"))
            res = eng.run(s, fetch=is_query)
        if res is not None:
            (OUT / "tables").mkdir(parents=True, exist_ok=True)
            res.to_csv(OUT / "tables" / f"{name}.csv", index=False, encoding="utf-8")
        print(f"  {path.name:<22} {name:<20} {time.time() - t:6.1f}s")


def find_csv(arg):
    """Accepts a .csv or .zip. If none is given, looks for UserBehavior.csv / UserBehavior*.zip
    in data/ (and one level above the project, e.g. Downloads) and unzips if needed."""
    p = Path(arg) if arg else None
    if p is None:
        cands = ([ROOT / "data" / "UserBehavior.csv"] + sorted((ROOT / "data").glob("UserBehavior*.zip"))
                 + sorted(ROOT.parent.glob("UserBehavior*.zip")))
        p = next((c for c in cands if c.exists()), None)
        if p is None:
            raise SystemExit("[ERROR] No UserBehavior.csv or UserBehavior*.zip found in data/. "
                             "Put the downloaded dataset there first. "
                             "(To test the code only: --csv data/UserBehavior_sample.csv --engine sqlite)")
    if p.suffix.lower() == ".zip":
        target = ROOT / "data" / "UserBehavior.csv"
        if not target.exists():
            print(f"Unzipping {p.name} ...")
            with zipfile.ZipFile(p) as z:
                name = next(n for n in z.namelist() if n.endswith(".csv"))
                with z.open(name) as src, open(target, "wb") as dst:
                    while chunk := src.read(64 << 20):
                        dst.write(chunk)
        p = target
    if not p.exists():
        raise SystemExit(f"[ERROR] Data file not found: {p}")
    return str(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None, help="Default: auto-detect UserBehavior.csv / .zip in data/")
    ap.add_argument("--engine", choices=["duckdb", "sqlite"], default="duckdb")
    ap.add_argument("--db", default=None, help="Database file path, default output/ub.<engine>")
    a = ap.parse_args()

    a.csv = find_csv(a.csv)
    print(f"Data file: {a.csv}")
    for sub in ("tables", "charts"):
        shutil.rmtree(OUT / sub, ignore_errors=True)
        (OUT / sub).mkdir(parents=True, exist_ok=True)
    db = a.db or str(OUT / f"ub.{a.engine}")
    Path(db).unlink(missing_ok=True)
    eng = Engine(a.engine, db)

    t0 = time.time()
    print(f"[1/3] Load & clean ({a.engine})")
    if a.engine == "sqlite":
        load_sqlite_raw(eng, a.csv)
        run_file(eng, SQL_DIR / "01_clean_sqlite.sql")
    else:
        run_file(eng, SQL_DIR / "01_clean_duckdb.sql", csv=Path(a.csv).resolve().as_posix())

    print("[2/3] Analysis SQL")
    for f in ["02_traffic.sql", "03_funnel.sql", "04_retention.sql", "05_rfm.sql", "06_category.sql"]:
        run_file(eng, SQL_DIR / f)

    print("[3/3] Charts & report")
    from make_report import build
    build(OUT)
    print(f"Done in {time.time() - t0:.0f}s -> {OUT}")


if __name__ == "__main__":
    main()
