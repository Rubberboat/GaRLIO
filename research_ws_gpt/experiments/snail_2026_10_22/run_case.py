"""Run one isolated experiment, preserving image/source identity and command."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--method',required=True,choices=['garlio','garlio_gpt','baseline','robust','dynamic']);p.add_argument('--image',required=True);p.add_argument('--dataset',choices=['data4','data6','synthetic'],required=True);p.add_argument('--config',type=Path);p.add_argument('--source',type=Path);p.add_argument('--rate',default='1');a=p.parse_args()
root=Path(os.environ.get('LIO_WORKSPACE', Path(__file__).resolve().parents[4])).resolve();out=root/'output/improvement_2026-10-22';run=out/a.name;run.mkdir(exist_ok=False)
old=root/'output/push_validation_2026-10-21'
if a.dataset=='data4':
 bag=old/'heldout_20231007_data4/sensors_zed2i.bag';cfg=old/'heldout_20231007_data4/config.yaml';gt=old/'heldout_20231007_data4/reference_lidar.tum'
elif a.dataset=='data6':
 data=root/'output/simulation_comparison_2026-10-21/real_data';bag=data/'data6_sensors.bag';cfg=data/'data6.yaml';gt=data/'reference_lidar.tum'
else:
 data=old/'synthetic_all/inputs';bag=data/'synthetic.bag';cfg=data/'config.yaml';gt=data/'groundtruth.tum'
if a.config:cfg=a.config.resolve()
image=json.loads(subprocess.check_output(['docker','image','inspect',a.image],text=True))[0]
base=['docker','run','--rm','--init','--network','none','--user',f'{os.getuid()}:{os.getgid()}','--cpus','4','--memory','8g','-e','HOME=/tmp/replay-home','-e','PYTHONDONTWRITEBYTECODE=1','-v',f'{root}:/lio:ro','-v',f'{run}:/results','-v',f'{bag}:/data/input.bag:ro','-v',f'{cfg}:/data/config.yaml:ro']
isga=a.method.startswith('garlio');variant='fork' if a.method=='garlio_gpt' else 'baseline'
source=a.source.resolve() if a.source else root/('GaRLIO' if isga else 'jurlio')
if isga:base+=['-e',f'RESEARCH_GARLIO_VARIANT={variant}','-e','RESEARCH_FORK_SOURCE=/lio/'+str(source.relative_to(root))]
base+=[image['Id'],'bash','-c','mkdir -p "$HOME"; git config --global --add safe.directory /opt/research/catkin_ws/src/garlio; exec "$@"','replay']
if isga:
 args=['python3','/lio/GaRLIO/research_ws_gpt/scripts/run_experiment.py',a.method,a.dataset,'--bag','/data/input.bag','--config','/data/config.yaml','--output','/results','--runs','1','--rate',a.rate]
else:
 args=['python3','/lio/'+str(source.relative_to(root))+'/scripts/run_replay.py','/data/input.bag','--config','/data/config.yaml','--output','/results/replay','--mode',a.method,'--rate',a.rate]
repo=source;names=['src','include','CMakeLists.txt','package.xml'];hashes={}
for name in names:
 q=repo/name
 if not q.exists():raise RuntimeError('Missing build source: '+str(q))
 for f in sorted(q.rglob('*')) if q.is_dir() else [q]:
  if f.is_file():hashes[str(f.relative_to(repo))]=hashlib.sha256(f.read_bytes()).hexdigest()
harness_files=[root/'GaRLIO/research_ws_gpt/scripts/run_experiment.py',root/'GaRLIO/research_ws_gpt/scripts/garlio_source.py',source/'scripts/run_replay.py']
harness_hashes={str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in harness_files if f.is_file()}
meta={'source_hashes_role':'host fork context; actual upstream commit is verified in run_1/meta.json' if a.method=='garlio' else 'selected build package','harness_hashes':harness_hashes,'name':a.name,'method':a.method,'dataset':a.dataset,'image':image['Id'],'config':str(cfg.relative_to(root)),'reference':str(gt.relative_to(root)),'rate':a.rate,'source_hashes':hashes,'source_root':str(source.relative_to(root)),'command':base+args,'start':time.time()}
(run/'experiment.json').write_text(json.dumps(meta,indent=2)+'\n')
# Verify actual binary inputs for JURLIO too, before launching its nodes.
try:
 binary_dir=('/opt/research/'+('fork_ws' if variant=='fork' else 'catkin_ws')+'/devel/lib/garlio') if isga else '/ws/devel/lib/jurlio'
 binary_check="import json,hashlib,pathlib,sys;print(json.dumps({n:hashlib.sha256((pathlib.Path(sys.argv[1])/n).read_bytes()).hexdigest() for n in ('cloudProcess','lidarMapping')}))"
 meta['binary_hashes']=json.loads(subprocess.check_output(base+['python3','-c',binary_check,binary_dir],text=True))
 meta['input_config_sha256']=hashlib.sha256(cfg.read_bytes()).hexdigest()
 meta['reference_sha256']=hashlib.sha256(gt.read_bytes()).hexdigest()
 if not isga:
  check="import hashlib,json,pathlib; expected=json.loads(pathlib.Path('/results/experiment.json').read_text())['source_hashes']; base=pathlib.Path('/ws/src/jurlio'); bad=[n for n,h in expected.items() if not (base/n).is_file() or hashlib.sha256((base/n).read_bytes()).hexdigest()!=h]; assert not bad,bad"
  subprocess.run(base+['python3','-c',check],check=True)
 with (run/'console.log').open('w') as f:r=subprocess.run(base+args,stdout=f,stderr=subprocess.STDOUT)
 meta['returncode']=r.returncode
except Exception as error:
 meta.update(returncode=1,error=str(error))
 raise
finally:
 meta['finished']=time.time();(run/'experiment.json').write_text(json.dumps(meta,indent=2)+'\n')
print(a.name,meta['returncode'],flush=True)
raise SystemExit(meta['returncode'])
