# HeadAsResonator3 — Where did the voice enter the recording?

**A phase-preserving, multichannel audio-to-electrode transfer microscope with strict null controls.**

[HeadAsResonator](https://github.com/anttiluode/HeadAsResonator) recovered audible audio-related structure from high-rate electrophysiology. Its README reported **0.954 peak coherence at 440.6 Hz**. The original filter saved magnitude but not complex phase, and estimated a delay from smoothed envelopes. These observations alone cannot distinguish skull vibration, mechanical cable/electrode contamination, electrical pickup, muscles or neural activity.

This third project asks the next, stricter question: **Which temporal components are actually identifiable from simultaneous audio and EEG, and when must we refuse to label a physical route?**

## What is implemented

- **Complex phase-preserving H1 transfer:** estimate H(f)=Sxy/Sxx with Welch-averaged cross-spectra, retaining its real and imaginary parts, frequency-wise coherence, a power-support mask, and the signed, circular inverse-FFT response. Phase is not discarded.
- **All electrode channels:** process EEG-named channels (up to 128 by default), or explicitly named channels including auxiliary EMG/EOG/audio monitor if present. Save per-channel PNG, JSON, CSV and compressed NPZ results.
- **Sparse audio-to-EEG lag proposals:** training-only correlation chooses up to nine separated time shifts, including negative lags, and ridge regression fits their contributions. This is a conventional finite-impulse-response baseline inspired by Luotain2's proposal-and-kill-test discipline, not a novel IV theorem or an identified skull law.
- **Independent splits and wrong-audio kill tests:** contiguous train/validation/test splits, with their lag boundaries discarded; the complete search is independently refitted against three large, deliberately wrong audio shifts.
- **Negative-lag alarm:** a fitted response arriving before the supposed cause is treated as a possible clock/filter/model problem, never claimed as negative physical propagation.
- **Equal-response impossibility check:** two hypothetical physical paths with the same impulse response can be detected jointly but are impossible to disentangle by passive audio/electrode measurements alone.

Both recorded streams receive a shared **causal** bandpass. We avoid zero-phase forward-backward filtering because it can create acausal pre-ringing.

## November 22 — Real Gate 002: EMG versus voice, across independent time windows

[**Full real result and limitations**](REAL_RESULT_002.md) · [Successful 12-test workflow](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45033613324) · [Download all three window audits and JSON](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45033613324/artifacts/14758304528).

Using the exact high-rate original ds007808 EDF, we compared **three nonoverlapping windows** (0–35, 120–155, 240–275 seconds). The official channel sidecar identifies **EEG131/132 as speaking-microphone monitors, EEG135–138 as lip EMG, EEG133–134 as EOG, and EEG129–130 as listening monitor channels**. Every EEG output was common-average referenced against **128 EEG channels only**.

The three post-CAR survivor electrodes were **EEG065, EEG105, EEG113**; two passed the earlier shifted-audio threshold in both later time slices. **Mic and lip EMG together** improved EEG065 prediction in the first window (held-out R² 0.117 versus 0.050 microphone-only and 0.055 lip-only); the relative contribution varied across time and electrodes. Importantly, a **fixed microphone→CAR filter trained only in the first window** still predicted the later windows without refitting: for EEG065, R² **0.0443** and **0.0822**. Thus the residual audio-linked response is not confined to one fitted 35-second segment. It **cannot** uniquely be assigned to cable, electrode, skull, muscle, electronics or brain.

The full numerical groups, independent shifted-audio controls, and warnings are in REAL_RESULT_002.md. This is a real, reproducible input-output finding using standard linear signal processing, **not** causal separation of the physical paths.

## November 22 real-data results — the original voice signal is reproducible

[**Real Result 001: exact-run replication, negative comparison, reference ablation**](REAL_RESULT_001.md) · [Original-run complex-phase results](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45027375890) · [Reference-ablation results](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45027519355).

**Original experiment recording verified:** sub-03/ses-20240821/task-speechopen/acq-pangolin/run-02 in OpenNeuro ds007808. We used the **same 1200Hz EDF clock** for the BIDS-confirmed speaking-microphone monitor EEG131 and 16 predeclared genuine EEG channels. The strongest electrode (EEG121) had **0.9928 peak coherence**, **0.417 held-out R²** and **0.041 shifted-audio-null R²**. A different subject/run produced no positive held-out result.

**Key control:** subtracting the 128-electrode common average reduced mean audio-prediction R² across the 16 predeclared channels from **0.3875** to **0.0247** (93.6% reduction), mean 50–500Hz coherence from **0.6724** to **0.0947**, and channels outperforming shifted-audio controls from **16/16** to **3/16**. The dominant response is therefore strongly **spatially common**, but the current passive records cannot uniquely identify whether that is cable, electrode, amplifier, head vibration, or widespread biological activity. **No physical origin or neural wiring has been identified.** The follow-up reference test was motivated by the initial observation and is exploratory.

### Small remote recording slices—not giant downloads

The public NEMAR ds007808 Zarr index has 1,974 stores **all at 250Hz**, insufficient to examine the reported 440.6Hz peak. We verified HTTP byte-range support for original **1200Hz EDF** data and fetched only a short ~12MB excerpt of the specific public run. BIDS channels.tsv confirms EEG131/132 are speaking-mic monitor channels; EEG129/130 are listening monitor channels; EEG135–138 lip EMG. This means there is **no need for a personal EEG rig or full 1.54TB dataset download** to reproduce these analyses. Run the two commands under REAL_RESULT_001.md.

## Run a complete demonstration now — no EEG download

Python 3.10+, CPU only:

~~~bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m resonator3.cli --demo --out results/synthetic_demo
~~~

Open the generated overview.png, summary.json, channel_audit.csv, and transfer_complex.npz.

[**Successful GitHub Actions run**](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45026473284) passed nine synthetic checks and uploaded the complete figure/data artifact.

| Synthetic channel | Held-out R² | Fitted dominant lag |
|---|---:|---:|
| Two delays | 0.966 | +5.83 ms |
| Long delay | 0.911 | +70.83 ms |
| Two inseparable paths | 0.979 | +5.83 ms |
| Immediate pickup | 0.901 | 0 ms |
| Completely independent electrode | -0.001 | meaningless |

Wrong-audio controls scored around zero. **These results validate software on known synthetic responses, not a physical or EEG discovery.**

## Run on a real matching EDF and WAV

~~~bash
python -m pip install -e ".[eeg,dev]"
python -m resonator3.cli --edf "recording_eeg.edf" --wav "matching_audio.wav" --duration 35 --nperseg 4096 --pre-ms 20 --post-ms 120 --step-ms 1 --band 50 500 --out results/overt
~~~

The default 50–500 Hz acoustic band requires more than 1000 Hz sampling. It is appropriate for the reported 1200 Hz g.Pangolin recording and **not** for ordinary 160 Hz resting EEG.

Use --channels to select comma-separated EDF channel names, or --max-channels to limit memory. A verified known EDF/WAV clock offset may be supplied using --audio-offset-ms; no synchronization offset is silently estimated. If synchronization is unknown, absolute physical delays are also unknown.

Output: overview.png (complex phase, amplitude, coherence, signed impulse, scores and spatial lag map); transfer_complex.npz (the actual complex H, coefficients, input-power support); channel_audit.csv (one channel per row); summary.json (all numerical results and limitations).

## Find only the relevant OpenNeuro recordings

The original project README named ds007630; the independently documented expanded EEG-Speech Brain Decoding Dataset is [OpenNeuro ds007808](https://openneuro.org/datasets/ds007808) / [NEMAR on007808](https://nemar.org/dataset/on007808), with overt speech, listening and listening-followed-by-imagery tasks. Its earlier overt-only version is [ds007602](https://openneuro.org/datasets/ds007602). Always verify the actual downloaded subject/session/run and metadata.

A local matched pair should have:
- An EDF inside the participant/session/eeg directory, ending in _eeg.edf.
- A WAV inside the corresponding participant/session/beh directory, ending in _recording-vocal_beh.wav (overt) or _recording-audio_beh.wav (listening).

Inspect the local BIDS tree *without downloading anything*:

~~~bash
python scripts/bids_pairs.py --root "/data/ds007808"
~~~

Analyze up to three pairs already downloaded locally:

~~~bash
python scripts/bids_pairs.py --root "/data/ds007808" --run --limit 3 --duration 35 --out results/bids_audit
~~~

It matches subject, session, task, acquisition and run; mismatched filenames are excluded. Imagery task labels by themselves do **not** identify imagery-only samples: event timing must be parsed before making that comparison. The full ds007808 collection is roughly 1.54 TB; do not download it all for this pilot.

**No raw real EEG files are bundled or uploaded.** Real EEG/audio results are now reported in REAL_RESULT_001.md, with the original run independently reanalyzed using its BIDS-labelled speaking microphone monitor. The original 0.954 figure itself used a different input and estimator, so its precise peak-frequency correspondence remains unverified.

## Scientific restrictions

- Audio-related input-output prediction, even with strong coherence, **does not locate a physical path**. Cables, skull, electrode junctions, EMG, direct electrical crosstalk and auditory neural response can all carry correlated structure.
- Negative lags can arise from independent acquisition clocks. Acoustic frequencies with insufficient input power are unidentifiable. A Welch window yields a circular impulse response, not infinite-delay recovery.
- A narrow 440 Hz line can strongly establish common periodic energy while leaving impulse delay ambiguous.
- In overt speech, the microphone waveform is partly caused by motor activity and neural/muscular physiology also contributing to the electrodes. It cannot automatically be treated as an exogenous **instrumental variable**. This initial analysis intentionally uses sparse ridge, not mislabelled WAIVES inference.
- Three wrong-audio controls are an initial screen, not a corrected population-level significance test. Further verification needs trial shuffles, phase-preserving surrogate nulls, auxiliaries, robust clock synchronization, independent sessions and (for actual physical location) interventions or independent vibration measurements.
- No neural wiring, anatomical source reconstruction, or medical interpretation is implied.

**Goal of the next gate:** reproduce and dissect the original audio-electrode coupling on a verified matching high-rate real recording; preserve the complex transfer phase; compare overt production, listening and stimulus-free intervals only where event annotations exist; report which measured responses remain observationally indistinguishable.

Sources: [HeadAsResonator](https://github.com/anttiluode/HeadAsResonator), [HeadAsResonator2](https://github.com/anttiluode/HeadAsResonator2), [NEMAR ds007808](https://nemar.org/dataset/on007808). Welch transfer estimation, ridge FIR regression and wrong-audio controls are established signal-processing techniques, not new physics.
