"""Fetch Overture Maps places for Casablanca (health-related only) into a local GeoJSON-ish JSON.

Reads only the parquet row groups whose bbox statistics overlap the Casablanca
bounding box, using HTTP range requests, so the full ~13 GB theme is never downloaded.
"""
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import fsspec
import pyarrow.parquet as pq
import requests

RELEASE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-21.0"
BUCKET = "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com"
# Greater Casablanca (prefecture + Ain Harrouda/Mohammedia edge excluded)
XMIN, YMIN, XMAX, YMAX = -7.75, 33.45, -7.40, 33.66
OUT = sys.argv[2] if len(sys.argv) > 2 else "places_casablanca.json"

listing = requests.get(
    f"{BUCKET}/?list-type=2&prefix=release/{RELEASE}/theme=places/type=place/", timeout=60
).text
keys = re.findall(r"<Key>([^<]+\.parquet)</Key>", listing)
print(f"{len(keys)} parquet files", flush=True)

fs = fsspec.filesystem("http", block_size=4 * 1024 * 1024)
COLS = ["id", "names", "taxonomy", "basic_category", "operating_status", "confidence", "bbox", "addresses"]


def col_index(schema, path):
    for i in range(len(schema)):
        if schema.column(i).path == path:
            return i
    raise KeyError(path)


def process(key):
    url = f"{BUCKET}/{key}"
    rows = []
    with fs.open(url, "rb") as f:
        pf = pq.ParquetFile(f)
        md = pf.metadata
        s = md.schema
        ix = {p: col_index(s, f"bbox.{p}") for p in ("xmin", "xmax", "ymin", "ymax")}
        groups = []
        for g in range(md.num_row_groups):
            rg = md.row_group(g)
            st = {p: rg.column(i).statistics for p, i in ix.items()}
            if any(v is None or not v.has_min_max for v in st.values()):
                groups.append(g)
                continue
            if (st["xmax"].max >= XMIN and st["xmin"].min <= XMAX
                    and st["ymax"].max >= YMIN and st["ymin"].min <= YMAX):
                groups.append(g)
        print(f"{key.split('/')[-1][:10]}: {len(groups)}/{md.num_row_groups} row groups", flush=True)
        if not groups:
            return rows
        tbl = pf.read_row_groups(groups, columns=COLS).to_pylist()
    for r in tbl:
        b = r["bbox"]
        x, y = (b["xmin"] + b["xmax"]) / 2, (b["ymin"] + b["ymax"]) / 2
        if not (XMIN <= x <= XMAX and YMIN <= y <= YMAX):
            continue
        tax = r["taxonomy"] or {}
        addr = (r["addresses"] or [{}])[0] or {}
        rows.append({
            "id": r["id"],
            "name": (r["names"] or {}).get("primary"),
            "primary": tax.get("primary"),
            "hierarchy": tax.get("hierarchy") or [],
            "alternate": tax.get("alternates") or [],
            "basic": r["basic_category"],
            "status": r["operating_status"],
            "confidence": r["confidence"],
            "lon": x, "lat": y,
            "address": addr.get("freeform"),
        })
    return rows


allrows = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for rows in ex.map(process, keys):
        allrows.extend(rows)
print(f"{len(allrows)} places in bbox", flush=True)
with open(OUT, "w") as f:
    json.dump(allrows, f, ensure_ascii=False)
