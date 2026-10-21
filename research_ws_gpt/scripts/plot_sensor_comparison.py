#!/usr/bin/env python3
"""Plot completed comparisons and preserve failed attempts in a machine-readable summary."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

NAMES={'garlio':'GaRLIO (official)','baseline':'JURLIO baseline','robust':'JURLIO robust','dynamic':'JURLIO dynamic'}
COLORS={'garlio':'#2563eb','baseline':'#94a3b8','robust':'#dc2626','dynamic':'#059669'}


def cpu_summary(folder,meta):
    start=meta['replay_started_unix']+3 # 2 s player delay + one sampling interval
    end=meta['replay_finished_unix']
    samples=defaultdict(lambda:[0.,0.])
    with (folder/'cpu.csv').open() as f:
        for row in csv.DictReader(f):
            t=float(row['unix_time'])
            if start<=t<=end and row['process'] in ('cloudProcess','lidarMapping'):
                s=samples[round(t-start)];s[0]+=float(row['cpu_percent_one_core']);s[1]+=int(row['rss_bytes'])/1024**2
    values=np.asarray(list(samples.values()))
    return {'cpu_mean_percent_one_core':float(values[:,0].mean()),'cpu_p95_percent_one_core':float(np.percentile(values[:,0],95)),
            'rss_peak_mib_sum':float(values[:,1].max()),'sample_count':len(values),
            'scope':'cloudProcess + lidarMapping, active replay excluding first 3 s; summed RSS double-counts shared pages'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--synthetic',type=Path,nargs='+',required=True)
    p.add_argument('--real',type=Path)
    p.add_argument('--additional-failures',type=Path,nargs='*',default=[],help='Diagnostic retries to preserve, without pooling their timing with the main comparison')
    p.add_argument('--jurlio-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(a.jurlio_root/'scripts'))
    from evaluate import read_tum,associate,evaluate,alignment_transform
    from configuration import load_config,quaternion_matrix
    from interpolate_trajectory import resample
    summary={'synthetic':[],'real':[],'failed_attempts':[]}
    for root in a.additional_failures:
        for status in json.loads((root/'status.json').read_text()):
            if status['status']=='failed':
                summary['failed_attempts'].append(dict(status,experiment=str(root)))
    plotdata={}
    for kind,roots in [('synthetic',a.synthetic),('real',[a.real] if a.real else [])]:
        for root in roots:
            gt=read_tum(root/'inputs/groundtruth.tum')
            for status in json.loads((root/'status.json').read_text()):
                folder=root/status['directory']
                if status['status']!='completed':
                    summary['failed_attempts'].append(dict(status,experiment=str(root)))
                    continue
                meta=json.loads((folder/('meta.json' if status['method']=='garlio' else 'run.json')).read_text())
                metrics=json.loads((folder/'metrics.json').read_text())
                est=read_tum(folder/'trajectory.tum')
                rotation=None
                if kind=='real':
                    cfg=load_config(root/'inputs/config.yaml')
                    rotation=np.asarray(cfg['mapping']['extrinsic_R_il']).reshape(3,3)
                    translation=np.asarray(cfg['mapping']['extrinsic_t_il'])
                    for row in est:row[1:4]+=quaternion_matrix(row[4:8])@translation
                pairs=associate(est,gt,.05);e,g=est[pairs[:,0]],gt[pairs[:,1]]
                r,t=alignment_transform(e[:,1:4],g[:,1:4],metrics['alignment'])
                xyz=est[:,1:4]@r.T+t
                errors=np.linalg.norm(xyz[pairs[:,0]]-g[:,1:4],axis=1)
                item=dict(method=status['method'],repeat=status['repeat'],directory=str(folder),metrics=metrics,
                          resources=cpu_summary(folder,meta),first_pose=float(est[0,0]),last_pose=float(est[-1,0]),
                          max_pose_gap_seconds=float(np.max(np.diff(est[:,0]))),
                          tail_lag_seconds=meta['tail_lag_seconds'])
                if 'radar_diagnostics' in meta:item['radar_diagnostics']=meta['radar_diagnostics']
                summary[kind].append(item)
                if status['repeat']==1:
                    plotdata[(kind,status['method'])]=(est,gt,xyz,errors,e[:,0],rotation)
        if not summary[kind]:continue
        # Same GT timestamps for all methods, so a different output frequency
        # cannot silently change the error comparison. Refit SE(3), never scale.
        candidates={method:plotdata[(kind,method)] for method in NAMES if (kind,method) in plotdata}
        reference=next(iter(candidates.values()))[1]
        interpolated={m:resample(v[0],reference[:,0],max_gap=.2) for m,v in candidates.items()}
        common=np.logical_and.reduce([v[1] for v in interpolated.values()])
        if np.count_nonzero(common)>=3:
            for item in summary[kind]:
                if item['repeat']!=1:continue
                m=item['method'];est,gt,_,_,_,rot=candidates[m]
                item['common_reference_metrics']=evaluate(interpolated[m][0][common],reference[common],
                    'se3' if kind=='real' else 'none',.05,rot)
                item['common_reference_metrics']['resampling']='linear translation + quaternion SLERP, no extrapolation, max bracket gap 0.2 s'
                item['common_reference_metrics']['reference_coverage_fraction']=float(np.mean(common))
                if kind=='real':
                    sampled=interpolated[m][0][common]
                    r,t=alignment_transform(sampled[:,1:4],reference[common,1:4],'se3')
                    xyz=est[:,1:4]@r.T+t
                    errors=np.linalg.norm(sampled[:,1:4]@r.T+t-reference[common,1:4],axis=1)
                    candidates[m]=(est,gt,xyz,errors,reference[common,0],rot)
        fig,axs=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for method,(est,gt,xyz,err,ts,rot) in candidates.items():
            color=COLORS[method];name=NAMES[method];t0=gt[0,0]
            axs[0,0].plot(xyz[:,0],xyz[:,1],color=color,lw=1.5,label=name)
            axs[0,1].plot(est[:,0]-t0,xyz[:,2],color=color,lw=1,label=name)
            axs[1,0].plot(ts-t0,err*(1000 if kind=='synthetic' else 1),color=color,lw=1,label=name)
        gt=next(iter(candidates.values()))[1];t0=gt[0,0]
        axs[0,0].plot(gt[:,1],gt[:,2],'k--',lw=1.2,label='Reference')
        axs[0,0].set(xlabel='x [m]',ylabel='y [m]',title='Trajectory (XY)');axs[0,0].axis('equal');axs[0,0].legend(fontsize=8)
        axs[0,1].plot(gt[:,0]-t0,gt[:,3],'k--',lw=1.1,label='Reference')
        axs[0,1].set(xlabel='Time from reference start [s]',ylabel='z [m]',title='Height')
        axs[1,0].set(xlabel='Time from reference start [s]',ylabel='Position error ['+('mm' if kind=='synthetic' else 'm')+']',title='Position error at common reference times' if kind=='real' else 'Position error at associated poses')
        methods=list(candidates);means=[];std=[]
        for method in methods:
            vals=[x['resources']['cpu_mean_percent_one_core'] for x in summary[kind] if x['method']==method]
            means.append(np.mean(vals));std.append(np.std(vals))
        axs[1,1].bar(range(len(methods)),means,yerr=std,color=[COLORS[m] for m in methods],capsize=3)
        axs[1,1].set_xticks(range(len(methods)),[NAMES[m].replace(' ','\n') for m in methods],fontsize=9)
        axs[1,1].set(ylabel='CPU [% of one logical core]',title='Active replay: two estimator processes')
        for ax in axs.flat:ax.grid(alpha=.2)
        title='SNAIL 20231105/data6 | 126 s real sensors | 4 CPU / 8 GiB | 1x, 1 run' if kind=='real' else 'Synthetic room | 12 s | 20% radar outliers | 2 CPU / 6 GiB | 1x, 3 repeats'
        missing=[NAMES[m] for m in NAMES if m not in candidates]
        if missing:title+='\nIncomplete runs excluded: '+', '.join(missing)
        fig.suptitle(title,fontsize=13)
        fig.savefig(a.output/(kind+'_comparison.png'),dpi=160);fig.savefig(a.output/(kind+'_comparison.pdf'));plt.close(fig)
        # A trajectory playback, not a generated sensor video or physics simulation.
        fig,ax=plt.subplots(figsize=(8,6),layout='constrained')
        ax.plot(gt[:,1],gt[:,2],'k--',alpha=.5,label='Reference')
        traces={};dots={}
        for m in methods:
            traces[m],=ax.plot([],[],color=COLORS[m],lw=1.5,label=NAMES[m]);dots[m],=ax.plot([],[],marker='o',color=COLORS[m],ms=5)
        extent=np.concatenate([v[2][:,:2] for v in candidates.values()]+[gt[:,1:3]])
        low,high=extent.min(0),extent.max(0);pad=np.maximum((high-low)*.08,.1)
        ax.set(xlim=(low[0]-pad[0],high[0]+pad[0]),ylim=(low[1]-pad[1],high[1]+pad[1]),xlabel='x [m]',ylabel='y [m]')
        ax.set_aspect('equal',adjustable='box');ax.legend(fontsize=8,loc='upper right');ax.grid(alpha=.2)
        times=np.linspace(min(v[0][0,0] for v in candidates.values()),max(v[0][-1,0] for v in candidates.values()),126)
        def update(t):
            for m,(est,_,xyz,*_) in candidates.items():
                n=np.searchsorted(est[:,0],t,side='right');traces[m].set_data(xyz[:n,0],xyz[:n,1])
                dots[m].set_data(xyz[n-1:n,0] if n else [],xyz[n-1:n,1] if n else [])
            ax.set_title(('Real SNAIL' if kind=='real' else 'Synthetic')+f' trajectory playback | t = {t-times[0]:.1f} s')
            return list(traces.values())+list(dots.values())
        FuncAnimation(fig,update,frames=times,interval=100).save(a.output/(kind+'_playback.gif'),writer=PillowWriter(fps=10),dpi=100)
        plt.close(fig)
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    for kind in ('synthetic','real'):
        for method in NAMES:
            rows=[r for r in summary[kind] if r['method']==method]
            if rows:
                print(kind,method,len(rows),'ATE m',np.mean([r['metrics']['ate_rmse_m'] for r in rows]),'CPU',np.mean([r['resources']['cpu_mean_percent_one_core'] for r in rows]))


if __name__=='__main__':main()
