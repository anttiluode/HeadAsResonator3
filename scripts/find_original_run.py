#!/usr/bin/env python
"""Find the exact run cited by HeadAsResonator, no EEG download."""
import urllib.request,json
from pathlib import Path

INDEX="https://zarr.nemar.org/on007808/zarr/index.json"
ORIGINAL="sub-03_ses-20240821_task-speechopen_acq-pangolin_run-02"


def main():
    with urllib.request.urlopen(INDEX,timeout=45) as h:
        idx=json.load(h)
    matches=[{
      "zarr":s["zarr"],
      "edf_path":s.get("path"),
      "groups":s.get("groups",[])
    } for s in idx.get("stores",[])
       if ORIGINAL in s.get("zarr","") or ORIGINAL in s.get("path","")]
    report={"index_url":INDEX,"old_repository_run":ORIGINAL,
            "exact_matches":matches,
            "finding":("exact old run found in dataset index" if matches
                       else "no exact index match; do not invent a path")}
    p=Path("results/old_run_lookup.json");p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2),flush=True)


if __name__=="__main__":
    main()
