#!/usr/bin/env python
"""Gate 002: does post-CAR speech pickup track audio, lip EMG, or both?

Single verified public OpenNeuro/NEMAR run, high-rate same-clock acquisition.
Three *fixed, nonoverlapping* 35s windows: [0,35),[120,155),[240,275)s.
The first is the previously examined window; the latter two are independent
time intervals with no tuning/selection based on their outcomes.

Inputs are recorded speaking audio monitors EEG131/132 and upper/lower lip
bipolar EMG EEG135-136/137-138. Listening monitors EEG129/130 and EOG
EEG133-134 are documented controls. Outputs are 16 predeclared
EEG001,009,...121, each CAR-referenced against all 128 EEG channels.
All physical meanings come from the public BIDS channels.tsv, not label order.

CAUTION: microphone and lip EMG both arise from vocal acts; conditional
prediction does not distinguish anatomical origin or prove neural response.
"""
from __future__ import annotations
import json,tempfile
from pathlib import Path

import numpy as np
from mne.io import read_raw_edf
from resonator3.cli import analyze
from resonator3.conditional import bandpass_sources,conditional_predictors
from resonator3.core import candidate_lags,_fit_and_score,_design,_scores
from scripts.real_nemar_excerpt import urls,fetch_excerpt,channels_from_sidecar

TIMES=(0,120,240)
DURATION=35
ELECTRODES=tuple(f"EEG{i:03d}" for i in range(1,129,8))
REFERENCE=tuple(f"EEG{i:03d}" for i in range(1,129))
AUX={
    "listen1":"EEG129","listen2":"EEG130",
    "mic1":"EEG131","mic2":"EEG132",
    "eog_positive":"EEG133","eog_negative":"EEG134",
    "emg_upper_positive":"EEG135","emg_upper_negative":"EEG136",
    "emg_lower_positive":"EEG137","emg_lower_negative":"EEG138",
}


def verify_roles(metadata):
    if any(metadata.get(c,{}).get("type")!="EEG" for c in REFERENCE):
        raise ValueError("CAR must include precisely 128 BIDS EEG channels")
    expected={
       "EEG129":("MISC","Listening audio monitor"),
       "EEG130":("MISC","Listening audio monitor"),
       "EEG131":("MISC","Speaking microphone monitor"),
       "EEG132":("MISC","Speaking microphone monitor"),
       "EEG133":("EOG","EOG electrode"),
       "EEG134":("EOG","EOG electrode"),
       "EEG135":("EMG","Upper-lip EMG electrode"),
       "EEG136":("EMG","Upper-lip EMG electrode"),
       "EEG137":("EMG","Lower-lip EMG electrode"),
       "EEG138":("EMG","Lower-lip EMG electrode"),
    }
    for label,(type_,text) in expected.items():
        row=metadata.get(label,{})
        if row.get("type")!=type_ or text not in row.get("description",""):
            raise ValueError(f"{label} BIDS type/description changed; refusing")
    return True


def extract_signals(raw):
    fs=float(raw.info["sfreq"])
    if abs(fs-1200)>1e-3:
        raise ValueError("Expected 1200Hz full-rate EDF, not 250Hz Zarr")
    if not set(REFERENCE).issubset(raw.ch_names) or not set(AUX.values()).issubset(raw.ch_names):
        raise ValueError("Channels absent; do not guess labels")
    eeg=raw.get_data(picks=list(REFERENCE))
    aux={k:raw.get_data(picks=[name])[0] for k,name in AUX.items()}
    # Compute sensor common mean BEFORE selecting outputs. No audio,
    # muscle, ocular or auxiliary channel enters the EEG reference.
    offset=np.mean(eeg,axis=0)
    car=eeg[np.arange(0,128,8)]-offset
    src={
      "mic1":aux["mic1"],
      "mic2":aux["mic2"],
      "lip_upper":aux["emg_upper_positive"]-aux["emg_upper_negative"],
      "lip_lower":aux["emg_lower_positive"]-aux["emg_lower_negative"],
      "eog":aux["eog_positive"]-aux["eog_negative"],
      "listen1":aux["listen1"],
      "listen2":aux["listen2"],
    }
    return fs,src,car


def _stats(values):
    vals=np.asarray(values,dtype=float)
    if not len(vals):
        return None
    return {"mean":float(np.mean(vals)),
            "median":float(np.median(vals)),
            "minimum":float(np.min(vals)),
            "maximum":float(np.max(vals))}


def _group_summary(conditional,names):
    groups={}
    for k,g in conditional["groups"].items():
        scores=g["test_r2"]
        groups[k]={
            "active":g["active"],
            "mean_test_r2":float(np.mean(scores)) if scores is not None else None,
            "per_channel_test_r2":dict(zip(names,scores)) if scores is not None else None,
            "source_channels":g["sources"],
        }
    return groups


def run():
    which="original"
    url,sideurl=urls(which)
    metadata=channels_from_sidecar(sideurl)
    verify_roles(metadata)
    root=Path("results/real_gate_002")
    root.mkdir(parents=True,exist_ok=True)
    entries=[]
    frozen=None
    for start in TIMES:
        with tempfile.TemporaryDirectory(prefix="har3_excerpt_") as temp:
            path=Path(temp)/"partial.edf"
            info=fetch_excerpt(path,url,start_seconds=start,duration_seconds=DURATION)
            raw=read_raw_edf(path,preload=False,verbose="ERROR")
            fs,src,car=extract_signals(raw)
            raw.close()
        # Each window processed separately, no transfer of training data.
        # First window repeats the earlier post-CAR finding; 120/240s
        # segments have no tuning and are held independently.
        folder=root/f"start_{start:03d}"
        microphone=src["mic1"]
        aud=analyze(microphone,car,list(ELECTRODES),fs,folder,
                    band=(50,500),nperseg=4096,
                    pre_ms=20,post_ms=120,step_ms=1,
                    wrong_audio_shifts=3,
                    dataset_meta={
                        "dataset":"NEMAR on007808 / OpenNeuro ds007808",
                        "source":url,
                        "interval_start_seconds":start,
                        "window_seconds":DURATION,
                        "audio_input":"EEG131, BIDS speaking microphone monitor",
                        "outputs":"16 fixed CAR electrodes, mean of 128 BIDS EEG only",
                        "auxiliary":"EEG132 speaking monitor 2, EEG135..138 lip EMG, EEG133..134 EOG, EEG129..130 listening monitor",
                        "warning":"Auxiliaries are non-neural references, not tissue labels"
                    })
        xfiltered,yfiltered=bandpass_sources(src,car,fs,low=50,high=500)
        conditional=conditional_predictors(xfiltered,yfiltered,fs)
        # Distinguish a response that can be independently re-fit in each
        # 35-second window from a stable, transportable physical operator.
        # Freeze the FIR coefficients from the FIRST window's training
        # interval BEFORE analyzing windows 120 and 240 seconds.
        lag_grid=candidate_lags(fs,negative_ms=20,positive_ms=120,step_ms=1)
        if start==TIMES[0]:
            coef,intercept,_,_,_=_fit_and_score(
                xfiltered["mic1"],yfiltered,lag_grid,
                ridge=.03,max_taps=9,
                spacing_samples=max(1,round(fs*.004)))
            frozen=(coef,intercept,lag_grid)
            frozen_score=None
        else:
            C,b,lag_grid=frozen
            design,time_idx=_design(xfiltered["mic1"],lag_grid)
            # Full later segment is an outer holdout relative to first-
            # window training. No re-centering or re-fitting of weights.
            frozen_score=_scores(yfiltered[:,time_idx].T,
                                 design@C+b)

        rows={v["channel"]:v for v in aud["rows"]}
        positive=[k for k in ELECTRODES if rows[k]["above_shifted_audio_controls"]]
        entries.append({
            "start_seconds":start,"end_seconds":start+DURATION,
            "number_samples":int(car.shape[1]),
            "source_standard_deviation":conditional["source_standard_deviation"],
            "source_active":conditional["source_active"],
            "audio_to_car_mean_coherence":float(np.mean([
                v["coherence_mean_in_band"] for v in rows.values()])),
            "audio_to_car_mean_heldout_r2":float(np.mean([
                v["heldout_r2"] for v in rows.values()])),
            "car_positive_audio_channels":positive,
            "car_positive_audio_count":len(positive),
            "frozen_first_window_train_to_this_window_r2":(
                dict(zip(ELECTRODES,frozen_score.tolist()))
                if frozen_score is not None else None),
            "source_group_comparison":_group_summary(conditional,ELECTRODES),
            "mic_increment_over_lip":dict(zip(
                ELECTRODES,conditional["mic_increment_over_lip"]))
                if conditional["mic_increment_over_lip"] is not None else None,
            "lip_increment_over_mic":dict(zip(
                ELECTRODES,conditional["lip_increment_over_mic"]))
                if conditional["lip_increment_over_mic"] is not None else None,
            "mic_increment_vs_shifted_given_lip":dict(zip(
                ELECTRODES,conditional["mic_increment_vs_shifted_mic_given_lip"]))
                if conditional["mic_increment_vs_shifted_mic_given_lip"] is not None else None,
            "car_audio_score":{
                k:{"heldout_r2":v["heldout_r2"],
                   "wrong_audio_best_r2":v["wrong_audio_best_r2"],
                   "mean_coherence":v["coherence_mean_in_band"],
                   "peak_coherence":v["coherence_peak_in_band"]}
                for k,v in rows.items()},
            "byte_range_source":info["source_url"],
            "temporary_raw_excerpt_removed":True,
        })
        print(f"WINDOW [{start},{start+DURATION}): "
              f"CAR audio-positive {len(positive)}/16, "
              f"mean R2 {entries[-1]['audio_to_car_mean_heldout_r2']:+.4f}, "
              f"mic source SD {conditional['source_standard_deviation']['mic1']:.4g}",
              flush=True)
    # These survivors are SELECTED after seeing window 0, so results on
    # later windows must be reported as a post-selection temporal check.
    survivors=entries[0]["car_positive_audio_channels"]
    comparisons={}
    for c in survivors:
        comparisons[c]=[
            {"start_seconds":r["start_seconds"],
             "car_audio_heldout_r2":r["car_audio_score"][c]["heldout_r2"],
             "first_window_frozen_fir_r2":(
                 r["frozen_first_window_train_to_this_window_r2"][c]
                 if r["frozen_first_window_train_to_this_window_r2"] is not None
                 else None),
             "audio_minus_best_wrong_r2":r["car_audio_score"][c]["heldout_r2"]-
                                         r["car_audio_score"][c]["wrong_audio_best_r2"],
             "mic_only_fixedlag_r2":r["source_group_comparison"]["mic1"]["per_channel_test_r2"][c],
             "lip_only_fixedlag_r2":r["source_group_comparison"]["lip_emg"]["per_channel_test_r2"][c],
             "both_fixedlag_r2":r["source_group_comparison"]["mic_plus_lip"]["per_channel_test_r2"][c],
             "lip_increment_over_mic":(
                 r["lip_increment_over_mic"][c] if r["lip_increment_over_mic"] is not None else None),
             "mic_increment_over_lip":(
                 r["mic_increment_over_lip"][c] if r["mic_increment_over_lip"] is not None else None),
            }
            for r in entries
        ]
    output={
        "title":"HeadAsResonator3 real Gate 002: BIDS-confirmed lip EMG and same-clock microphone contrasts",
        "source_edf":url,"channels_sidecar":sideurl,
        "sampling_hz":1200,
        "intervals_seconds":[[s,s+DURATION] for s in TIMES],
        "windows":[{"start_seconds":r["start_seconds"],
                    "end_seconds":r["end_seconds"],
                    "source_standard_deviation":r["source_standard_deviation"],
                    "source_active":r["source_active"],
                    "audio_to_car_mean_coherence":r["audio_to_car_mean_coherence"],
                    "audio_to_car_mean_heldout_r2":r["audio_to_car_mean_heldout_r2"],
                    "car_positive_audio_channels":r["car_positive_audio_channels"],
                    "car_positive_audio_count":r["car_positive_audio_count"],
                    "frozen_first_window_train_to_this_window_r2":
                        r["frozen_first_window_train_to_this_window_r2"],
                    "source_group_comparison":r["source_group_comparison"],
                    "mic_increment_over_lip":r["mic_increment_over_lip"],
                    "lip_increment_over_mic":r["lip_increment_over_mic"],
                    "mic_increment_vs_shifted_given_lip":
                        r["mic_increment_vs_shifted_given_lip"]}
                   for r in entries],
        "window0_survivors_postselected":survivors,
        "survivor_generalization":comparisons,
        "raw_data_policy":"Only derived channel-level results are uploaded. Each raw excerpt deleted on exit.",
        "interpretation":"Predictive contrasts among recorded electrical/microphone channels; physical source not uniquely identifiable.",
        "limits":[
            "Three windows from ONE previously selected participant/run; not cross-subject replication.",
            "Original 0..35s window selected due to strong earlier signal; other windows were frozen in code before running.",
            "The three survivor IDs were postselected from the initial window; they are not independent discovery targets.",
            "A fixed sparse FIR is fitted only on the first 60% of window 0 and evaluated without refitting on complete later windows; scores may be negative if the response changes.",
            "Lip EMG and speech microphone share common vocal causes; gains do not prove EMG contamination or a neural source.",
            "The microphone channel is a recorded monitor, not an exogenous instrument.",
            "CAR can remove widespread real electrophysiology as well as pickup.",
            "Seven fixed signed lag taps are illustrative; results depend on bandpass 50–500Hz and sensor calibration.",
            "All comparisons within time slices, no hardware intervention, no causal physical routing identification."
        ]
    }
    (root/"GATE_002_summary.json").write_text(json.dumps(output,indent=2)+"\n")
    print("POSTSELECTED WINDOW-0 SURVIVORS:",survivors,flush=True)
    for ch,records in comparisons.items():
        print("SURVIVOR",ch,[(r["start_seconds"],
                  round(r["car_audio_heldout_r2"],4),
                  round(r["lip_only_fixedlag_r2"],4),
                  round(r["both_fixedlag_r2"],4),
                  None if r["first_window_frozen_fir_r2"] is None
                  else round(r["first_window_frozen_fir_r2"],4))
                  for r in records],flush=True)
    print("WROTE",root/"GATE_002_summary.json",flush=True)


if __name__=="__main__":
    run()
