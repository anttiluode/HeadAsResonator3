# Real Gate 002 — Post-reference speech residual, lip EMG, and independent time windows

**Date:** 22 November 2026. **Status:** completed real public-data experiment. All **15/15 automated tests** passed and all three 35-second public EEG windows were analyzed. This is observational electrical/acoustic measurement, *not* anatomical source separation or new biological physics.

[Successful complete workflow](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45033613324) · [Full derived per-channel results and three plots](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45033613324/artifacts/14758304528) · [Compact persistent JSON](results/REAL_RESULT_002_summary.json) · [Reproducible code](scripts/real_gate_002.py) · [Fixed-lag model](resonator3/conditional.py).

## Dataset and prespecified inputs

Use the original HeadAsResonator data: [OpenNeuro ds007808 / NEMAR on007808](https://nemar.org/dataset/on007808), exact **sub-03/ses-20240821/task-speechopen/acq-pangolin/run-02**, original **1200 Hz** EDF with microphone monitors on the *same sample clock*.

Three fixed, non-overlapping intervals from the same run:

- **0–35 s**, previously examined and used for discovery/first calibration;
- **120–155 s**, independent later time slice;
- **240–275 s**, second independent later time slice.

The latter two were set before the new control was run. **They are not independent participants or randomized experimental conditions.**

The official BIDS channels.tsv confirms:

| Original EDF labels | Physical measurement described in sidecar |
|---|---|
| EEG001–EEG128 | 128 g.Pangolin EEG grid electrodes |
| EEG129 / EEG130 | Listening audio monitor channels 1 and 2 |
| EEG131 / EEG132 | Speaking microphone monitor channels 1 and 2 |
| EEG133 / EEG134 | EOG, positive and negative |
| EEG135 / EEG136 | Upper-lip EMG, positive and negative |
| EEG137 / EEG138 | Lower-lip EMG, positive and negative |

This experiment uses EEG131 as the primary microphone waveform, computes two bipolar lip EMG differences (135−136 and 137−138), and also tests EEG132, the two listening monitor channels, and bipolar EOG. The 16 original probe electrodes **EEG001, 009, …, 121** were kept fixed. Each output was re-referenced against the mean of **all 128 EEG channels**; no monitor or EMG went into the reference.

All sources and targets used the same causal 50–500 Hz filter. A dedicated fixed-lag ridge comparison uses seven signed lags: **−8, −4, 0, +4, +8, +16, +32 ms**. It holds time indices, training-only normalization, and regularization rules consistent across source groups. Groups were: speaking monitor alone, its second channel alone, lip EMG alone, microphone + both lip EMG, deliberately shifted microphone alone, shifted microphone + lip EMG, EOG, and listening monitors.

## A. Which post-CAR electrodes survive?

The original 0–35s window (also used in Gate 001) yielded precisely **EEG065, EEG105, EEG113** above the established descriptive wrong-audio threshold. Checking these *postselected* IDs in later windows:

| CAR electrode | 0–35s held-out audio R² | 120–155s held-out audio R² | 240–275s held-out audio R² |
|---|---:|---:|---:|
| EEG065 | 0.2185 | 0.0551 | 0.0580 |
| EEG105 | 0.0527 | 0.0428 | 0.0333 |
| EEG113 | 0.0313 | 0.0173 | 0.0178 |

The count above the original shifted-audio criterion was **3/16, 2/16, 2/16** respectively. Only EEG065 and EEG105 passed in both later windows. Average CAR audio-to-output held-out R² across all 16 electrodes decreased from **0.0247** to **0.0104** and **0.0097**.

These are within-window *refitted* models; the next test specifically removes that flexibility.

## B. Freeze the first model; does it transfer to other times?

We trained the existing nine-candidate sparse microphone-to-electrode FIR **only on the first 60% of window 0**. Its coefficients and intercept were then frozen, with the same audio lag grid and causal filtering. They were evaluated directly on the full 120–155s and 240–275s windows, **without new fitting, per-window centering or target normalization**.

| Original survivor | Frozen first-window FIR → 120–155s | Frozen first-window FIR → 240–275s |
|---|---:|---:|
| EEG065 | **0.0443** | **0.0822** |
| EEG105 | **0.0289** | **0.0369** |
| EEG113 | **0.0118** | **0.0144** |

All six scores are positive. **A measurable audio-to-CAR linear response learned in the first interval transfers to two later intervals of this same recording.** That is more stringent than re-fitting the model in each window. Yet it does not tell us whether the route is mechanical, electric, muscular, or neuronal. Same-session time transfer is not across-subject replication.

## C. Lip EMG adds predictive information, but not consistently

A separate *fixed seven-lag ridge model* tested microphone alone, upper/lower lip EMG alone, and both together. Held-out R² for the three window-0 survivors:

| Window | Electrode | Mic only | Lip EMG only | Mic + lip EMG |
|---|---|---:|---:|---:|
| 0–35s | EEG065 | 0.0495 | 0.0549 | **0.1170** |
| 120–155s | EEG065 | 0.0068 | 0.0067 | 0.0127 |
| 240–275s | EEG065 | 0.0038 | **0.0337** | 0.0322 |
| 0–35s | EEG105 | 0.0390 | 0.0338 | **0.0505** |
| 120–155s | EEG105 | 0.0271 | 0.0068 | **0.0288** |
| 240–275s | EEG105 | 0.0319 | 0.0351 | **0.0455** |
| 0–35s | EEG113 | 0.0277 | 0.0134 | 0.0291 |
| 120–155s | EEG113 | 0.0118 | 0.0008 | 0.0118 |
| 240–275s | EEG113 | 0.0176 | 0.0113 | 0.0179 |

On **EEG065 in the first window**, microphone and lip EMG are meaningfully complementary for prediction (0.117 combined versus 0.0495 mic and 0.0549 lip alone), and replacing the true mic with shifted mic plus lip reduced R² to about **0.0552**. On that channel in the last window, microphone adds **no gain** over lip EMG alone (0.0322 versus 0.0337). EEG105 retains modest microphone information in later windows. There is **no uniform, stable EMG-vs-microphone dominance**.

The listening-monitor and EOG channels were **not silent**; both yielded finite model scores, including mean EOG-only R² around 0.022–0.026 in the two later windows, and listening-monitor-only mean R² around 0.009–0.010. They must be treated as **measured auxiliary electrical signals**, not clean independent negative controls. Their activity could reflect real stimulation or shared recording-chain effects and cannot be classified without trial events and hardware information.

## D. What can be claimed?

**Positive result:** the previously reported loud, largely common-mode speech-related signal contains a much smaller but *time-transferable* residual after common-average referencing. Two of the three initially selected electrodes remain above the earlier descriptive null threshold in both later windows. Lip EMG supplies some predictive information, particularly for EEG065 in certain windows, and the first-window microphone mapping generalizes without refitting.

**Not identifiable:** whether the residual comes from the skull as an acoustic resonator, lip/face muscles coupled to electrodes, cable/connector microphonics, ground/amplifier pickup, mechanical electrode interfaces, distributed neural responses, or combinations. Microphone and lip EMG both track the underlying act of speaking. Conditional predictability **is not causal mediation**. Even phase-stable, multi-window response cannot uniquely identify two physical paths with the same temporal filter.

Other limitations: one participant/session, fixed electrode subset chosen before this test, survivors postselected on the first interval, no separate true sham recording or hardware manipulation, uncorrected three-shift exploratory null, fixed linear lag bases only, and all sensors share an instrument and acquisition clock but can have distinct analog circuit delays. Not a medical investigation.

## Reproduce without personal recording equipment

The pipeline downloads three ~12MB high-rate public EDF excerpts through verified HTTP Range, consults official BIDS channel types and retains only derived summaries/plots. No raw signal is uploaded as a workflow artifact.

Install then run:

    python -m pip install -e ".[eeg,dev]"
    python -m pytest -q
    python -m scripts.real_gate_002

The complete JSON is **GATE_002_summary.json** in the workflow artifact, along with three overview.png, channel_audit.csv, summary.json and complex transfer NPZ outputs. Source [scripts/real_gate_002.py](scripts/real_gate_002.py); [workflow](.github/workflows/real_gate_002.yml); [public source and receiver attribution](REAL_RESULT_001.md).

**Best next external falsification:** compare identical analysis across separate *sessions or participants*, with task/event-defined listening vs speaking and more than one reference montage, while avoiding any physical-path label until independent interventions are available.
