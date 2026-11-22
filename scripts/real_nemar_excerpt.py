#!/usr/bin/env python
"""Run HeadAsResonator3 on one REAL, public, same-clock NEMAR EDF excerpt.

Source: OpenNeuro ds007808 / NEMAR on007808 v1.0.0. We do not fetch
the parallel external WAV (which may have an independent recording clock).
Instead BIDS channels.tsv identifies EEG131 as the SPEAKING MICROPHONE
MONITOR recorded inside the same 1200Hz EDF as the EEG electrode channels.

Downloads 40 one-second EDF records by HTTP Range (~13.3 MB), reconstructs
a valid local 40-second EDF with the original header and shortened record
count, analyzes, and discards the raw excerpt. No remote job or sensor
anatomy inference. The HTTP range must be honored (206).
"""
from __future__ import annotations
import argparse,csv,io,json,tempfile
from pathlib import Path
from urllib.request import Request,urlopen

import numpy as np
from resonator3.cli import analyze

BASE="https://data.nemar.org/on007808/v1.0.0/sub-01/ses-20230829/eeg/"
STEM="sub-01_ses-20230829_task-speechopen_acq-pangolin_run-01"
EDF_URL=BASE+STEM+"_eeg.edf"
SIDE_URL=BASE+STEM+"_channels.tsv"


def read_range(url, start, stop, max_bytes=20_000_000):
    if stop<start or stop-start+1>max_bytes:
        raise ValueError("refusing oversized or inverted HTTP Range")
    req=Request(url,headers={"Range":f"bytes={start}-{stop}",
                             "User-Agent":"HeadAsResonator3-2026-study/0.1"})
    with urlopen(req,timeout=90) as r:
        if r.status!=206:
            raise RuntimeError(f"Server did not honor HTTP Range ({r.status}); refusing full EDF")
        data=r.read(max_bytes+1)
        cr=r.headers.get("Content-Range","")
    if len(data)!=stop-start+1:
        raise RuntimeError(f"Range length mismatch {len(data)} vs {stop-start+1}: {cr}")
    if not cr.startswith(f"bytes {start}-{stop}/"):
        raise RuntimeError("Unexpected Content-Range "+cr)
    return data


def fetch_excerpt(path, *, start_seconds=60,duration_seconds=40):
    head256=read_range(EDF_URL,0,255,max_bytes=512)
    if head256[:8].strip()!=b"0":
        raise RuntimeError("Not recognizable EDF header")
    nsig=int(head256[252:256].strip())
    hd=int(head256[184:192].strip())
    if not (1<=nsig<=1000 and hd==256+256*nsig):
        raise RuntimeError("Invalid EDF per-signal header size")
    header=read_range(EDF_URL,0,hd-1,max_bytes=512_000)
    labels=[header[256+16*i:256+16*(i+1)].decode("ascii","replace").strip()
            for i in range(nsig)]
    samples=[int(header[256+216*nsig+8*i:256+216*nsig+8*(i+1)].strip())
             for i in range(nsig)]
    rec_time=float(header[244:252].strip())
    n_total=int(header[236:244].strip())
    rec_bytes=2*sum(samples)
    if not (0<rec_time<=10 and rec_bytes>0 and rec_bytes<5_000_000):
        raise RuntimeError("Invalid EDF records")
    start_record=int(round(start_seconds/rec_time))
    n_records=int(round(duration_seconds/rec_time))
    if not (n_records>=12 and start_record>=0 and start_record+n_records<=n_total):
        raise ValueError("Selected excerpt outside original EDF or too short")
    start_byte=hd+start_record*rec_bytes
    stop_byte=start_byte+n_records*rec_bytes-1
    raw=read_range(EDF_URL,start_byte,stop_byte,max_bytes=20_000_000)
    newhead=bytearray(header)
    newhead[236:244]=str(n_records).ljust(8).encode("ascii")
    Path(path).write_bytes(newhead+raw)
    return {
      "source_url":EDF_URL,"header_bytes":hd,
      "original_records":n_total,"record_duration_seconds":rec_time,
      "excerpt_start_original_seconds":start_record*rec_time,
      "excerpt_duration_seconds":n_records*rec_time,
      "excerpt_bytes":hd+len(raw),
      "signals":nsig,"signal_labels":labels,
      "per_signal_samples":samples
    }


def channels_from_sidecar():
    with urlopen(SIDE_URL,timeout=45) as response:
        rows=list(csv.DictReader(io.StringIO(response.read(200000).decode("utf-8-sig")),
                                  delimiter="\t"))
    by_name={r["name"]:r for r in rows}
    # Must be anchored to *published* BIDS channel type, not guessed from
    # numerical EEG labels.
    source=by_name.get("EEG131")
    if not source or source.get("type")!="MISC" or "Speaking microphone" not in source.get("description",""):
        raise RuntimeError("EEG131 is not verified as a speaking microphone monitor")
    return by_name


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--start",type=int,default=60)
    p.add_argument("--duration",type=int,default=40)
    p.add_argument("--out",default="results/real_nemar_001")
    a=p.parse_args()
    from mne.io import read_raw_edf
    sidecar=channels_from_sidecar()
    names=[f"EEG{index:03d}" for index in range(1,129,8)] # 16 predeclared spaced labels
    assert len(names)==16
    if any(sidecar.get(name,{}).get("type")!="EEG" for name in names):
        raise RuntimeError("One of the output channels isn't declared EEG")
    with tempfile.TemporaryDirectory() as t:
        path=Path(t)/"public_excerpt.edf"
        info=fetch_excerpt(path,start_seconds=a.start,duration_seconds=a.duration)
        raw=read_raw_edf(path,preload=False,verbose="ERROR")
        fs=float(raw.info["sfreq"])
        if fs<1000:
            raise RuntimeError(f"Expected original high-rate 1200 Hz; observed {fs}")
        if any(name not in raw.ch_names for name in names+["EEG131"]):
            raise RuntimeError("EDF file label/sidecar mismatch")
        # SAME EDF SAMPLE CLOCK; not an independently aligned external WAV.
        audio=raw.get_data(picks=["EEG131"])[0]
        Y=raw.get_data(picks=names)
        raw.close()
        if float(np.std(audio))<1e-11:
            raise RuntimeError("Speaking-monitor channel nearly silent")
        summary=analyze(audio,Y,names,fs,a.out,band=(50,500),
                        pre_ms=20,post_ms=120,step_ms=1,
                        wrong_audio_shifts=3,
                        dataset_meta={
                          "dataset":"NEMAR on007808 v1.0.0 / OpenNeuro ds007808",
                          "edf_source":EDF_URL,
                          "sidecar":SIDE_URL,
                          "audio_input":"EEG131, speaking microphone monitor channel 1 (inside same EDF)",
                          "timebase":"same EDF sample clock, hardware transfer delays unknown",
                          "original_interval_start_seconds":a.start,
                          "duration_seconds":a.duration,
                          "electrodes":"fixed EEG001,009,...,121 (16 EEG-type sensors)",
                          "source_notice":"EDF raw excerpt downloaded temporarily and not uploaded"})
    report={"download_meta":{k:v for k,v in info.items() if k not in
                            ("per_signal_samples","signal_labels")},
            "summary_path":str(Path(a.out)/"summary.json"),
            "strongest_channels":sorted(summary["rows"],
                key=lambda r:r["heldout_r2"],reverse=True)[:8]}
    out=Path(a.out)/"real_excerpt_receipt.json"
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2)[:18000],flush=True)


if __name__=="__main__":
    main()
