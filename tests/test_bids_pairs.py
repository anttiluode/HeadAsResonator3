"""Local BIDS pairing checks cannot substitute an unrelated WAV."""
from scripts.bids_pairs import entities,find_pairs


def test_entities_and_pair_match(tmp_path):
    eegdir=tmp_path/"sub-03"/"ses-20240821"/"eeg"
    behdir=eegdir.parent/"beh"
    eegdir.mkdir(parents=True);behdir.mkdir()
    prefix="sub-03_ses-20240821_task-speechopen_acq-pangolin_run-02"
    eeg=eegdir/(prefix+"_eeg.edf");eeg.touch()
    correct=behdir/(prefix+"_recording-vocal_beh.wav");correct.touch()
    wrong=behdir/("sub-03_ses-20240821_task-listening_acq-pangolin_run-02_recording-audio_beh.wav")
    wrong.touch()
    result=find_pairs(tmp_path)
    assert len(result)==1
    assert result[0]["wav"]==str(correct)
    assert result[0]["task"]=="speechopen"
    assert entities(correct.name)["run"]=="02"


def test_empty_data_directory_not_silent_success(tmp_path):
    assert find_pairs(tmp_path)==[]
