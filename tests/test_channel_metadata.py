"""Fail closed on ambiguous EEG### auxiliary labeling."""
import pytest
from resonator3.cli import _select_auto_channels


class RawDummy:
    def __init__(self,names):
        self.ch_names=list(names)
    def get_channel_types(self):
        return ["eeg"]*len(self.ch_names)


def test_bids_sidecar_excludes_audio_monitors_and_lip_emg(tmp_path):
    name="sub-03_ses-20240821_task-speechopen_acq-pangolin_run-02"
    p=tmp_path/(name+"_eeg.edf")
    sidecar=tmp_path/(name+"_channels.tsv")
    all_names=[f"EEG{i:03d}" for i in range(1,140)]
    sidecar.write_text("name\ttype\tdescription\n"+
        "\n".join(f"{n}\t{('EEG' if i<=128 else 'MISC' if i<=132 else 'EMG')}\tmetadata"
                  for i,n in enumerate(all_names,1))+"\n")
    assert _select_auto_channels(p,RawDummy(all_names),140)==all_names[:128]
    assert len(_select_auto_channels(p,RawDummy(all_names),16))==16


def test_missing_sidecar_refuses_ambiguous_128_plus_auxiliary_labels(tmp_path):
    names=[f"EEG{i:03d}" for i in range(1,140)]
    with pytest.raises(ValueError,match="not safe"):
        _select_auto_channels(tmp_path/"untyped_eeg.edf",RawDummy(names),140)


def test_general_eeg_labels_without_auxiliary_names_can_be_used(tmp_path):
    raw=RawDummy(["Fz","C3","C4","Pz"])
    assert _select_auto_channels(tmp_path/"generic.edf",raw,3)==["Fz","C3","C4"]
