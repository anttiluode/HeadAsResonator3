# Real Gate 003 — Is the original common-mode speech pickup a population phenomenon?

**Method frozen before reading the new subjects' signal values.**

This is a cross-participant falsification test of HeadAsResonator3's observation that the original high-rate speech EEG run contains strong microphone-related electrode voltage, most of which disappears after 128-electrode common-average referencing.

## Frozen selection

Read only the public [NEMAR on007808 index](https://zarr.nemar.org/on007808/zarr/index.json). Require original full-rate EDF source rate >=1000 Hz, Pangolin acquisition and overt speech task. Include two *known anchors*, which will **not** count toward independent replication:

- Original strong sub-03/ses-20240821/speechopen/pangolin/run-02.
- Previously weak sub-01/ses-20230829/speechopen/pangolin/run-01. The previous negative result was on 60–100 seconds; this gate instead examines 0–35 seconds.

Then select **eight additional distinct subjects**, in ascending numerical subject order, excluding 01/03. For each, select the first lexical eligible run. Also select the first different recording of subject 03 if present, as a same-subject comparison only. **No replacements after failures or weak microphone signals.** Any input/channel metadata error or missing file remains a reported failure.

Selection code: [scripts/choose_cross_subject_runs.py](scripts/choose_cross_subject_runs.py).

## Frozen analysis

Fetch only **35 seconds from the start** of the original 1200 Hz EDF by HTTP byte-range. The same EDF sample clock contains the speaking microphone monitor EEG131 and 128 actual EEG channels. Require official BIDS channels.tsv identity for every channel. The EEG outputs are EEG001, EEG009, ..., EEG121 (16 fixed channels). Construct a second referenced version by subtracting the mean of all 128 EEG channels, **excluding** microphone, lip EMG, EOG and other monitors.

For both the original reference and common-average (CAR), apply exactly the same procedure as the previous real gate: causal 50–500 Hz bandpass to input/output; complex Welch H1/coherence over 4096 samples; train-only sparse FIR lags −20 to +120ms on a 1ms grid (up to nine taps); 60/20/20 temporal train/validation/test split with buffer; and three independently refitted wrong-audio circular shifts.

A channel **descriptively** passes if held-out R² >0.03 and its advantage over the strongest shifted-audio null is >0.03. A run is descriptively *strong* if at least eight of 16 channels pass, its mean R² >0.10, and mean advantage over the shifted-audio null >0.03. A *large* CAR attenuation is >80% disappearance of the positive raw-reference mean R² in a strong run. These thresholds were declared before examining the new recordings and are **not multiple-testing-adjusted significance statements**.

Record raw and CAR mean/median R², coherence, peak coherence and frequency, sensor-noise/excitation diagnostics (microphone SD), channel passing counts, mean differences, exact metadata and errors. Original and known negative are separately identified; the eight fresh participants form the independent set. No retuning based on outcomes.

## Kill conditions

If the original recording is strong but all eight new recordings are weak, report that the effect **did not generalize across these selected participants**. If raw coupling is common but CAR attenuation varies, report reference dependence and heterogeneity, not a universal skull law. If an input is nearly silent or a sidecar mismatches, keep the failure in the denominator instead of replacing the participant. A false positive in the synthetic common-mode control is grounds to halt.

The population is small, lexically selected and not necessarily representative. Early segments may have no overt speech, so absence of audio excitation also precludes identification. **Even perfect generalization cannot discriminate skull, wire, cable, amplifier, face muscles, or widespread brain activity from passive observations alone.** There is no clinical or patient-level inference.

## Reproduce

    python -m pip install -e ".[eeg,dev]"
    python -m pytest -q
    python -m scripts.real_gate_003 --fresh 8

Files: metadata selection, per-run scores, any errors, aggregate JSON and cross-subject comparison plot. Raw public EDF excerpts are temporary and not uploaded. [GitHub workflow](.github/workflows/real_gate_003.yml) records both successes and failures.
