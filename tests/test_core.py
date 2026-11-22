"""Synthetic kill tests for phase, delays, mismatched audio, and null attribution.

All synthetic. Never interpret these as proof of physical origins in real EEG.
"""
import numpy as np
import pytest
from scipy import signal

from resonator3.core import (
    complex_transfer, lag_audit, candidate_lags, synthesize, _design,
)


def test_transfer_recovers_complex_phase_and_delayed_fir():
    fs=1200
    x,Y,names,truth,_=synthesize(seed=11,fs=fs,seconds=15)
    tr=complex_transfer(x,Y,fs,nperseg=4096)
    assert tr.H_complex.shape==(5,2049)
    # Exact generated H(f)=0.95e^(-i f a)+0.5e^(-i f b).
    a,b=truth["two-delays"]
    f=tr.frequencies_hz
    expected=.95*np.exp(-2j*np.pi*f*a/fs)+.5*np.exp(-2j*np.pi*f*b/fs)
    valid=(f>80)&(f<450)&tr.identifiable_mask
    # Complex comparison checks phase; a magnitude-only filter would fail.
    error=np.median(np.abs(tr.H_complex[0,valid]-expected[valid]))
    assert error<.13, error
    assert np.median(tr.coherence[0,valid])>.80
    assert np.median(tr.coherence[4,valid])<.18
    # The imaginary spectrum cannot be discarded without changing timing.
    assert np.median(abs(tr.H_complex[0,valid].imag))>.1


def test_audio_specific_multichannel_lag_and_wrong_audio_null():
    x,Y,names,truth,fs=synthesize(seed=8,seconds=20)
    result=lag_audit(x,Y,fs,negative_ms=20,positive_ms=100,
                     step_ms=2,max_taps=9,wrong_audio_shifts=3)
    assert result["test_r2"].shape==(5,)
    assert result["wrong_audio_test_r2"].shape==(3,5)
    assert np.all(result["test_r2"][:4]>.75),result["test_r2"]
    assert result["test_r2"][4]<.10
    assert np.all(result["test_r2_above_wrong_audio_max"][:4]>.55)
    assert abs(result["dominant_lag_ms"][1]-71)<3.1
    assert abs(result["dominant_lag_ms"][3])<3
    assert result["negative_lag_energy_fraction"][0]<.2


def test_negative_lags_detect_possible_clock_mismatch_not_anatomy():
    rng=np.random.default_rng(77)
    fs=1000
    x=rng.standard_normal(fs*8)
    # EEG anticipates the microphone due to recording offset.
    Y=np.r_[x[6:],np.zeros(6)][None,:]
    outcome=lag_audit(x,Y,fs,negative_ms=15,positive_ms=30,
                      step_ms=1,wrong_audio_shifts=1,max_taps=5)
    assert outcome["test_r2"][0]>.92
    assert abs(outcome["dominant_lag_ms"][0]+6)<1.1


def test_delayed_electrode_cannot_be_assigned_to_skull_or_wire_by_audio_only():
    x,Y,names,truth,fs=synthesize(seed=19,seconds=12)
    assert truth["two-sources-same-lag"][0]==truth["two-sources-same-lag"][1]
    result=lag_audit(x,Y,fs,negative_ms=20,positive_ms=100,
                     step_ms=2,wrong_audio_shifts=1)
    assert result["test_r2"][2]>.85
    # The delayed audio is real, but the observation does not identify
    # the two identical-latency physical sources that created it.


def test_lag_features_do_not_cross_train_test_split():
    x=np.arange(100.,dtype=float)
    A,t=_design(x,np.array([-4,0,6]))
    assert A[0,0]==x[10]
    assert A[0,1]==x[6]
    assert A[0,2]==x[0]
    assert A[-1,2]<len(x)


def test_validation_refuses_invalid_inputs_and_small_recordings():
    with pytest.raises(ValueError):
        candidate_lags(1000,negative_ms=2,positive_ms=1,step_ms=50)
    with pytest.raises(ValueError):
        complex_transfer(np.zeros(256),np.ones((2,128)),1200)
    with pytest.raises(ValueError):
        lag_audit(np.zeros(100),np.zeros((1,100)),1200)


def test_same_power_random_phase_destroys_eeg_audio_alignment():
    rng=np.random.default_rng(12)
    x,Y,_,_,fs=synthesize(seed=20,seconds=10)
    spec=np.fft.rfft(x)
    phase=rng.uniform(-np.pi,np.pi,len(spec))
    phase[0]=0
    if len(x)%2==0:phase[-1]=0
    wrong=np.fft.irfft(abs(spec)*np.exp(1j*phase),n=len(x))
    assert np.allclose(abs(np.fft.rfft(wrong)),abs(spec),rtol=1e-10)
    tr_real=complex_transfer(x,Y,fs,nperseg=2048)
    tr_wrong=complex_transfer(wrong,Y,fs,nperseg=2048)
    band=(tr_real.frequencies_hz>50)&(tr_real.frequencies_hz<450)
    assert np.mean(tr_real.coherence[0,band]) > np.mean(tr_wrong.coherence[0,band])+.35
