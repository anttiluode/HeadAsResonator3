"""HeadAsResonator3 core: complex audio->electrode transfer and blind lag audit.

No data loading, network calls, model training on test data, or anatomical
source classification. Audio timing must be independently synchronized.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy import signal


@dataclass
class Transfer:
    frequencies_hz: np.ndarray
    H_complex: np.ndarray                # electrodes × frequencies
    coherence: np.ndarray                # electrodes × frequencies
    input_power: np.ndarray
    identifiable_mask: np.ndarray        # input power support, no causal claim
    impulse_lags_ms: np.ndarray
    impulse_response: np.ndarray         # electrodes × signed circular lags


def complex_transfer(audio, electrodes, fs, nperseg=4096, regularization=1e-6,
                     input_floor_ratio=1e-5):
    """Welch H1 = S_xy/S_xx preserving complex phase.

    scipy.signal.csd(x,y) estimates conj(X)*Y. Thus a *positive* acoustic
    delay produces a negative phase slope in H, as required.
    Broadband stationary-system approximation; not a physical source label.
    """
    x=np.asarray(audio,dtype=float)
    Y=np.atleast_2d(np.asarray(electrodes,dtype=float))
    if x.ndim!=1 or Y.ndim!=2 or Y.shape[1]!=x.size:
        raise ValueError("audio must be 1D and electrodes must be [channel, time]")
    if fs<=0 or x.size<64 or not np.all(np.isfinite(x)) or not np.all(np.isfinite(Y)):
        raise ValueError("invalid sampling frequency, length, or NaN/inf")
    nperseg=min(int(nperseg),x.size//2)
    if nperseg<32:
        raise ValueError("need at least 32 samples per spectral window")
    noverlap=nperseg//2
    f,Sxx=signal.welch(x,fs=fs,nperseg=nperseg,noverlap=noverlap,
                       detrend="constant")
    H=np.zeros((len(Y),len(f)),complex)
    C=np.zeros_like(H.real)
    strength=np.asarray(Sxx,float)
    floor=input_floor_ratio*max(float(Sxx.max()),1e-20)
    mask=Sxx>floor
    for j,y in enumerate(Y):
        _,Sxy=signal.csd(x,y,fs=fs,nperseg=nperseg,noverlap=noverlap,
                         detrend="constant")
        _,Syy=signal.welch(y,fs=fs,nperseg=nperseg,noverlap=noverlap,
                          detrend="constant")
        # Don't divide by input power absent from the experiment.
        denominator=Sxx+regularization*max(float(Sxx.max()),1e-30)
        H[j]=np.where(mask,Sxy/denominator,0)
        C[j]=np.clip(np.abs(Sxy)**2/
                     np.maximum(Sxx*Syy,1e-30),0,1)
        C[j,~mask]=0
    # A one-sided H includes phase. Real inverse FFT describes the
    # circular linear response in a nperseg-sample window.
    h=np.fft.fftshift(np.fft.irfft(H,n=nperseg,axis=-1),axes=-1)
    lags=(np.arange(nperseg)-nperseg//2)/fs*1000
    return Transfer(f,H,C,strength,mask,lags,h)


def candidate_lags(fs,negative_ms=20,positive_ms=120,step_ms=2):
    """Positive lag means audio at t-lag predicts electrode at time t."""
    if fs<=0 or negative_ms<0 or positive_ms<=0 or step_ms<=0:
        raise ValueError("invalid lag window")
    ms=np.arange(-negative_ms,positive_ms+step_ms*.4,step_ms)
    taps=np.unique(np.rint(ms*fs/1000).astype(int))
    if len(taps)<3:
        raise ValueError("lag resolution exceeds sample spacing")
    return taps


def _design(x,lags):
    """Construct shifted audio columns without crossing this split's border."""
    x=np.asarray(x,dtype=float)
    margin=int(max(np.max(np.abs(lags)),1))
    if x.size<2*margin+80:
        raise ValueError("recording split too short for requested lag range")
    ti=np.arange(margin,x.size-margin)
    A=x[ti[:,None]-lags[None,:]]
    return A,ti


def _scores(y,p):
    """R2 against the held-out mean, not evidence of causal origin."""
    y=np.asarray(y,dtype=float)
    denom=np.mean((y-y.mean())**2,axis=0)
    return 1-np.mean((y-p)**2,axis=0)/np.maximum(denom,1e-25)


def _fit_one(A,Y,lags,ridge=.03,max_taps=9,spacing_samples=3):
    """Choose independent lag candidates using TRAIN correlation only."""
    n,c=A.shape
    k=Y.shape[1]
    aa=A-A.mean(axis=0)
    yy=Y-Y.mean(axis=0)
    corr=(aa.T@yy)/(np.sqrt(np.sum(aa**2,axis=0))[:,None]*
                     np.sqrt(np.sum(yy**2,axis=0))[None,:]+1e-30)
    coef=np.zeros((c,k))
    offsets=np.zeros(k)
    selected=[]
    for ch in range(k):
        order=np.argsort(-np.abs(corr[:,ch]))
        keep=[]
        for ix in order:
            if len(keep)>=max_taps:break
            if all(abs(int(lags[ix])-int(lags[other]))>=spacing_samples
                   for other in keep):
                keep.append(int(ix))
        keep=np.asarray(keep,dtype=int)
        features=aa[:,keep]
        gram=features.T@features/max(n,1)
        scale=max(float(np.trace(gram)/max(len(keep),1)),1e-20)
        rhs=features.T@yy[:,ch]/max(n,1)
        bet=np.linalg.solve(gram+ridge*scale*np.eye(len(keep)),rhs)
        coef[keep,ch]=bet
        offsets[ch]=Y[:,ch].mean()-A[:,keep].mean(axis=0)@bet
        selected.append([int(lags[idx]) for idx in keep])
    return coef,offsets,selected


def _fit_and_score(x,Y,lags,train_fraction=.6,validation_fraction=.2,
                   ridge=.03,max_taps=9,spacing_samples=3):
    n=len(x)
    p=int(n*train_fraction)
    q=int(n*(train_fraction+validation_fraction))
    if not (0<train_fraction<1 and 0<validation_fraction<1 and
            train_fraction+validation_fraction<1):
        raise ValueError("invalid train/validation fractions")
    if Y.shape[1]!=n:
        raise ValueError("unaligned audio and electrode sample counts")
    # Build in each disjoint partition, discarding boundaries. Therefore
    # no audio samples near a split can cross into another split's features.
    A0,t0=_design(x[:p],lags)
    A1,t1=_design(x[p:q],lags)
    A2,t2=_design(x[q:],lags)
    C,offsets,selected=_fit_one(A0,Y[:,:p].T[t0],lags,ridge,
                               max_taps,spacing_samples)
    val=_scores(Y[:,p:q].T[t1],A1@C+offsets)
    test=_scores(Y[:,q:].T[t2],A2@C+offsets)
    return C,offsets,selected,val,test


def lag_audit(audio,electrodes,fs,*,negative_ms=20,positive_ms=120,
              step_ms=2,ridge=.03,max_taps=9,min_spacing_ms=4,
              wrong_audio_shifts=3,seed=29):
    """Training-only lag proposals, heldout prediction and wrong-audio null.

    The null refits the whole search with circularly shifted audio, not just
    tests already learned coefficients on wrong audio. The comparison says
    whether there is predictive audio-specific structure, not what material
    or biological process carried it.
    """
    x=np.asarray(audio,dtype=float)
    Y=np.atleast_2d(np.asarray(electrodes,dtype=float))
    if x.ndim!=1 or Y.ndim!=2 or Y.shape[1]!=len(x):
        raise ValueError("audio and multichannel electrode arrays misaligned")
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(Y))):
        raise ValueError("NaN/inf input")
    lags=candidate_lags(fs,negative_ms,positive_ms,step_ms)
    if len(x)<max(1024,12*int(np.max(np.abs(lags)))):
        raise ValueError("recording too short for reliable three-way temporal split")
    spacing=max(1,int(np.rint(min_spacing_ms/1000*fs)))
    coef,intercept,selected,val,test=_fit_and_score(
        x,Y,lags,ridge=ridge,max_taps=max_taps,spacing_samples=spacing)
    rng=np.random.default_rng(seed)
    null=[]
    if wrong_audio_shifts:
        # Shifts >= ~1/5 record length deliberately break synchronized
        # audio, but retain its spectrum and local temporal structure.
        for i in range(int(wrong_audio_shifts)):
            lower=int(len(x)*.2);upper=int(len(x)*.8)
            shift=int(rng.integers(lower,upper))
            wrong=np.roll(x,shift)
            *_,nval,ntest=_fit_and_score(
                wrong,Y,lags,ridge=ridge,max_taps=max_taps,
                spacing_samples=spacing)
            null.append(ntest)
    null=np.asarray(null).reshape(-1,len(Y))
    max_null=np.max(null,axis=0) if len(null) else np.full(len(Y),np.nan)
    peak_idx=np.argmax(np.abs(coef),axis=0)
    dominant_lag_ms=lags[peak_idx]/fs*1000
    return {
        "lags_samples":lags,
        "coefficients":coef.T,       # channels x candidate-lags
        "selected_lags_samples":selected,
        "intercept":intercept,
        "validation_r2":val,
        "test_r2":test,
        "wrong_audio_test_r2":null,
        "wrong_audio_max_test_r2":max_null,
        "test_r2_above_wrong_audio_max":test-max_null,
        "dominant_lag_ms":dominant_lag_ms,
        "negative_lag_energy_fraction":(
            np.sum(coef[lags<0]**2,axis=0)/
            np.maximum(np.sum(coef**2,axis=0),1e-30)),
        "interpretation":"timing/transfer evidence only; physical path remains unassigned",
    }


def synthesize(seed=11,fs=1200,seconds=24):
    """Known acoustic pathways + confounded channel + audio-independent null.

    Ground truth contains two separate acoustic responses, plus a channel
    where two distinct physical sources share the SAME response and thus
    cannot be separated from audio-electrode measurements alone.
    """
    rng=np.random.default_rng(seed)
    n=int(fs*seconds)
    x=rng.standard_normal(n)
    x=signal.lfilter([1],[1,-.64],x)
    x=x/(np.std(x)+1e-12)
    Y=np.stack([.18*rng.standard_normal(n) for _ in range(5)])
    shift=lambda lag:np.pad(x[:-lag],(lag,0)) if lag>0 else x.copy()
    a=int(round(.006*fs))
    b=int(round(.025*fs))
    c=int(round(.071*fs))
    Y[0]+=.95*shift(a)+.5*shift(b)
    Y[1]+=.65*shift(c)
    Y[2]+=.7*shift(a)+.7*shift(a) # inseparable "skull"+"cable" same delay
    Y[3]+=.60*x                 # nominal simultaneous input recording
    # Y[4] is wholly independent of microphone
    names=["two-delays","long-delay","two-sources-same-lag","zero-lag","independent"]
    truth={"two-delays":[a,b],"long-delay":[c],
           "two-sources-same-lag":[a,a],"zero-lag":[0],
           "independent":[]}
    return x,Y,names,truth,fs
