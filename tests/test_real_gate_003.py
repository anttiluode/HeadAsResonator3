"""Gate 003 selection and common-mode synthetic controls."""
import numpy as np
from scipy import signal
from scripts.real_gate_003 import compare,score_monitor,summarize,SELECTED

def test_reference_cancels_shared_microphone_but_cannot_name_physical_route():
    rng=np.random.default_rng(12)
    fs=1200;n=fs*15
    mic=signal.lfilter([1],[1,-.35],rng.standard_normal(n))
    common=.8*mic
    grid=np.vstack([common+.15*rng.standard_normal(n) for _ in range(128)])
    raw=grid[::8];car=raw-grid.mean(axis=0)
    a=score_monitor(mic,raw,fs)
    b=score_monitor(mic,car,fs)
    c=compare(a,b)
    assert c["strong_raw_audio_coupling_descriptive"]
    assert c["large_car_attenuation_descriptive"]
    assert a["n_passing"]==len(SELECTED)
    assert b["n_passing"]==0

def test_no_success_inferred_when_input_has_no_explained_signal():
    a={"mean_r2":-.02,"n_passing":0,"mean_coherence":.02,
       "all_channels_r2_above_wrong_audio_mean":0}
    b={"mean_r2":-.01,"n_passing":0,"mean_coherence":.03}
    c=compare(a,b)
    assert not c["strong_raw_audio_coupling_descriptive"]
    assert c["raw_to_car_drop_fraction_if_positive"] is None

def test_failed_files_not_replaced_in_denominator():
    sel={"runs":[{},{},{}],"n_fresh_requested":1}
    rows=[
        {"selection":{"label":"fresh_subject"},"status":"evaluated",
         "comparison":{"strong_raw_audio_coupling_descriptive":True,
                       "large_car_attenuation_descriptive":True}},
        {"selection":{"label":"known_original"},"status":"evaluated",
         "comparison":{"strong_raw_audio_coupling_descriptive":True,
                       "large_car_attenuation_descriptive":False}},
        {"selection":{"label":"known_previous_negative"},"status":"failed"}]
    summary=summarize(sel,rows)
    assert summary["selected_runs"]==3 and summary["failures"]==1
    assert summary["fresh_subjects_evaluated"]==1
    assert summary["strong_raw_fresh"]==1
