"""Gate 003: non-adaptive participant/run selection, then fixed audio/EEG audit.

No participant is selected based on EEG or audio samples. Public NEMAR Zarr
index is used only as a manifest of ORIGINAL full-rate EDF paths; the Zarr
sample stream is downsampled and is never used for the 440 Hz analysis.
"""
from __future__ import annotations
import json,re
from pathlib import Path
from urllib.request import urlopen

INDEX="https://zarr.nemar.org/on007808/zarr/index.json"
EDF_ROOT="https://data.nemar.org/on007808/v1.0.0/"
ORIGINAL_STEM="sub-03_ses-20240821_task-speechopen_acq-pangolin_run-02"
KNOWN_NEGATIVE_STEM="sub-01_ses-20230829_task-speechopen_acq-pangolin_run-01"
REGEX=re.compile(r"^sub-(\d+)/ses-([^/]+)/eeg/"
    r"(sub-\d+_ses-[^_]+_task-speechopen_acq-pangolin_run-\d+)_eeg\.edf$")


def choose_runs(index, n_fresh=8):
    """Reproducible lexical selection, NOT maximizing early signal response.

    Include two previously inspected anchors, up to eight *different*
    fresh subjects, and the first distinct run for sub-03 (if available).
    No replacements if individual files fail to download or validate.
    """
    by_subject={}
    candidate_paths={}
    for entry in index.get("stores",[]):
        path=entry.get("path","")
        m=REGEX.match(path)
        if not m:
            continue
        groups=entry.get("groups",[])
        if not any(float(g.get("source_rate_hz",0))>=1000 for g in groups):
            continue
        candidate_paths[m.group(3)]=path
        by_subject.setdefault(m.group(1),[]).append(m.group(3))
    for subject in by_subject:
        by_subject[subject]=sorted(set(by_subject[subject]))
    if ORIGINAL_STEM not in candidate_paths or KNOWN_NEGATIVE_STEM not in candidate_paths:
        raise RuntimeError("Public index no longer includes both predeclared anchors")
    picked=[
        ("known_original",ORIGINAL_STEM),
        ("known_previous_negative",KNOWN_NEGATIVE_STEM),
    ]
    fresh_subjects=[s for s in sorted(by_subject,key=lambda k:int(k))
                    if s not in ("01","03")][:n_fresh]
    if len(fresh_subjects)<n_fresh:
        raise RuntimeError(f"Only {len(fresh_subjects)} independent new subjects available")
    for sub in fresh_subjects:
        picked.append(("fresh_subject",by_subject[sub][0]))
    extra=[s for s in by_subject.get("03",[]) if s!=ORIGINAL_STEM]
    if extra:
        picked.append(("same_subject_different_run",extra[0]))
    selected=[]
    for kind,stem in picked:
        path=candidate_paths[stem]
        selected.append({"label":kind,"stem":stem,"subject":stem.split("_")[0],
                         "edf_path":path,"edf_url":EDF_ROOT+path,
                         "channels_tsv_url":EDF_ROOT+path.removesuffix("_eeg.edf")+"_channels.tsv",
                         "window_start_seconds":0,"window_duration_seconds":35})
    return {
        "source_index":INDEX,"source_archive_root":EDF_ROOT,
        "method":"lexically first full-rate speechopen pangolin run per subject, from public metadata only",
        "selection_uses_signal":False,
        "n_subjects_eligible":len(by_subject),
        "n_fresh_requested":n_fresh,
        "anchors":["known_original","known_previous_negative"],
        "runs":selected,
        "warning":"Original and known previous negative were preselected; fresh subjects were selected without reading signal values."
    }


def read_index():
    with urlopen(INDEX,timeout=50) as r:
        return json.load(r)


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--fresh",type=int,default=8)
    p.add_argument("--out",default="results/real_gate_003/selection.json")
    a=p.parse_args()
    result=choose_runs(read_index(),a.fresh)
    dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,indent=2)[:16000],flush=True)


if __name__=="__main__":
    main()
