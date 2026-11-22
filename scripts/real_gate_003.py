"""HeadAsResonator3 Real Gate 003 — cross-participant acoustic common-mode test.

No per-subject retuning. Metadata-only selection in choose_cross_subject_runs.
Same 1200Hz EDF microphone monitor, EEG output channels, first 35s window,
linear audit, and shifted-audio controls for every selected run. Failure,
silence, missing data and negative scores remain in the denominator.

This experiment investigates prevalence of an AUDIO-LINKED EEG voltage;
physical material and neural source remain unidentifiable.
"""
from __future__ import annotations
import json,tempfile,traceback
from pathlib import Path
import numpy as np
from scipy import signal

from resonator3.core import lag_audit,complex_transfer
from resonator3.cli import _filter_pair
from scripts.choose_cross_subject_runs import choose_runs,read_index
from scripts.real_nemar_excerpt import fetch_excerpt,channels_from_sidecar

FS=1200
DURATION_S=35
BAND=(50,500)
CHANNELS=[f"EEG{k:03d}" for k in range(1,129)]
SELECTED=CHANNELS[::8]
THRESH_R2=.03
THRESH_GAIN=.03


def score_monitor(audio,eegr,fs=FS,seed=29):
    """Original Gate 001 method on raw and CAR voltages; no fit on test.

    As in prior gates, report R2 for each 16-electrode model and the
    maximum out of three refitted wrong-audio circular-shift controls.
    Derived spectra/coherence retained as quantitative summaries.
    """
    Y=np.atleast_2d(np.asarray(eegr,float))
    x=np.asarray(audio,float)
    xf,yf=_filter_pair(x,Y,fs,*BAND)
    transfer=complex_transfer(xf,yf,fs,nperseg=4096)
    audit=lag_audit(xf,yf,fs,negative_ms=20,positive_ms=120,
                    step_ms=1,max_taps=9,wrong_audio_shifts=3,seed=seed)
    band=(transfer.frequencies_hz>=BAND[0])&(
           transfer.frequencies_hz<=BAND[1])
    coherence=transfer.coherence[:,band]
    peak_indices=np.argmax(coherence,axis=1)
    freq=transfer.frequencies_hz[band]
    r2=audit["test_r2"]
    gain=audit["test_r2_above_wrong_audio_max"]
    success=(r2>THRESH_R2)&(gain>THRESH_GAIN)
    return {
        "channels":SELECTED,
        "r2":r2.tolist(),
        "wrong_audio_max_r2":audit["wrong_audio_max_test_r2"].tolist(),
        "r2_gain":gain.tolist(),
        "mean_r2":float(np.mean(r2)),
        "median_r2":float(np.median(r2)),
        "best_r2":float(np.max(r2)),
        "mean_coherence":float(np.mean(coherence)),
        "peak_coherence_max":float(np.max(coherence)),
        "peak_freq_hz_by_channel":freq[peak_indices].tolist(),
        "peak_coherence_by_channel":np.max(coherence,axis=1).tolist(),
        "mean_negative_lag_energy_fraction":float(np.mean(
            audit["negative_lag_energy_fraction"])),
        "passes_descriptive_audio_null":dict(zip(SELECTED,success.tolist())),
        "n_passing":int(success.sum()),
        "all_channels_r2_above_wrong_audio_mean":float(np.mean(gain)),
    }


def compare(raw,car):
    """Descriptive commonality only, not specific pickup source attribution."""
    before=float(raw["mean_r2"]);after=float(car["mean_r2"])
    attenuation=(before-after)/before if before>0 else None
    strong=(raw["n_passing"]>=8 and raw["mean_r2"]>.10
            and raw["all_channels_r2_above_wrong_audio_mean"]>.03)
    return {
        "raw_mean_r2":before,"car_mean_r2":after,
        "raw_to_car_drop_absolute":before-after,
        "raw_to_car_drop_fraction_if_positive":attenuation,
        "raw_mean_coherence":raw["mean_coherence"],
        "car_mean_coherence":car["mean_coherence"],
        "raw_passing":raw["n_passing"],"car_passing":car["n_passing"],
        "strong_raw_audio_coupling_descriptive":strong,
        "large_car_attenuation_descriptive":bool(strong and attenuation is not None
                                                and attenuation>.8),
    }


def one_run(selection,output):
    import mne
    url=selection["edf_url"]
    sidecar=channels_from_sidecar(selection["channels_tsv_url"])
    if not all(sidecar.get(k,{}).get("type")=="EEG" for k in CHANNELS):
        raise RuntimeError("Cannot safely compute CAR: BIDS 128 EEG identities differ")
    if "Speaking microphone" not in sidecar.get("EEG131",{}).get("description",""):
        raise RuntimeError("BIDS primary microphone identity not verified")
    with tempfile.TemporaryDirectory(prefix="har3_cross_") as folder:
        src=Path(folder)/"excerpt.edf"
        info=fetch_excerpt(src,url,start_seconds=0,duration_seconds=DURATION_S)
        raw=mne.io.read_raw_edf(str(src),preload=False,verbose="ERROR")
        try:
            fs=float(raw.info["sfreq"])
            if not np.isclose(fs,FS,atol=1e-2):
                raise RuntimeError(f"Expected 1200 Hz, received {fs}")
            if not set(CHANNELS+["EEG131"]).issubset(raw.ch_names):
                raise RuntimeError("EDF channels do not match BIDS sidecar")
            mic=raw.get_data(picks=["EEG131"])[0]
            grid=raw.get_data(picks=CHANNELS)
        finally:
            raw.close()
    if len(mic)<FS*32:
        raise RuntimeError("Shorter recording than minimum analysis window")
    if not np.all(np.isfinite(mic)) or not np.all(np.isfinite(grid)):
        raise RuntimeError("Non-finite instrument signals")
    if np.std(mic)<1e-11:
        raise RuntimeError("Microphone recording lacks sufficient detectable activity")
    base=grid[::8].copy()
    car=base-grid.mean(axis=0)[None,:]
    raw_result=score_monitor(mic,base,fs)
    car_result=score_monitor(mic,car,fs)
    results={
        "selection":selection,
        "status":"evaluated",
        "sample_rate_hz":fs,
        "microphone_sd":float(np.std(mic)),
        "microphone_rms":float(np.sqrt(np.mean(mic**2))),
        "mean_eeg_sd":float(np.mean(np.std(base,axis=1))),
        "mean_car_sd":float(np.mean(np.std(car,axis=1))),
        "raw":raw_result,"car":car_result,
        "comparison":compare(raw_result,car_result),
        "original_edf_record_count":info["original_records"],
        "download_bytes":info["excerpt_bytes"],
        "raw_excerpt_uploaded":False,
    }
    output.mkdir(parents=True,exist_ok=True)
    (output/(selection["stem"]+".json")).write_text(
         json.dumps(results,indent=2)+"\n",encoding="utf-8")
    return results


def summarize(selection,rows):
    ok=[r for r in rows if r["status"]=="evaluated"]
    fresh=[r for r in ok if r["selection"]["label"]=="fresh_subject"]
    def count(test,subset):return sum(bool(test(r)) for r in subset)
    return {
        "selected_runs":len(selection["runs"]),
        "evaluated_runs":len(ok),
        "failures":len(rows)-len(ok),
        "fresh_subjects_selected":selection["n_fresh_requested"],
        "fresh_subjects_evaluated":len(fresh),
        "strong_raw_fresh":count(
            lambda r:r["comparison"]["strong_raw_audio_coupling_descriptive"],fresh),
        "strong_raw_all":count(
            lambda r:r["comparison"]["strong_raw_audio_coupling_descriptive"],ok),
        "large_car_attenuation_among_strong_fresh":count(
            lambda r:r["comparison"]["large_car_attenuation_descriptive"],fresh),
        "descriptive_definition":"Strong raw = >=8/16 electrodes exceed 0.03 heldout R2 and 0.03 shifted-null advantage, plus mean R2>0.10 and mean R2 advantage >0.03. Large CAR suppression = >80% drop in mean R2 for strong raw runs.",
        "not_significance":"No corrected inferential p values; subjects/runs are observational and selected from the same acquisition family.",
    }


def plot(rows,output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ok=[r for r in rows if r["status"]=="evaluated"]
    if not ok:return
    names=[r["selection"]["stem"].split("_")[0] + "/" +
           r["selection"]["stem"].split("_")[-1] +
           (" (original)" if r["selection"]["label"]=="known_original" else
            " (previous negative)" if r["selection"]["label"]=="known_previous_negative" else "")
           for r in ok]
    xs=np.arange(len(ok))
    raw=np.asarray([r["comparison"]["raw_mean_r2"] for r in ok])
    car=np.asarray([r["comparison"]["car_mean_r2"] for r in ok])
    fig,axes=plt.subplots(2,1,figsize=(max(11,len(ok)*1.15),9),constrained_layout=True)
    w=.35
    axes[0].bar(xs-w/2,raw,width=w,label="Original reference")
    axes[0].bar(xs+w/2,car,width=w,label="128-electrode common average")
    axes[0].axhline(.10,color="gray",ls=":",label="Descriptive strong-raw mean-R² threshold")
    axes[0].set(ylabel="Mean held-out mic→EEG R²",
                title="HeadAsResonator3 — Cross-participant audio coupling")
    axes[0].legend()
    a=np.asarray([r["raw"]["n_passing"] for r in ok])
    b=np.asarray([r["car"]["n_passing"] for r in ok])
    axes[1].bar(xs-w/2,a,width=w,label="Original reference")
    axes[1].bar(xs+w/2,b,width=w,label="CAR")
    axes[1].set(ylim=(0,16.5),ylabel="Electrodes exceeding shifted-audio null (of 16)",
                xlabel="Metadata-selected public recordings")
    axes[1].set_xticks(xs)
    axes[1].set_xticklabels(names,rotation=40,ha="right")
    fig.savefig(output/"cross_subject_overview.png",dpi=140)
    plt.close(fig)


def run(n_fresh=8,out="results/real_gate_003"):
    output=Path(out);output.mkdir(parents=True,exist_ok=True)
    selected=choose_runs(read_index(),n_fresh=n_fresh)
    (output/"frozen_metadata_selection.json").write_text(
        json.dumps(selected,indent=2)+"\n",encoding="utf-8")
    rows=[]
    for i,s in enumerate(selected["runs"]):
        try:
            row=one_run(s,output)
            t=row["comparison"]
            print(f"RUN {i+1}/{len(selected['runs'])} {s['stem']}: "
                  f"RAW mean R2 {t['raw_mean_r2']:.4f}, "
                  f"CAR {t['car_mean_r2']:.4f}, "
                  f"pass {t['raw_passing']}/{t['car_passing']}, "
                  f"strong={t['strong_raw_audio_coupling_descriptive']}",
                  flush=True)
        except Exception as exc:
            row={"selection":s,"status":"failed","error":str(exc),
                 "warning":"No replacement selected; failure retained in denominator"}
            print(f"FAILED {s['stem']}: {type(exc).__name__}: {exc}",flush=True)
        rows.append(row)
        (output/"checkpoint.json").write_text(
            json.dumps({"selection":selected,"rows":rows},indent=2)+"\n",
            encoding="utf-8")
    summary=summarize(selected,rows)
    report={
        "experiment":"HeadAsResonator3 real Gate 003 cross-participant generalization",
        "dataset":"OpenNeuro ds007808/NEMAR on007808 v1.0.0",
        "selection":selected,
        "config":{"n_channels":16,"sample_rate_hz":1200,"seconds_per_run":35,
                  "band_hz":[50,500],"phase_preserved":True,
                  "microphone_input":"EEG131 same EDF sample clock",
                  "raw_and_car_reference":"all EEG001..EEG128 only, monitors excluded",
                  "wrong_audio_controls":3,"delay_search_ms":[-20,120],
                  "delay_step_ms":1,"no_cross_subject_retuning":True,
                  "no_raw_eeg_uploaded":True},
        "summary":summary,
        "rows":rows,
        "limits":[
            "Audio-related voltage patterns are not evidence of skull, cable, neuron or lip physical origins.",
            "The 8 new subjects use lexically earliest available full-rate speechopen recording, regardless of measured signal.",
            "Only one 35s interval per run, not a random or representative population sample.",
            "Original and previous-negative anchors were previously analyzed and must be reported separately.",
            "Initial 35s may include silence; an unexcited microphone cannot identify transfer.",
            "3 refitted shifted-audio controls and fixed thresholds are descriptive, not corrected p-values.",
            "CAR can cancel genuine widespread brain signals as well as measurement-chain artifacts.",
            "Source waveforms and target channels share a clock but can experience distinct analog filtering.",
            "No external intervention or independently verified physical vibration path."
        ]
    }
    (output/"GATE_003_summary.json").write_text(
        json.dumps(report,indent=2)+"\n",encoding="utf-8")
    plot(rows,output)
    print("SUMMARY",json.dumps(summary,sort_keys=True),flush=True)
    print("WROTE",output/"GATE_003_summary.json",flush=True)
    return report


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--fresh",type=int,default=8)
    p.add_argument("--out",default="results/real_gate_003")
    a=p.parse_args()
    run(a.fresh,a.out)
