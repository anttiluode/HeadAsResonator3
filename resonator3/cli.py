#!/usr/bin/env python
"""HeadAsResonator3 CLI.

Usage:
  python -m resonator3.cli --demo --out results/demo
  python -m resonator3.cli --edf path/to/_eeg.edf \
    --wav path/to/_recording-vocal_beh.wav --duration 40 --out results/real
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
from fractions import Fraction

import numpy as np
from scipy import signal
from .core import complex_transfer, lag_audit, synthesize


def _select_auto_channels(edf, raw, max_channels):
    """Avoid mistaking EDF microphone/EMG monitors for EEG electrodes.

    BIDS channel type from the actual companion channels.tsv is authoritative.
    Without it, refuse ambiguous Pangolin-style 128 EEG + generic EEG###
    auxiliary labels, rather than silently treating the microphone as brain.
    """
    p=Path(edf)
    sidecar=(p.with_name(p.name[:-8]+"_channels.tsv")
             if p.name.endswith("_eeg.edf") else None)
    if sidecar is not None and sidecar.is_file():
        with sidecar.open("r",encoding="utf-8-sig",newline="") as handle:
            rows=list(csv.DictReader(handle,delimiter="\t"))
        by_type={r.get("name"):r.get("type","").upper() for r in rows}
        choices=[name for name in raw.ch_names
                 if by_type.get(name) in ("EEG","ECOG","SEEG")]
        if not choices:
            raise ValueError("No BIDS EEG/ECOG/SEEG channel labels in "+str(sidecar))
        return choices[:max_channels]
    # Fallback MNE typing is safe only when labels are not ambiguous.
    if "EEG128" in raw.ch_names and any(
        f"EEG{i:03d}" in raw.ch_names for i in (129,130,131,132,135,139)):
        raise ValueError(
            "EDF has generic EEG129+ labels that could be microphone, EMG or EOG. "
            "Supply the companion BIDS channels.tsv or explicit --channels; "
            "automatic classification is not safe.")
    declared=raw.get_channel_types()
    bad_words=("EOG","EMG","ECG","EKG","MIC","AUDIO","TRIG","AUX")
    choices=[name for name,typ in zip(raw.ch_names,declared)
             if typ.lower() in ("eeg","ecog","seeg") and
             not any(word in name.upper() for word in bad_words)]
    return choices[:max_channels]


def _read_pair(edf, wav, duration, channels, max_channels, audio_offset_ms):
    try:
        import mne
        import soundfile as sf
    except ImportError as e:
        raise RuntimeError("Install mne and soundfile for EDF/WAV: pip install -e '.[eeg]'") from e
    if not Path(edf).is_file() or not Path(wav).is_file():
        raise FileNotFoundError("Both an existing EDF and matching WAV must be supplied")
    raw=mne.io.read_raw_edf(str(edf),preload=False,verbose="ERROR")
    fs=float(raw.info["sfreq"])
    if fs<150:
        raise ValueError("Sampling frequency too low for 50–500 Hz acoustic pickup")
    if channels:
        names=[c.strip() for c in channels.split(",") if c.strip()]
        unknown=[c for c in names if c not in raw.ch_names]
        if unknown:
            raise ValueError("EDF does not contain: "+str(unknown)+"\nAvailable: "+str(raw.ch_names[:30]))
    else:
        names=_select_auto_channels(edf,raw,max_channels)
    if not names:
        raise ValueError("No EEG channels identified. Pass --channels explicitly")
    n=int(fs*duration) if duration>0 else raw.n_times
    n=min(n,raw.n_times)
    Y=raw.get_data(picks=names,start=0,stop=n)
    raw.close()
    with sf.SoundFile(str(wav)) as f:
        fs_audio=f.samplerate
        frames=int(duration*fs_audio)+int(abs(audio_offset_ms)*fs_audio/1000)+4 if duration>0 else -1
        x=f.read(frames=frames,always_2d=True).mean(axis=1)
    if fs_audio!=fs:
        ratio=Fraction(fs/fs_audio).limit_denominator(100000)
        x=signal.resample_poly(x,ratio.numerator,ratio.denominator)
    offset=int(round(audio_offset_ms*fs/1000))
    # Positive offset: discard this many initial electrode samples and
    # the same number of final audio samples. Negative: opposite.
    if abs(offset)>=min(Y.shape[1],len(x)):
        raise ValueError("Audio offset larger than available recording")
    if offset>0:
        Y=Y[:,offset:]
    elif offset<0:
        x=x[-offset:]
    n=min(Y.shape[1],len(x))
    if n<5000:
        raise ValueError("Paired recording is too short")
    return x[:n],Y[:,:n],names,fs


def _filter_pair(x,Y,fs,low,high):
    if low is None or high is None:
        return x,Y
    if not 0<low<high<fs/2:
        raise ValueError(f"Band [{low}, {high}] must fit strictly within Nyquist {fs/2}")
    # Forward (causal) filtering, not filtfilt: the latter creates
    # pre-ringing that could be mistaken for negative propagation time.
    sos=signal.butter(3,[low,high],fs=fs,btype="band",output="sos")
    return signal.sosfilt(sos,x),signal.sosfilt(sos,Y,axis=-1)


def _plot(out,names,trans,audit,fs,max_freq=500):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    f=trans.frequencies_hz
    passband=(f>0)&(f<max_freq)
    fig,axes=plt.subplots(3,2,figsize=(14,12),constrained_layout=True)
    j=int(np.argmax(audit["test_r2"]))
    H=trans.H_complex[j]
    axes[0,0].plot(f[passband],np.abs(H[passband]))
    axes[0,0].set(xlabel="Hz",ylabel="|EEG/audio|",title=f"Complex H magnitude: {names[j]}")
    axes[0,1].plot(f[passband],np.angle(H[passband]))
    axes[0,1].set(xlabel="Hz",ylabel="Phase (radians; wrapped)",title="Measured complex phase (not discarded)")
    axes[1,0].plot(f[passband],trans.coherence[j,passband])
    axes[1,0].set(xlabel="Hz",ylabel="Magnitude-squared coherence",ylim=(0,1),title="Frequency-specific dependence")
    laglim=max(120,float(abs(trans.impulse_lags_ms).max()/12))
    usable=np.abs(trans.impulse_lags_ms)<=laglim
    axes[1,1].plot(trans.impulse_lags_ms[usable],trans.impulse_response[j,usable])
    axes[1,1].axvline(0,color="gray",linewidth=.7)
    axes[1,1].set(xlabel="Signed lag (ms)",ylabel="Circular estimated response",title="Phase-derived impulse: not a physical location")
    ix=np.arange(len(names))
    axes[2,0].bar(ix,audit["test_r2"],label="Matched audio")
    if len(audit["wrong_audio_test_r2"]):
        axes[2,0].scatter(ix,audit["wrong_audio_max_test_r2"],c="red",marker="x",s=22,label="Best wrong-audio control")
    axes[2,0].set(xlabel="Channel index",ylabel="Held-out R²",title="Honest trial mismatch control")
    axes[2,0].legend(loc="best")
    axes[2,1].scatter(ix,audit["dominant_lag_ms"],c=audit["test_r2"],cmap="coolwarm")
    axes[2,1].axhline(0,color="gray",linewidth=.7)
    axes[2,1].set(xlabel="Channel index",ylabel="Dominant fitted lag (ms)",title="Unassigned delay evidence, not skull/cable/brain")
    fig.suptitle("HeadAsResonator3: input-output audit — unknown synchronization remains a confound")
    fig.savefig(out/"overview.png",dpi=140)
    plt.close(fig)


def analyze(x,Y,names,fs,out,*,band=(50,500),nperseg=4096,
            pre_ms=20,post_ms=120,step_ms=2,wrong_audio_shifts=3,
            dataset_meta=None):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(Y)):
        raise ValueError("Non-finite recording values")
    if Y.shape[1]!=x.size or len(names)!=Y.shape[0]:
        raise ValueError("Misaligned channels/audio")
    if band:
        band=(float(band[0]),min(float(band[1]),fs*.48))
    xf,yf=_filter_pair(x,Y,fs,*band) if band else (x,Y)
    transfer=complex_transfer(xf,yf,fs,nperseg=nperseg)
    audit=lag_audit(xf,yf,fs,negative_ms=pre_ms,positive_ms=post_ms,
                    step_ms=step_ms,wrong_audio_shifts=wrong_audio_shifts)
    freq_mask=(transfer.frequencies_hz>=band[0])&(transfer.frequencies_hz<=band[1]) if band else transfer.frequencies_hz>0
    coh_mean=np.mean(transfer.coherence[:,freq_mask],axis=1)
    coh_peak=np.max(transfer.coherence[:,freq_mask],axis=1)
    audio_excited_fraction=float(np.mean(transfer.identifiable_mask[freq_mask]))
    score=[]
    for j,name in enumerate(names):
        row={
          "channel":name,
          "coherence_mean_in_band":float(coh_mean[j]),
          "coherence_peak_in_band":float(coh_peak[j]),
          "validation_r2":float(audit["validation_r2"][j]),
          "heldout_r2":float(audit["test_r2"][j]),
          "wrong_audio_best_r2":float(audit["wrong_audio_max_test_r2"][j]),
          "r2_above_wrong_audio":float(audit["test_r2_above_wrong_audio_max"][j]),
          "dominant_lag_ms":float(audit["dominant_lag_ms"][j]),
          "negative_lag_energy_fraction":float(audit["negative_lag_energy_fraction"][j]),
          "selected_lags_ms":[round(k/fs*1000,3) for k in audit["selected_lags_samples"][j]],
        }
        # A descriptive calibration, NOT a p-value or neural classifier.
        row["above_shifted_audio_controls"]=bool(
            row["r2_above_wrong_audio"]>0.03 and row["heldout_r2"]>0.03)
        score.append(row)
    np.savez_compressed(out/"transfer_complex.npz",
        fs=fs,names=np.asarray(names),frequencies_hz=transfer.frequencies_hz,
        H_complex=transfer.H_complex,coherence=transfer.coherence,
        excited_mask=transfer.identifiable_mask,
        input_power=transfer.input_power,
        impulse_lags_ms=transfer.impulse_lags_ms,
        impulse_response=transfer.impulse_response,
        candidates_lag_samples=audit["lags_samples"],
        sparse_coefficients=audit["coefficients"],
        matched_r2=audit["test_r2"],
        wrong_audio_r2=audit["wrong_audio_test_r2"])
    with (out/"channel_audit.csv").open("w",newline="",encoding="utf-8") as fh:
        writer=csv.DictWriter(fh,fieldnames=list(score[0]))
        writer.writeheader();writer.writerows(score)
    summary={
      "software":"HeadAsResonator3", "method":"phase-preserving H1 + independently held-out sparse FIR lag audit",
      "sample_rate_hz":float(fs),"duration_seconds":float(len(x)/fs),
      "channels":len(names),"band_hz":band,
      "lag_window_ms":[-pre_ms,post_ms],"lag_step_ms":step_ms,
      "wrong_audio_shifts":wrong_audio_shifts,
      "audio_input_excited_spectral_fraction":audio_excited_fraction,
      "rows":score,
      "source":dataset_meta or {"type":"unspecified paired local audio/electrodes"},
      "warnings":[
        "Clock offsets between EDF and WAV may be unknown: fitted delay is not absolute physical latency.",
        "Sensor-space amplitude/phase and lag do not identify cable vs skull vs electrode vs brain.",
        "Zero-phase filtering was avoided; common causal bandpass was applied to audio and EEG.",
        "No source localisation, anatomical connectivity or medical conclusion.",
        "H1 assumes a stationary linear response and exogenous observed audio; correlated noise/feedback can bias it.",
        "Circular phase-derived impulse can wrap: lags beyond half nperseg are not unambiguous.",
        "Selected-lag R2 versus three shifted-audio controls is descriptive, not a corrected significance test.",
        "The audio-monitor channel, EOG, EMG and event markers should be audited separately before mechanism claims."
      ]
    }
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    _plot(out,names,transfer,audit,fs,max_freq=band[1] if band else fs/2)
    return summary


def main():
    parser=argparse.ArgumentParser(description="Multichannel phase-preserving speech/EEG transfer audit")
    parser.add_argument("--demo",action="store_true",help="Synthetic known-lag control with an unidentifiable two-path channel")
    parser.add_argument("--edf",help="Local high-rate EEG EDF file")
    parser.add_argument("--wav",help="Matching synchronized microphone or monitored audio WAV")
    parser.add_argument("--channels",help="Comma-separated EDF electrode names; default all EEG")
    parser.add_argument("--max-channels",type=int,default=128)
    parser.add_argument("--duration",type=float,default=35)
    parser.add_argument("--audio-offset-ms",type=float,default=0,help="Metadata-based offset; not an estimated source delay")
    parser.add_argument("--band",nargs=2,type=float,default=(50.,500.),metavar=("LOW","HIGH"),
                        help="Passband Hz, filtered causally on both signals")
    parser.add_argument("--nperseg",type=int,default=4096)
    parser.add_argument("--pre-ms",type=float,default=20)
    parser.add_argument("--post-ms",type=float,default=120)
    parser.add_argument("--step-ms",type=float,default=1)
    parser.add_argument("--wrong-audio-shifts",type=int,default=3)
    parser.add_argument("--out",default="results/headasresonator3")
    a=parser.parse_args()
    if a.demo:
        x,Y,names,truth,fs=synthesize()
        metadata={"type":"synthetic","known_delays_samples":truth,
                  "warning":"two different physical sources may share the same impulse; source attribution impossible"}
    else:
        if not a.edf or not a.wav:
            parser.error("provide --edf and --wav together, or --demo")
        x,Y,names,fs=_read_pair(a.edf,a.wav,a.duration,
                                a.channels,a.max_channels,a.audio_offset_ms)
        metadata={"type":"real paired EDF/WAV","edf":str(a.edf),"wav":str(a.wav),
                  "offset_ms":a.audio_offset_ms,
                  "warning":"assumed recording synchronization; offset is not resolved by this analysis"}
    summary=analyze(x,Y,names,fs,a.out,band=a.band,nperseg=a.nperseg,
                    pre_ms=a.pre_ms,post_ms=a.post_ms,step_ms=a.step_ms,
                    wrong_audio_shifts=a.wrong_audio_shifts,
                    dataset_meta=metadata)
    print("Wrote",a.out,"channels",summary["channels"])
    for r in sorted(summary["rows"],key=lambda r:r["heldout_r2"],reverse=True)[:12]:
        print(f"  {r['channel']:25} heldout R2={r['heldout_r2']:+.3f}"
              f" wrong={r['wrong_audio_best_r2']:+.3f}"
              f" lag={r['dominant_lag_ms']:+.2f}ms "
              f"gain={r['r2_above_wrong_audio']:+.3f}")


if __name__=="__main__":
    main()
