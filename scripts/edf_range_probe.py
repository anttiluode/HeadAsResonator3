#!/usr/bin/env python
"""Check a SINGLE 8 KiB HTTP range of a public NEMAR EDF.

No full EEG downloaded. Uses exact index-linked path. Does not infer a
physical pathway or alter the repository's signal analysis.
"""
from __future__ import annotations
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import json
from pathlib import Path

URL=("https://data.nemar.org/on007808/v1.0.0/sub-01/ses-20230829/eeg/"
     "sub-01_ses-20230829_task-speechopen_acq-pangolin_run-01_eeg.edf")


def main():
    req=Request(URL,headers={"Range":"bytes=0-8191",
                             "User-Agent":"HeadAsResonator3-public-research/0.1"})
    with urlopen(req,timeout=55) as res:
        status=res.status
        header={k:v for k,v in res.headers.items() if k.lower() in
                 ("content-range","content-length","content-type","accept-ranges")}
        b=res.read(8192)
    if not b.startswith(b"0"):
        # EDF starts with ASCII 0 or spaces; do not trust a non-EDF response.
        label="not-obviously-edf"
    else:
        label="possible-edf"
    nsignals=int(b[252:256].strip() or b"0") if len(b)>=256 and b[252:256].strip().isdigit() else None
    header_bytes=int(b[184:192].strip() or b"0") if len(b)>=192 and b[184:192].strip().isdigit() else None
    names=[]
    if header_bytes is not None and len(b)>=header_bytes and nsignals:
        for i in range(nsignals):
            names.append(b[256+16*i:256+16*(i+1)].decode("ascii",errors="replace").strip())
    report={"url":URL,"status":status,"headers":header,"bytes_read":len(b),
            "looks_like_edf":label,"header_bytes":header_bytes,
            "nsignals":nsignals,"signal_labels":names,
            "warning":"Only first 8192 bytes requested/read. No EEG signal samples, no full EDF."}
    p=Path("results/edf_range_probe.json");p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2)[:12000],flush=True)


if __name__=="__main__":
    main()
