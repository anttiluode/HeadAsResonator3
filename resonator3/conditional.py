"""Fixed-lag conditional comparison of recorded microphone, lip EMG and EEG.

This is *predictive* ablation on simultaneous signals, not causal mediation.
Training centering/scales come strictly from the first 60% of a window.
"""
from __future__ import annotations
import numpy as np
from scipy import signal


# Fixed BEFORE examining the new windows. Signed delays relative to monitor.
LAG_MS=(-8,-4,0,4,8,16,32)
GROUPS={
    "mic1":("mic1",),
    "mic2":("mic2",),
    "lip_emg":("lip_upper","lip_lower"),
    "mic_plus_lip":("mic1","lip_upper","lip_lower"),
    "shifted_mic":("shifted_mic",),
    "shifted_mic_plus_lip":("shifted_mic","lip_upper","lip_lower"),
    "eog":("eog",),
    "listening_monitors":("listen1","listen2"),
}


def bandpass_sources(sources,Y,fs,low=50,high=500):
    """Same causal filter for all inputs/outputs, no future pre-ringing."""
    if not (0<low<high<fs*.5):
        raise ValueError("Band outside Nyquist")
    sos=signal.butter(3,[low,high],fs=fs,btype="band",output="sos")
    src={k:signal.sosfilt(sos,np.asarray(v,dtype=float))
         for k,v in sources.items()}
    tgt=signal.sosfilt(sos,np.asarray(Y,dtype=float),axis=-1)
    return src,tgt


def lag_matrix(sources,keys,fs,n,indices):
    lags=np.unique(np.rint(np.asarray(LAG_MS)*fs/1000).astype(int))
    columns=[]
    for key in keys:
        x=sources[key]
        if len(x)!=n:
            raise ValueError("Source array lengths disagree")
        columns.append(x[indices[:,None]-lags[None,:]])
    return np.column_stack(columns)


def _r2(true,pred):
    denom=np.mean((true-true.mean(axis=0))**2,axis=0)
    return 1-np.mean((true-pred)**2,axis=0)/np.maximum(denom,1e-26)


def conditional_predictors(sources,Y,fs,*,ridge=.03,seed=911):
    """Return per-channel heldout R2 for sources and nested source groups.

    Same fixed lags, same training/test times, and per-input train-only
    z-scales across groups. Source inactivity is reported, never converted
    to a true zero neural pathway.
    """
    Y=np.atleast_2d(np.asarray(Y,dtype=float))
    n=Y.shape[1]
    if fs<=0 or n<max(int(fs*12),1000):
        raise ValueError("Need at least 12 seconds of data")
    if not np.isfinite(Y).all() or any(
        len(v)!=n or not np.isfinite(v).all() for v in sources.values()):
        raise ValueError("Nonfinite or misaligned source")
    required={"mic1","mic2","lip_upper","lip_lower","eog","listen1","listen2"}
    if set(sources)!=required:
        raise ValueError(f"Sources should have exactly these keys: {sorted(required)}")
    # Shift a copied independent audio stream; never shuffle the EEG target.
    rng=np.random.default_rng(seed)
    shift=int(rng.integers(int(n*.3),int(n*.7)))
    src={**sources,"shifted_mic":np.roll(sources["mic1"],shift)}
    max_lag=int(round(max(abs(t) for t in LAG_MS)*fs/1000))
    margin=max_lag+max(1,int(fs*.1))
    cut1=int(n*.6)
    cut2=int(n*.8)
    idx_train=np.arange(margin,cut1-margin)
    idx_val=np.arange(cut1+margin,cut2-margin)
    idx_test=np.arange(cut2+margin,n-margin)
    if min(map(len,(idx_train,idx_val,idx_test)))<50:
        raise ValueError("Insufficient independent window data")

    # Standardize each input by training samples only. Do NOT re-normalize
    # sources separately for each fitted group.
    std={k:float(np.std(x[idx_train])) for k,x in src.items()}
    mic_std=max(std["mic1"],1e-20)
    # Mark silent auxiliary monitors when their measured SD is negligible
    # relative to the speaking microphone monitor. This is an heuristic
    # instrument-quality flag, not a physiological statement.
    active={k:bool(v>max(1e-15,mic_std*.001)) for k,v in std.items()}
    center={k:float(np.mean(v[idx_train])) for k,v in src.items()}
    norm={k:(v-center[k])/max(std[k],1e-20) for k,v in src.items()}

    train_y=Y[:,idx_train].T
    ymean=train_y.mean(axis=0)
    ys=max(float(np.sqrt(np.mean(np.var(train_y,axis=0)))),1e-16)
    yt=(train_y-ymean)/ys
    ytest=Y[:,idx_test].T
    yval=Y[:,idx_val].T
    results={}
    for name,keys in GROUPS.items():
        if not all(active[k] for k in keys):
            results[name]={"active":False,"test_r2":None,"val_r2":None,
                           "sources":list(keys)}
            continue
        A=lag_matrix(norm,keys,fs,n,idx_train)
        E=lag_matrix(norm,keys,fs,n,idx_test)
        V=lag_matrix(norm,keys,fs,n,idx_val)
        amean=A.mean(axis=0)
        A=A-amean
        E=E-amean
        V=V-amean
        cov=A.T@A/max(len(A),1)
        scale=max(float(np.trace(cov)/cov.shape[0]),1e-8)
        weights=np.linalg.solve(cov+ridge*scale*np.eye(cov.shape[0]),
                                A.T@yt/len(A))
        predict=lambda m: m@weights*ys+ymean
        results[name]={"active":True,"sources":list(keys),
                       "test_r2":_r2(ytest,predict(E)).tolist(),
                       "val_r2":_r2(yval,predict(V)).tolist()}
    def delta(a,b):
        if not (results[a]["active"] and results[b]["active"]):
            return None
        return (np.asarray(results[a]["test_r2"])-
                np.asarray(results[b]["test_r2"])).tolist()
    return {
        "fixed_lags_ms":list(LAG_MS),
        "train_samples":int(len(idx_train)),
        "validation_samples":int(len(idx_val)),
        "test_samples":int(len(idx_test)),
        "wrong_mic_circular_shift_samples":shift,
        "source_standard_deviation":std,
        "source_active":active,
        "groups":results,
        "mic_increment_over_lip":delta("mic_plus_lip","lip_emg"),
        "lip_increment_over_mic":delta("mic_plus_lip","mic1"),
        "mic_increment_vs_shifted_mic_given_lip":delta(
            "mic_plus_lip","shifted_mic_plus_lip"),
        "warnings":[
            "Predictive source ablation is not causal unmixing or anatomical inference.",
            "Lip EMG and the speaking microphone share vocal production causes.",
            "Group regressions have unequal numbers of predictors; test R2 may prefer simpler models.",
            "All lags fixed in advance; comparison is within this 35-second window.",
            "Only one shifted-microphone null is used in this grouped ablation.",
            "CAR cancels globally shared EEG signals, including potentially genuine ones."
        ]
    }
