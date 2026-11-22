"""Gate 003B: separate metadata-only three-subject repeated-run protocol."""
import random
import pytest
from scripts.choose_run_replicates import choose_repeated_runs
from scripts.choose_cross_subject_runs import ORIGINAL_STEM,KNOWN_NEGATIVE_STEM


def sample(sub,run,session):
    stem=f"sub-{sub:02d}_ses-{session}_task-speechopen_acq-pangolin_run-{run:02d}"
    return {"path":f"sub-{sub:02d}/ses-{session}/eeg/{stem}_eeg.edf",
            "groups":[{"source_rate_hz":1200.0}]}


def test_fixed_three_subject_inventory_includes_original_and_negative_without_signal_peeking():
    stores=[]
    for sub in (1,2,3):
        for run in (1,2,3,4):
            ses="20230829" if sub==1 else "20240821"
            stores.append(sample(sub,run,ses))
    a=choose_repeated_runs({"stores":stores},3)
    random.Random(22).shuffle(stores)
    b=choose_repeated_runs({"stores":stores},3)
    assert a==b
    assert len(a["runs"])==9
    assert len({r["subject"] for r in a["runs"]})==3
    assert a["runs"][0]["stem"]==KNOWN_NEGATIVE_STEM
    assert next(r for r in a["runs"] if r["label"]=="known_original")["stem"]==ORIGINAL_STEM
    assert sum(r["label"]=="fresh_subject" for r in a["runs"])==1
    assert sum(r["label"]=="same_subject_different_run" for r in a["runs"])==6
    assert a["selection_uses_signal"] is False


def test_invented_fourth_participant_refused_without_retargeting():
    stores=[sample(sub,1,"20230829" if sub==1 else "20240821")
            for sub in (1,2,3,4)]
    with pytest.raises(RuntimeError,match="exactly three"):
        choose_repeated_runs({"stores":stores},3)
