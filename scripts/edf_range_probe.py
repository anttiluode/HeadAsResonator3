#!/usr/bin/env python
"""Check a SINGLE 64 KiB HTTP range of a public NEMAR EDF.

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
    req=Request(URL,headers={"Range":"bytes=0-65535",
                             "User-Agent":"HeadAsResonator3-public-research/0.1"})
    with urlopen(req,timeout=55) as res:
        status=res.status
        header={k:v for k,v in res.headers.items() if k.lower() in
                 ("content-range","content-length","content-type","accept-ranges")}
        b=res.read(65536)
    if not b.startswith(b"0"):
        # EDF starts with ASCII 0 or spaces; do not trust a non-EDF response.
        label="not-obviously-edf"
    else:
        label="possible-edf"
    nsignals=int(b[252:256].strip() or b"0") if len(b)>=256 and b[252:256].strip().isdigit() else None
    header_bytes=int(b[184:192].strip() or b"0") if len(b)>=192 and b[184:192].strip().isdigit() else None
    names=[]
    record_duration=None
    bytes_per_record=None
    sample_counts=[]
    nrecords=None
    if header_bytes is not None and len(b)>=header_bytes and nsignals:
        for i in range(nsignals):
            names.append(b[256+16*i:256+16*(i+1)].decode("ascii",errors="replace").strip())
            s0=256+nsignals*216+8*i
            samples=int(b[s0:s0+8].strip() or b"0")
            sample_counts.append(samples)
        record_duration=float(b[244:252].strip())
        nrecords=int(b[236:244].strip())
        bytes_per_record=sum(sample_counts)*2
    report={"url":URL,"status":status,"headers":header,"bytes_read":len(b),
            "looks_like_edf":label,"header_bytes":header_bytes,
            "nsignals":nsignals,"signal_labels":names,
            "sample_counts":sample_counts,"record_duration":record_duration,
            "number_records":nrecords,"bytes_per_record":bytes_per_record,
            "potential_audio_channels":[name for name in names if any(
                k in name.lower() for k in ("audio","mic","vocal","sound","voice"))],
            "warning":"Only first 65536 bytes requested/read. No EEG signal samples, no full EDF."}
    p=Path("results/edf_range_probe.json");p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2)[:12000],flush=True)


if __name__=="__main__":
    main()
