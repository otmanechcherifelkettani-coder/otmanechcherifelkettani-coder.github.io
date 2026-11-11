import re,json,requests,fsspec,pyarrow.parquet as pq
from shapely import wkb
from shapely.geometry import mapping
B="https://overturemaps-us-west-2.s3.us-west-2.amazonaws.com"
XMIN,YMIN,XMAX,YMAX=-9.6,31.8,-6.3,34.1
keys=re.findall(r"<Key>([^<]+\.parquet)</Key>",requests.get(f"{B}/?list-type=2&prefix=release/2026-10-21.0/theme=divisions/type=division_area/").text)
fs=fsspec.filesystem("http",block_size=4<<20); out=[]
for k in keys:
    pf=pq.ParquetFile(fs.open(f"{B}/{k}","rb")); md=pf.metadata; s=md.schema
    idx={c:[i for i in range(len(s)) if s.column(i).path==f"bbox.{c}"][0] for c in("xmin","xmax","ymin","ymax")}
    g=[j for j in range(md.num_row_groups) if (lambda st:st['xmax'].max>=XMIN and st['xmin'].min<=XMAX and st['ymax'].max>=YMIN and st['ymin'].min<=YMAX)({c:md.row_group(j).column(i).statistics for c,i in idx.items()})]
    if not g: continue
    for r in pf.read_row_groups(g,columns=["names","subtype","country","geometry","bbox"]).to_pylist():
        if r["country"]!="MA" or r["subtype"] not in("region","county"): continue
        b=r["bbox"]
        if b["xmax"]<XMIN or b["xmin"]>XMAX or b["ymax"]<YMIN or b["ymin"]>YMAX: continue
        n=r["names"] or {}; name=dict(n.get("common") or {}).get("fr") or n.get("primary")
        out.append({"name":name,"subtype":r["subtype"],"geom":wkb.loads(r["geometry"])})
reg=[o for o in out if o["subtype"]=="region" and "Casablanca" in (o["name"] or "")]
print([ (o["name"],o["subtype"]) for o in out if o["subtype"]=="region"])
R=reg[0]["geom"]; print("region bounds",R.bounds, "area deg2",R.area)
prov=[o for o in out if o["subtype"]=="county" and R.buffer(-0.01).intersects(o["geom"]) and o["geom"].intersection(R).area>0.5*o["geom"].area]
print([p["name"] for p in prov])
json.dump({"region":{"name":reg[0]["name"],"geom":mapping(R.simplify(0.002))},
           "provinces":[{"name":p["name"],"geom":mapping(p["geom"].simplify(0.002))} for p in prov]},open("region.json","w"),ensure_ascii=False)
