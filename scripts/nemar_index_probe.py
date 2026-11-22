#!/usr/bin/env python
"""NEMAR on007808 public Zarr index metadata inspection; no data read."""
from __future__ import annotations
import argparse,json,urllib.request


INDEX="https://zarr.nemar.org/on007808/zarr/index.json"


def choose(index,task="speechopen",acquisition="pangolin",limit=5):
    matches=[]
    for store in index.get("stores",[]):
        # Index schema can evolve. Do not assume groups are always a single
        # string; keep all metadata and print candidate name and paths.
        name=str(store.get("zarr",""))
        groups=store.get("groups",[])
        joined=(name+" "+json.dumps(groups)).lower()
        if task.lower() not in joined or acquisition.lower() not in joined:
            continue
        matches.append({"zarr":name,"groups":groups,
                        "s3_uri":store.get("s3_uri"),
                        "meta":{k:v for k,v in store.items()
                                if k not in ("zarr","groups")}})
        if len(matches)>=limit:break
    return matches


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--task",default="speechopen")
    a.add_argument("--acquisition",default="pangolin")
    a.add_argument("--limit",type=int,default=4)
    a.add_argument("--out",default="results/nemar_index_probe.json")
    args=a.parse_args()
    with urllib.request.urlopen(INDEX,timeout=50) as res:
        index=json.load(res)
    from collections import Counter
    rates=Counter()
    by_task={}
    highrate=[]
    for store in index.get("stores",[]):
        name=str(store.get("zarr",""))
        for group in store.get("groups",[]):
            rate=group.get("rate")
            key=str(rate)
            rates[key]+=1
            task=next((p[5:] for p in name.split("_") if p.startswith("task-")),"unknown")
            by_task.setdefault(task,Counter())[key]+=1
            if isinstance(rate,(int,float)) and rate>=900 and len(highrate)<10:
                highrate.append({"zarr":name,"group":group})
    report={
        "available_stored_sample_rates":dict(rates),
        "rates_by_task":{k:dict(v) for k,v in by_task.items()},
        "sample_highrate_stores":highrate,
        "index_url":INDEX,
        "dataset_id":index.get("dataset_id"),
        "index_version":index.get("format_version"),
        "number_stores":len(index.get("stores",[])),
        "matches":choose(index,args.task,args.acquisition,args.limit),
        "warning":"Index metadata only, no EDF, audio or EEG was read."
    }
    from pathlib import Path
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2)[:9000],flush=True)


if __name__=="__main__":
    main()
