#!/usr/bin/env python
"""Find actual local BIDS EDF/WAV pairs in ds007808 without fetching 1.54 TB.

No hidden download, no guessed session/run, no automatic timing alignment.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path


def entities(filename):
    """Parse only the stable BIDS entity tokens needed to match audio/EEG."""
    import re
    return {k:v for k,v in re.findall(r"(sub|ses|task|acq|run)-([^_]+)",
                                    Path(filename).name)}


def find_pairs(root,tasks=("speechopen","listening","listeningcovert")):
    root=Path(root).expanduser()
    pairs=[]
    for eeg in sorted(root.glob("sub-*/ses-*/eeg/*_eeg.edf")):
        identity=entities(eeg.name)
        if identity.get("task") not in tasks:
            continue
        beh=eeg.parent.parent/"beh"
        if not beh.is_dir():continue
        for wav in sorted(beh.glob("*.wav")):
            wid=entities(wav.name)
            if all(wid.get(k)==identity.get(k) for k in
                   ("sub","ses","task","acq","run")):
                pairs.append({"edf":str(eeg),"wav":str(wav),
                              "task":identity.get("task"),
                              "subject":identity.get("sub"),
                              "session":identity.get("ses"),
                              "run":identity.get("run"),
                              "acquisition":identity.get("acq")})
    return pairs


def main():
    p=argparse.ArgumentParser(description="List or audit selected local ds007808 EDF/WAV pairs")
    p.add_argument("--root",required=True,help="Local OpenNeuro/NEMAR BIDS directory")
    p.add_argument("--tasks",nargs="+",default=["speechopen","listening","listeningcovert"])
    p.add_argument("--run",action="store_true",help="Actually analyze found local pairs")
    p.add_argument("--limit",type=int,default=3,help="Maximum total selected EDF/WAV pairs")
    p.add_argument("--duration",type=float,default=35)
    p.add_argument("--max-channels",type=int,default=128)
    p.add_argument("--out",default="results/bids_audit")
    a=p.parse_args()
    found=find_pairs(a.root,a.tasks)
    print(json.dumps({"pairs_locally_available":len(found),
                      "sample":found[:min(a.limit,10)]},indent=2))
    out=Path(a.out);out.mkdir(exist_ok=True,parents=True)
    (out/"available_pairs.json").write_text(
        json.dumps({"pairs":found},indent=2)+"\n",encoding="utf-8")
    if not a.run:
        return
    if not found:
        raise SystemExit("No paired EDF/WAV files found. Download selected runs first.")
    results=[]
    for i,entry in enumerate(found[:max(0,a.limit)]):
        path=out/f"{i:03}_{entry['subject']}_{entry['task']}_{entry['session']}_{entry['run']}"
        cmd=[sys.executable,"-m","resonator3.cli",
             "--edf",entry["edf"],"--wav",entry["wav"],
             "--duration",str(a.duration),"--max-channels",str(a.max_channels),
             "--out",str(path)]
        print("ANALYZE",entry,flush=True)
        subprocess.run(cmd,check=True)
        scored=json.loads((path/"summary.json").read_text())
        rows=scored["rows"]
        results.append({**entry,"result_dir":str(path),
                        "channels":scored["channels"],
                        "max_heldout_r2":max(r["heldout_r2"] for r in rows),
                        "channels_beating_shifted_audio":sum(
                            r["above_shifted_audio_controls"] for r in rows)})
    (out/"batch_summary.json").write_text(json.dumps({
        "results":results,
        "warning":"Task comparison is observational; imagery intervals require event markers.",
        "explicit_missing_conditions":"Any task with no downloaded paired recording is absent, not a negative effect."
    },indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
