"""Conditional microphone/EMG comparison numerical and negative controls."""
import numpy as np
import pytest
from scipy import signal
from resonator3.conditional import (
    conditional_predictors, bandpass_sources, LAG_MS, lag_matrix,
)


def fake_sources(seed=17,n=30000):
    rng=np.random.default_rng(seed)
    a=signal.lfilter([1],[1,-.5],rng.standard_normal(n))
    e=signal.lfilter([1],[1,-.5],rng.standard_normal(n))
    d=lambda s,l:np.pad(s[:-l],(l,0))
    sources={"mic1":a,"mic2":.8*a+.02*rng.standard_normal(n),
             "lip_upper":e,"lip_lower":.6*e+.05*rng.standard_normal(n),
             "eog":rng.standard_normal(n),
             "listen1":np.zeros(n),"listen2":np.zeros(n)}
    Y=np.array([d(a,8),d(e,8),d(a,8)+d(e,8),
                rng.standard_normal(n)])+.16*rng.standard_normal((4,n))
    return sources,Y


def test_fixed_lag_model_discriminates_microphone_and_lip_emg():
    src,Y=fake_sources()
    fs=1000
    src,Y=bandpass_sources(src,Y,fs,low=40,high=350)
    result=conditional_predictors(src,Y,fs)
    assert result["fixed_lags_ms"]==list(LAG_MS)
    assert result["groups"]["mic1"]["test_r2"][0]>.6
    assert result["groups"]["mic1"]["test_r2"][1]<.12
    assert result["groups"]["lip_emg"]["test_r2"][1]>.6
    assert result["groups"]["mic_plus_lip"]["test_r2"][2]>.65
    assert result["mic_increment_over_lip"][0]>.4
    assert result["lip_increment_over_mic"][1]>.4
    assert result["groups"]["shifted_mic"]["test_r2"][0]<.1
    assert result["groups"]["mic1"]["test_r2"][3]<.10
    assert not result["groups"]["listening_monitors"]["active"]


def test_fixed_features_use_signed_time_offsets():
    fs=1000
    n=2000
    x=np.arange(n,dtype=float)
    src={"mic1":x}
    A=lag_matrix(src,("mic1",),fs,n,np.array([100]))
    expected=np.asarray([x[100-l] for l in LAG_MS])
    assert np.allclose(A.ravel(),expected)


def test_bad_data_refused():
    src,Y=fake_sources(n=1000)
    with pytest.raises(ValueError):
        conditional_predictors(src,Y,1000)
    src,Y=fake_sources(n=15000)
    src["lip_upper"]=src["lip_upper"][:-1]
    with pytest.raises(ValueError):
        conditional_predictors(src,Y,1000)
