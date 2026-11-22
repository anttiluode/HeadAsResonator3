#!/usr/bin/env python
"""Same full-rate public run, fixed channel selection, two EEG references.

Follow-up designed AFTER observing a strong 0ms audio-dependent spatially
uniform pattern on sub-03 run-02. Not preregistered; no causal hardware
source classification. Never include microphone monitor in reference mean.
"""
import json,tempfile
from pathlib import Path
import numpy as np

from scripts.real_nemar_excerpt import fetch_excerpt,channels_from_sidecar,urls
from resonator3.cli import analyze


def main():
    from mne.io import read_raw_edf
    edf_url,side_url=urls("original")
    meta=channels_from_sidecar(side_url)
    channels=[f"EEG{i:03d}" for i in range(1,129)]
    names=[f"EEG{i:03d}" for i in range(1,129,8)]
    assert len(names)==16
    assert all(meta[name]["type"]=="EEG" for name in channels)
    assert "Speaking microphone" in meta["EEG131"]["description"]
    with tempfile.TemporaryDirectory() as temp:
        edf=Path(temp)/"excerpt.edf"
        info=fetch_excerpt(edf,edf_url,start_seconds=0,duration_seconds=35)
        raw=read_raw_edf(edf,preload=False,verbose="ERROR")
        fs=float(raw.info["sfreq"])
        audio=raw.get_data(picks=["EEG131"])[0]
        all_eeg=raw.get_data(picks=channels)
        raw.close()
    selected_idx=np.arange(0,128,8)
    base=all_eeg[selected_idx].copy()
    mean_reference=all_eeg.mean(axis=0)
    car=base-mean_reference
    root=Path("results/reference_ablation")
    common={
      "dataset":"NEMAR on007808 / original sub-03 ses-20240821 speechopen run-02",
      "first_seconds":35,
      "input":"speaking-microphone monitor EEG131 in same 1200Hz EDF",
      "selected_channels":names,
      "exclusion":"audio monitor never included in common average",
      "re_reference_population":"all 128 true EEG channels",
      "note":"Follow-up motivated by first run; not a prospective validation"
    }
    results={}
    for key,Y in [("raw",base),("car",car)]:
        s=analyze(audio,Y,names,fs,root/key,
                  band=(50,500),nperseg=4096,pre_ms=20,
                  post_ms=120,step_ms=1,wrong_audio_shifts=3,
                  dataset_meta={**common,"reference":key})
        r=s["rows"]
        results[key]={
            "mean_test_r2":float(np.mean([v["heldout_r2"] for v in r])),
            "median_test_r2":float(np.median([v["heldout_r2"] for v in r])),
            "max_test_r2":float(np.max([v["heldout_r2"] for v in r])),
            "mean_coherence":float(np.mean([v["coherence_mean_in_band"] for v in r])),
            "mean_peak_coherence":float(np.mean([v["coherence_peak_in_band"] for v in r])),
            "audio_positive_count":sum(v["above_shifted_audio_controls"] for v in r),
            "per_channel":[{"channel":v["channel"],
                            "heldout_r2":v["heldout_r2"],
                            "mean_coherence":v["coherence_mean_in_band"],
                            "best_null_r2":v["wrong_audio_best_r2"],
                            "negative_lag_fraction":v["negative_lag_energy_fraction"]}
                           for v in r]
        }
    report={
      "design":common,
      "source_edf":edf_url,
      "results":results,
      "mean_r2_difference_raw_minus_car":
         results["raw"]["mean_test_r2"]-results["car"]["mean_test_r2"],
      "warnings":[
        "Common-average reference can cancel broadly shared genuine signals too.",
        "A vanishing response is evidence for spatially shared pickup, not specific proof of cable vibration or electrical bleed.",
        "Sample clock is common; analog hardware and referencing delays may differ.",
        "Only one 35s recording, 16 fixed target electrodes, 128-channel reference; no cross-run validation."
      ]
    }
    (root/"reference_comparison.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:{v:val for v,val in x.items() if v!="per_channel"}
                      for k,x in results.items()},indent=2),flush=True)


if __name__=="__main__":
    main()
