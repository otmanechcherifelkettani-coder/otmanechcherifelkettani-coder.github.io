"""Fetch neighbourhood / district name points from Overture divisions for a bbox (env BBOX) -> divisions.json."""
import json
import os
import re
import sys

import fsspec
import pyarrow.parquet as pq
import requests

RELEASE = sys.argv[1] if len(sys.argv) > 1 else "2026-10-21.0"
OUT = sys.argv[2] if len(sys.argv) > 2 else "divisions.json"
B = "https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com"
XMIN, YMIN, XMAX, YMAX = (map(float, os.environ["BBOX"].split(",")) if os.environ.get("BBOX")
                          else (-7.75, 33.45, -7.40, 33.66))
KEEP = ("neighborhood", "macrohood", "microhood", "locality", "borough", "localadmin", "county")
keys = re.findall(r"<Key>([^<]+\.parquet)</Key>",
                  requests.get(f"{B}/?list-type=2&prefix=release/{RELEASE}/theme=divisions/type=division/", timeout=60).text)
fs = fsspec.filesystem("http", block_size=4 << 20)
out = []
for k in keys:
    pf = pq.ParquetFile(fs.open(f"{B}/{k}", "rb"))
    md, s = pf.metadata, pf.metadata.schema
    idx = {c: next(i for i in range(len(s)) if s.column(i).path == f"bbox.{c}") for c in ("xmin", "xmax", "ymin", "ymax")}
    groups = []
    for j in range(md.num_row_groups):
        st = {c: md.row_group(j).column(i).statistics for c, i in idx.items()}
        if st["xmax"].max >= XMIN and st["xmin"].min <= XMAX and st["ymax"].max >= YMIN and st["ymin"].min <= YMAX:
            groups.append(j)
    if not groups:
        continue
    for r in pf.read_row_groups(groups, columns=["names", "subtype", "bbox"]).to_pylist():
        b = r["bbox"]
        x, y = (b["xmin"] + b["xmax"]) / 2, (b["ymin"] + b["ymax"]) / 2
        if XMIN <= x <= XMAX and YMIN <= y <= YMAX and r["subtype"] in KEEP:
            n = r["names"] or {}
            out.append({"name": dict(n.get("common") or {}).get("fr") or n.get("primary"),
                        "subtype": r["subtype"], "lon": x, "lat": y})
json.dump(out, open(OUT, "w"), ensure_ascii=False)
print(len(out), "division points")
