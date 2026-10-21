"""Common-time comparison plus per-run coverage; full-sequence alignment only."""
import argparse,json,sys,os
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--dataset',choices=['data4','data6'],required=True);a=p.parse_args()
root=Path(os.environ.get('LIO_WORKSPACE', Path(__file__).resolve().parents[4])).resolve();out=root/'output/improvement_2026-10-22'
sys.path[:0]=[str(root/'jurlio/scripts'),str(root/'GaRLIO/research_ws_gpt/scripts')]
from evaluate import read_tum,evaluate
from configuration import load_config,quaternion_matrix
from interpolate_trajectory import resample
old=root/'output/push_validation_2026-10-21';folder=old/('data6_all' if a.dataset=='data6' else 'heldout_all')
config=load_config(folder/'inputs/config.yaml');truth=read_tum(folder/'inputs/groundtruth.tum')
t=np.array(config['mapping']['extrinsic_t_il']);r=np.array(config['mapping']['extrinsic_R_il']).reshape(3,3)
paths={'original':folder/'repeat_1/garlio/sequence/run_1'}
for mode in ['baseline','robust','dynamic']:paths['j_previous_'+mode]=folder/f'repeat_1/jurlio_{mode}'
for f in sorted(out.glob('*/experiment.json')):
 m=json.loads(f.read_text())
 if m.get('dataset')!=a.dataset or m.get('returncode')!=0 or m.get('validation_status','').startswith('invalid'):continue
 path=f.parent/'replay' if m['method'] in ['baseline','robust','dynamic'] else f.parent/m['method']/a.dataset/'run_1'
 paths[f.parent.name]=path
samples={};counts={};gaps={}
for name,path in paths.items():
 poses=read_tum(path/'trajectory.tum');counts[name]=len(poses);gaps[name]=float(np.max(np.diff(poses[:,0])))
 for row in poses:row[1:4]+=quaternion_matrix(row[4:])@t
 samples[name]=resample(poses,truth[:,0],max_gap=.2)
valid=np.logical_and.reduce([v[1] for v in samples.values()]);result={'dataset':a.dataset,'reference_poses':len(truth),'common_poses':int(valid.sum()),'runs':{}}
print(a.dataset,'common',valid.sum(),'/',len(truth))
for name,(poses,ownvalid) in samples.items():
 metrics=evaluate(poses[valid],truth[valid],'se3',.05,r)
 own=evaluate(poses[ownvalid],truth[ownvalid],'se3',.05,r)
 result['runs'][name]={'common_metrics':metrics,'own_metrics':own,'reference_coverage':int(ownvalid.sum()),'poses':counts[name],'max_gap_s':gaps[name],'path':str(paths[name].relative_to(root))}
 print(f"{name:35} RMSE {100*metrics['ate_rmse_m']:8.3f}cm max {100*metrics['ate_max_m']:8.3f}cm rot {metrics['rotation_rmse_deg']:6.3f}deg poses {counts[name]} gap {gaps[name]:.3f}s coverage {ownvalid.sum()}")
(out/(a.dataset+'_scores.json')).write_text(json.dumps(result,indent=2)+'\n')
