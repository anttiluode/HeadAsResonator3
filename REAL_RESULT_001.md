# Real Gate 001 — Voice-related common-mode structure in high-rate EEG

**Date:** 2026-11-22. **Status:** real public-data analysis; independent physical pathway **not identified**.

## Dataset and timing

Dataset: [OpenNeuro ds007808](https://openneuro.org/datasets/ds007808) / [NEMAR on007808 v1.0.0](https://nemar.org/dataset/on007808).

- Original HeadAsResonator README run: **sub-03 / ses-20240821 / task-speechopen / acq-pangolin / run-02**, first **35 seconds**, **1200 Hz**.
- Microphone source: BIDS `channels.tsv` declares **EEG131 = speaking microphone monitor channel 1**, recorded inside the same EDF and sampling clock as the EEG electrodes.
- Targets: predeclared 16 channels **EEG001, EEG009, … EEG121**, all declared EEG in the channel sidecar.
- EEG signal: first 35s reconstructed from **HTTP Range reads of the actual full-rate EDF**, not the NEMAR display Zarr. The official display Zarr index contains 1974 stores **all at 250 Hz**, which cannot reproduce a 440.6 Hz spectral feature. No raw human EEG is committed or retained in the derived-artifact upload.
- Test: 50–500 Hz causal bandpass applied to both audio and EEG, training-only sparse FIR delay selection, separate validation/test blocks and 3 refitted shifted-audio nulls. Complex phase and cross-spectra saved in the derived NPZ.

**Full-rate EDF location:** `sub-03/ses-20240821/eeg/sub-03_ses-20240821_task-speechopen_acq-pangolin_run-02_eeg.edf`.

## A. The original speech-electrode coupling is present

[Successful exact-run CI](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45027375890) · [Derived plots, complex transfer, scores and full CSV](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45027375890/artifacts/14756322094).

| Quantity | Strongest predeclared electrode (EEG121) |
|---|---:|
| Peak coherence in 50–500 Hz | **0.992756** |
| Mean coherence in 50–500 Hz | **0.768661** |
| Held-out microphone→electrode R² | **0.417362** |
| Best refitted wrong-audio held-out R² | **0.041148** |
| Difference in R² above best shifted audio | **0.376214** |
| Dominant fitted relative lag | **0.0 ms** |
| Negative-lag fitted coefficient energy | **0.12857** |

Many electrodes selected nearly the same delay pattern: 0, -4.167, +5.833, +15.833, -14.167, +26.667, +94.167 and +114.167 ms. **The relative audio-monitor lag is not a physical material or propagation delay.** Hardware filtering/clock timing and channel mixing may cause both negative and positive lag components.

The first HeadAsResonator README reported **0.954 coherence at 440.6 Hz**. The new complex-H1 test **confirms strong acoustic-related structure on exactly the original EDF run**, but does **not** yet establish that its maximum occurred at the identical frequency: the new report currently records peak value and spectrum arrays, not a peak-frequency summary. Original code used a different audio file/estimator.

## B. A different session was a negative control

[Early-run real EEG workflow](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45027195951) · [Derived data](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45027195951/artifacts/14756391572).

- Distinct **sub-01 / ses-20230829 / speechopen / acq-pangolin / run-01**, 60–100 seconds, same 1200 Hz acquisition type and microphone-monitor analysis.
- All 16 evaluated electrodes had **negative held-out R²**; the maximum was **−0.00095**, mean 50–500 Hz coherence for that electrode **~0.0287**, peak coherence **~0.279**.
- Therefore strong speech pickup is **not universal** across the dataset/time slices. One negative excerpt does not disprove original high coherence.

## C. Common-average referencing changes the answer enormously

**Exploratory follow-up** designed after seeing shared-looking responses in the original-run output; not a preregistered independent study.

[Successful reference-ablation CI](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45027519355) · [Raw-vs-CAR plots and numerical archive](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45027519355/artifacts/14756825002).

Reconstruct the exact original first 35s again. For each selected EEG electrode, subtract the mean of **all 128 true EEG electrodes** at each sample; *microphone monitor EEG131 is excluded from the spatial mean*. Re-run identical phase/lag algorithm on raw and referenced electrode signals:

| Measurement | Raw EDF reference | 128-electrode common-average |
|---|---:|---:|
| Mean held-out microphone→electrode R² | **0.387526** | **0.024717** |
| Median held-out R² | 0.394072 | 0.010774 |
| Maximum held-out R² | 0.417362 | 0.218485 |
| Mean 50–500 Hz coherence | 0.672386 | 0.094694 |
| Mean maximum coherence | 0.981982 | 0.497933 |
| Channels above shifted-audio controls | **16/16** | **3/16** |

The mean held-out R² **fell by ~93.6%** (0.387526 → 0.024717); its mean coherence fell by ~85.9%. This strongly suggests the dominant audio-related signal is a **spatially common component** of the original electrode voltages.

However, CAR is an *algebraic cancellation*, not a randomized hardware intervention. It can remove true spatially distributed biological signals as well as common-reference pickup, motion, cable microphonics or amplifier/ground artifacts. Three channels still retain some audio dependence. **This analysis cannot uniquely attribute a signal to skull, cables, electrode interface, electronics, muscles or neurons.**

## D. What exactly is known—and what would falsify it?

**Established by these records:** (1) strong audio-linked electrophysiology in the exact previously cited run, (2) that structure generalizes temporally within the run better than the three refitted wrong-audio models, (3) it is mainly spatially shared over the 128-electrode grid under common-average subtraction, and (4) this result is not universally present on every analyzed participant/time window.

**Not established:** anatomical localization, an absolute positive or negative sound propagation time, recovered speech content independent of microphone calibration, a unique mechanism of acoustic pickup, brain stem/cortical origin, or formal statistical significance over many independent runs.

The next real-world controls are **same-session independent windows/runs**; task-specific listening versus overt speech with event timing; channel types from the official BIDS sidecar; common-reference, bipolar and Laplacian alternatives; EOG/EMG/audio-monitor comparisons; robust clock-offset sensitivity; and spectrum-preserving phase surrogates. If two candidate physical pathways remain observationally equivalent, output **not identifiable** rather than an anatomical story.

## Reproducibility

    python -m pip install -e ".[eeg,dev]"
    python -m pytest -q
    python scripts/real_nemar_excerpt.py --which original --start 0 --duration 35 --out results/real_original_sub03
    python -m scripts.reference_ablation

**No original user recording is required.** Both data pipelines read a small slice of a verified public high-rate EDF over HTTP Range. The temporary raw EDF excerpt is discarded after analysis and excluded from GitHub artifacts.
