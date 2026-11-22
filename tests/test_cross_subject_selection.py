"""Public metadata-based participant selection controls."""
import pytest
from scripts.choose_cross_subject_runs import (
    choose_runs, ORIGINAL_STEM, KNOWN_NEGATIVE_STEM,
)


def sample(sub,run=1,session="20240821",rate=1200):
    stem=f"sub-{sub:02d}_ses-{session}_task-speechopen_acq-pangolin_run-{run:02d}"
    return {"path":f"sub-{sub:02d}/ses-{session}/eeg/{stem}_eeg.edf",
            "groups":[{"source_rate_hz":rate}], "stored_signal_data":"INACCESSIBLE"}


def test_lexical_selection_ignores_signal_strength_and_shuffled_index():
    import random
    runs=[sample(1,1,session="20230829"),sample(3,2),
          sample(3,1),sample(2,2),sample(2,1),
          sample(4,1),sample(5,1),sample(6,1),sample(7,1),sample(8,1),
          sample(9,1),sample(10,1),sample(11,1)]
    first=choose_runs({"stores":runs},n_fresh=8)
    random.Random(1).shuffle(runs)
    second=choose_runs({"stores":runs},n_fresh=8)
    assert first["runs"]==second["runs"]
    assert len(first["runs"])==11
    assert first["runs"][0]["stem"]==ORIGINAL_STEM
    assert first["runs"][1]["stem"]==KNOWN_NEGATIVE_STEM
    assert first["runs"][2]["stem"].startswith("sub-02")
    assert first["runs"][-1]["label"]=="same_subject_different_run"
    assert "signal" not in next(iter(first["runs"][0]))


def test_downsampled_data_only_not_eligible_for_440hz():
    items=[sample(1,1,session="20230829"),sample(3,2),
           sample(2,1,rate=250)]
    with pytest.raises(RuntimeError,match="independent"):
        choose_runs({"stores":items},n_fresh=1)


def test_manifest_must_contain_known_original_and_negative():
    with pytest.raises(RuntimeError,match="anchors"):
        choose_runs({"stores":[sample(3,2)]},n_fresh=1)
