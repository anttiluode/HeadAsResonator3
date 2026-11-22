"""Gate 003B selection: publicly indexed repeated runs from only 3 subjects.

This is a NEW limited-scope protocol after Gate 003's 8-subject
eligibility requirement failed. This file does not weaken or overwrite
the earlier eligibility failure.
"""
from __future__ import annotations
import json
from pathlib import Path
from scripts.choose_cross_subject_runs import (
    REGEX,EDF_ROOT,INDEX,ORIGINAL_STEM,KNOWN_NEGATIVE_STEM,read_index)


def choose_repeated_runs(index,per_subject=3):
    if per_subject<1:
        raise ValueError("per_subject must be positive")
    inventory={}
    for s in index.get("stores",[]):
        path=s.get("path","")
        m=REGEX.match(path)
        if not m or not any(float(g.get("source_rate_hz",0))>=1000
                            for g in s.get("groups",[])):
            continue
        inventory.setdefault(m.group(1),{})[m.group(3)]=path
    required={"01":KNOWN_NEGATIVE_STEM,"03":ORIGINAL_STEM}
    if not all(anchor in inventory.get(sub,{})
               for sub,anchor in required.items()) or "02" not in inventory:
        raise RuntimeError("Fewer than three predeclared subjects with both original anchors")
    # The first Gate003 searched for eight new participants and found only
    # one. We declare exactly the three eligible subjects 01,02,03 here.
    if len(inventory)!=3:
        raise RuntimeError(f"Expected exactly three index subjects; got {sorted(inventory)}")
    selected=[]
    for sub in ("01","02","03"):
        available=sorted(inventory[sub])
        anchor=required.get(sub)
        if anchor:
            stems=[anchor]+[p for p in available if p!=anchor][:per_subject-1]
        else:
            stems=available[:per_subject]
        for i,stem in enumerate(stems):
            label=("known_previous_negative" if sub=="01" and i==0 else
                   "known_original" if sub=="03" and i==0 else
                   "fresh_subject" if sub=="02" and i==0 else
                   "same_subject_different_run")
            path=inventory[sub][stem]
            selected.append({"label":label,"stem":stem,"subject":f"sub-{sub}",
                             "edf_path":path,"edf_url":EDF_ROOT+path,
                             "channels_tsv_url":EDF_ROOT+path.removesuffix("_eeg.edf")+"_channels.tsv",
                             "window_start_seconds":0,"window_duration_seconds":35})
    return {
      "source_index":INDEX,
      "protocol":"Gate 003B; declared after original 8-fresh-subject eligibility failure",
      "selection_uses_signal":False,
      "reason_for_rescope":"Only three eligible participants, of whom two were already observed",
      "n_subjects_eligible":len(inventory),
      "participant_ids":["sub-01","sub-02","sub-03"],
      "n_fresh_requested":1,
      "n_replicates_per_subject_requested":per_subject,
      "same_subject_repeats_not_independent_participants":True,
      "runs":selected,
      "warning":"This is NOT an 8-subject experiment. Known anchors and new subject are separate strata."
    }


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--per-subject",type=int,default=3)
    p.add_argument("--out",default="results/real_gate_003b/metadata_selection.json")
    args=p.parse_args()
    report=choose_repeated_runs(read_index(),args.per_subject)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2)[:16000],flush=True)


if __name__=="__main__":
    main()
