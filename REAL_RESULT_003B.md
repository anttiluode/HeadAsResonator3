# Real Gate 003B — Does voice-related EEG pickup recur in independent recordings?

**November 22, 2026. Completed: 23/23 tests passed; 9/9 selected public high-rate EDF runs analyzed.**

[Successful workflow](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45036987578) · [Complete per-run receipts and figure](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45036987578/artifacts/14759684516) · [Compact numerical summary](results/REAL_RESULT_003B_summary.json) · [Frozen limited-scope protocol](REAL_GATE_003B_PROTOCOL.md).

## Why this is Gate 003B, not an eight-participant confirmation

The originally frozen [Gate 003](REAL_GATE_003_PROTOCOL.md) required eight **new** participants. Its workflow [failed its metadata eligibility check](https://github.com/anttiluode/HeadAsResonator3/actions/runs/45036719861): the published index exposes only **three** eligible full-rate Pangolin overt-speech participants, and two (sub-01 and sub-03) were already studied. There is **only one new participant**: sub-02.

We preserved that failure, declared this separate protocol, and selected the same metadata-defined first 35 seconds of **three runs per person**. The original sub-03 run-02 and previously weak sub-01 run-01 are marked known anchors; repeats of any subject are not independent people.

We did **not** change the signal filters, channel identities, train/validation/test fractions, shifted-audio controls, or descriptive thresholds from Gate 003.

## Fixed processing

- **Archive:** OpenNeuro ds007808 / NEMAR on007808 v1.0.0.
- **1200 Hz original EDF** via verified HTTP byte ranges, 35 seconds starting at 0 in each selected run.
- **Audio input:** BIDS-confirmed same-clock speaking microphone monitor EEG131.
- **Targets:** sixteen fixed electrode labels EEG001, EEG009, ..., EEG121; the 128-channel CAR is calculated from EEG001–EEG128 only, excluding mic/EMG/EOG/monitor channels.
- **Methods:** same causal 50–500 Hz filter, complex Welch cross-spectra, sparse lagged FIR with −20 to +120ms proposals, 60/20/20 temporal split and three re-fitted wrong-audio shifts.
- **Descriptive strong-run rule:** at least 8/16 electrodes separately outperform wrong audio by >0.03 R² and have held-out R²>0.03; mean raw-reference held-out R²>0.10 and mean advantage over shifted-audio controls >0.03. Large CAR attenuation = >80% of positive mean raw-reference R² removed. These thresholds are not multiple-comparison-adjusted significance tests.

No raw EEG was committed or included in the archived derived-results artifact.

## Results: nine recordings and two references

| Subject/run | Mean held-out R² original reference | Mean R² after CAR | Passing channels raw/CAR | Strong raw? | CAR reduction if strong |
|---|---:|---:|---:|---|---:|
| sub-01, 2023-08-29, run 01 (previous weak anchor) | +0.0009 | −0.0067 | 0 / 0 | No | — |
| sub-01, 2023-08-29, run 02 | −0.0042 | −0.0042 | 0 / 0 | No | — |
| sub-01, 2023-08-29, run 03 | −0.0626 | −0.0387 | 0 / 0 | No | — |
| **sub-02, 2025-05-22, run 01 (new participant)** | **+0.1892** | +0.0071 | **16 / 0** | **Yes** | **96.2%** |
| **sub-02, 2025-05-22, run 02** | **+0.2384** | +0.0170 | **16 / 4** | **Yes** | **92.9%** |
| **sub-02, 2025-05-22, run 03** | **+0.3494** | +0.0406 | **16 / 10** | **Yes** | **88.4%** |
| **sub-03, 2024-08-21, run 02 (original strong anchor)** | **+0.3875** | +0.0247 | **16 / 3** | **Yes** | **93.6%** |
| **sub-03, 2024-08-21, run 01** | **+0.3117** | +0.0161 | **15 / 1** | **Yes** | **94.8%** |
| sub-03, 2024-08-22, run 01 (another session) | +0.0435 | −0.0004 | **15 / 0** | No* | — |

*In the last run, 15 electrodes exceeded the descriptive shifted-audio channel threshold, but mean predictive R² was below the declared 0.10 strong-run threshold. The signal did **not** disappear; it was weaker by the stated multi-part condition.*

**Totals:** 5/9 strongly audio-linked recordings, from 2/3 participants; sub-02 (the only genuinely new participant) 3/3 strong, sub-03 2/3 strong, sub-01 0/3 strong. All 5 strongly linked recordings had >80% CAR attenuation; mean CAR reduction among them **93.18%**. **Do not report 5/9 as five independent participants.**

## What may explain differences, and what does not

The microphone monitor's measured standard deviation varied substantially:

| Participant | Microphone SD across the three first-35s runs (scaled EDF units) |
|---|---|
| sub-01 | 0.00353–0.00387 |
| sub-02 | 0.07867–0.09827 |
| sub-03 | 0.00689–0.04688 |

Differences in speaking activity, microphone gain, signal normalization or hardware noise can influence recoverability. In particular, all three sub-01 windows have very low microphone SD, so non-recovery may be a **low-excitation measurement** rather than evidence of absent transfer. However, microphone amplitude alone does not explain the results: sub-03's next-day window had higher microphone SD but much lower mean held-out R² than its original-day runs. The source-activity model remains to be tested with event-aligned trials and gain-matched comparisons.

The strongest individual **coherence frequency** from the new audit was about **437.1 Hz** in the original sub-03 run-02, near (but not the same as) the older HeadAsResonator report of **440.6 Hz** using a different microphone/estimator. The dominant coherence peaks **were not stable across participants/runs**: examples for sub-02 include ~475.2, 476.7 and 344.2 Hz. The experiment does not identify a universal 440 Hz anatomical resonator.

High coherence in one frequency bin is not itself enough for broadband predictive transfer: sub-03's next-day run reached strong peak coherence but only +0.0435 mean held-out raw R². Thus a single coherence peak should not be promoted to evidence of a stable physical path.

## Scientific conclusion and unresolved pathways

**Observed:** audio-specific electrode activity is independently reproducible in the genuinely new sub-02 participant and in an additional run of the previously investigated sub-03 participant. All strongly coupled runs share a substantial common-average-referenced component: **common-mode electrode voltage is a repeatable feature of certain recordings**. The sub-01 observations and later sub-03 session constrain any universality claim.

**Not observed or established:** a representative population prevalence, a universal 440 Hz resonance, a unique physical source or skull pathway, neuron-level coupling, speech decoding without audio calibration, or any medical property.

A 128-electrode spatial mean can subtract genuine distributed neuronal activity as well as common reference contamination, cable microphonics, amplified hardware pickup, facial EMG and head movement. A passive microphone/EEG input-output model and transfer delay do **not** uniquely label which material carried the sound.

**Next falsifiable control:** select speech-active intervals using independent public BIDS event timing before looking at electrode outputs; match input-audio excitation and test raw/CAR transfer across repeats and subjects, including an active-vs-silent input control. A gain-matched residual after CAR and lip-EMG controls would be a stronger result. No new hardware is needed.

## Reproduction

    python -m pip install -e ".[eeg,dev]"
    python -m pytest -q
    python -m scripts.real_gate_003b

The workflow artifact includes the frozen metadata manifest, per-run complex-phase-derived metrics, original/CAR summaries, microphone levels, shifted-audio null scores, checkpoint and the cross-run comparison chart.
