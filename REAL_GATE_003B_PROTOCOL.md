# Gate 003B — Three-subject repeated-run replication

**New, limited-scope protocol.** It was declared because Gate 003's
eight-new-participant eligibility check failed: the eligible high-rate
OpenNeuro/NEMAR speech index contains only **three people**, of whom
sub-01 and sub-03 were already examined. There is exactly **one** new
participant, sub-02. This Gate **does not replace or retroactively pass**
Gate 003, which remains an informative failed enrollment protocol.

## Frozen metadata-only selection

Select participants 01, 02, 03 and up to **three** original 1200Hz
task-speechopen acq-pangolin EDF runs for each. The previously examined
sub-01 run-01 and sub-03 run-02 are mandatory anchors; fill the rest
using the lexically earliest other runs, independent of signal strength.
For subject 02 choose the first three in lexical order. Run order and
selection are fixed by [choose_run_replicates.py](scripts/choose_run_replicates.py).
If fewer than three runs exist for a subject, retain the smaller available
sample: no fabricated or substituted data. Any run which fails metadata,
sampling, audio excitation or download tests is counted as a failure,
not replaced.

Only one recording per subject is a between-person comparison; other
recordings within subject are **not independent participants**.

## Unchanged measurement and thresholds from Gate 003

Use exactly the [Gate 003 scoring code](scripts/real_gate_003.py),
without changing its lags, filters, channel subset, reference, 60/20/20
time split, three wrong-audio refits, or descriptive thresholds:

- 35 seconds from the start of each original, byte-range-fetched
  1200Hz EDF.
- BIDS-verified speaking microphone EEG131 and real EEG001–EEG128,
  selecting outputs EEG001, EEG009, ... EEG121.
- Compare original reference vs 128-channel EEG common average (CAR)
  computed **without monitor or auxiliary channels**.
- Causal 50–500Hz bandpass, complex H1/coherence, FIR lag search
  −20 to +120ms in 1ms steps; three refitted wrong-audio controls.
- A channel passes descriptively if test R²>0.03 and advantage over
  strongest wrong-audio null >0.03.
- A recording is strongly audio-linked if >=8/16 channels pass,
  mean test R²>0.10 and mean advantage >0.03; large CAR suppression
  means a >80% drop in positive mean R².

Report per-recording, per-subject and anchor-vs-new comparisons.
Absence of an overt speech event in the first 35s may make excitation
insufficient, so an absent response is **not proof of missing physics**.
This study is limited to three public subjects (one new) and observational
microphone/electrode measurements. It cannot identify skull versus cable
versus electrode versus neural sources.

## Code and runtime

    python -m pip install -e ".[eeg,dev]"
    python -m pytest -q
    python -m scripts.real_gate_003b

Workflow: [.github/workflows/real_gate_003b.yml](.github/workflows/real_gate_003b.yml).
Derived JSON, metadata and comparison plot are archived; raw EDF
excerpts are temporary and never uploaded.
