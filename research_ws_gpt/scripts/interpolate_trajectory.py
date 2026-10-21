"""Resample TUM poses without extrapolation or bridging a sensor outage."""
import numpy as np


def resample(poses, timestamps, max_gap=0.2):
    poses=np.asarray(poses,dtype=float);timestamps=np.asarray(timestamps,dtype=float)
    if poses.ndim!=2 or poses.shape[1]!=8 or len(poses)<2 or not np.isfinite(poses).all():
        raise ValueError('Expected finite TUM poses')
    if np.any(np.diff(poses[:,0])<=0) or max_gap<=0 or not np.isfinite(max_gap):
        raise ValueError('Invalid timestamps or gap limit')
    result=np.full((len(timestamps),8),np.nan);valid=np.zeros(len(timestamps),dtype=bool)
    for k,t in enumerate(timestamps):
        i=np.searchsorted(poses[:,0],t)
        if i<len(poses) and poses[i,0]==t:
            result[k]=poses[i];valid[k]=True;continue
        if i==0 or i==len(poses):continue
        left,right=poses[i-1],poses[i];dt=right[0]-left[0]
        if dt>max_gap:continue
        alpha=(t-left[0])/dt
        q0=left[4:]/np.linalg.norm(left[4:]);q1=right[4:]/np.linalg.norm(right[4:])
        dot=np.dot(q0,q1)
        if dot<0:q1=-q1;dot=-dot
        if dot>.9995:q=(1-alpha)*q0+alpha*q1
        else:
            theta=np.arccos(np.clip(dot,-1,1))
            q=(np.sin((1-alpha)*theta)*q0+np.sin(alpha*theta)*q1)/np.sin(theta)
        result[k]=np.r_[t,(1-alpha)*left[1:4]+alpha*right[1:4],q/np.linalg.norm(q)]
        valid[k]=True
    return result,valid
