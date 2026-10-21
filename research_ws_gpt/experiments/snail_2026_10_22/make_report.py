import json, os, sys, csv, shutil
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(os.environ.get('LIO_WORKSPACE', Path(__file__).resolve().parents[4])).resolve();out=root/'output/improvement_2026-10-22'
report=root/'GaRLIO/research_ws_gpt/experiments/snail_2026_10_22'
summary={}
fig,axes=plt.subplots(1,2,figsize=(10.6,5.2),layout='constrained')
colors=['#64748b','#da8b27','#178f76']
labels=['Upstream GaRLIO','Claude 2dcc39e + link fix','Time-consistent fork']
for col,dataset in enumerate(['data4','data6']):
 data=json.loads((out/f'{dataset}_scores.json').read_text())
 names=[['original',f'original_{dataset}_r2',f'original_{dataset}_r3'],[f'claude_linkfix_2dcc39e_{dataset}_r1',f'claude_linkfix_2dcc39e_{dataset}_r2',f'claude_linkfix_2dcc39e_{dataset}_r3'],['g_time_d4' if dataset=='data4' else 'g_time_d6',f'g_final_{dataset}_r2',f'g_final_{dataset}_r3']]
 summary[dataset]={'common_poses':data['common_poses'],'reference_poses':data['reference_poses'],'groups':{}}
 for i,(label,ns) in enumerate(zip(labels,names)):
  runs=[data['runs'][n] for n in ns]
  vals=np.array([r['common_metrics']['ate_rmse_m']*100 for r in runs]);sd=float(vals.std(ddof=1))
  s={'runs':ns,'rmse_cm':vals.tolist(),'mean_rmse_cm':float(vals.mean()),'std_rmse_cm':sd,'max_error_cm':[r['common_metrics']['ate_max_m']*100 for r in runs],'own_rmse_cm':[r['own_metrics']['ate_rmse_m']*100 for r in runs],'coverage':[r['reference_coverage'] for r in runs],'max_output_gap_s':[r['max_gap_s'] for r in runs]}
  summary[dataset]['groups'][label]=s
  ax=axes[col];ax.bar(i,vals.mean(),color=colors[i],width=.58,alpha=.75);ax.errorbar(i,vals.mean(),yerr=sd,color='#253246',capsize=5,fmt='none');ax.scatter(i+np.array([-.12,0,.12]),vals,color=colors[i],edgecolor='white',s=45,zorder=3)
  ax.text(i,vals.max()+max(vals.mean()*.06,.06),f'{vals.mean():.2f} ± {sd:.2f}',ha='center',fontsize=10)
 ax.set_title(f'SNAIL {dataset} | {data["common_poses"]}/{data["reference_poses"]} common reference times',fontsize=12,pad=18);ax.set_ylabel('Position RMSE (cm; lower is better)');ax.set_xticks(range(3),['Upstream','Claude 2dcc39e\n+ OpenCV link fix','Time-consistent\nfork']);ax.set_ylim(bottom=0,top=ax.get_ylim()[1]*1.14);ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
fig.suptitle('Three complete replays per method · same inputs and calibration',fontsize=15)
own4=summary['data4']['groups']['Time-consistent fork']['own_rmse_cm']
fig.supxlabel('Points: individual runs · bars: mean ± sample SD · full-sequence SE(3), scale = 1\nDevelopment sequences; the time-consistent method waits for the next measured IMU.\n'+f'Data4 candidate on all 1,509 reference times: own RMSE {min(own4):.2f}–{max(own4):.2f} cm.',fontsize=10)
fig.savefig(out/'repeat_comparison.png',dpi=180);plt.close(fig)
# Coverage and processing lag are separate facts.
latency={}
for f in out.glob('g_final_data*/garlio_gpt/*/run_1/radar_guard.csv'):
 rows=list(csv.DictReader(f.open()));v=np.array([float(r['input_clock_lag_s']) for r in rows]);latency[str(f.relative_to(out))]={'rows':len(v),'median_s':float(np.median(v)),'p95_s':float(np.quantile(v,.95)),'max_s':float(v.max()),'max_imu_support_gap_s':max(float(r['imu_support_gap']) for r in rows)}
summary['input_clock_lag']=latency
for dataset in ['data4','data6']:
 groups=summary[dataset]['groups'];original=groups['Upstream GaRLIO'];candidate=groups['Time-consistent fork'];margin=original['mean_rmse_cm']-candidate['mean_rmse_cm'];threshold=2*max(original['std_rmse_cm'],candidate['std_rmse_cm'])
 summary[dataset]['conservative_difference_rule']={'mean_reduction_cm':margin,'twice_larger_sample_sd_cm':threshold,'passed':bool(margin>threshold),'note':'Descriptive research rule, not a significance test; three repeats on development data.'}
 claude=groups['Claude 2dcc39e + link fix'];margin=original['mean_rmse_cm']-claude['mean_rmse_cm'];threshold=2*max(original['std_rmse_cm'],claude['std_rmse_cm'])
 summary[dataset]['claude_linkfix_difference_rule']={'mean_reduction_cm':margin,'twice_larger_sample_sd_cm':threshold,'passed':bool(margin>threshold),'note':'Only the separately link-patched diagnostic copy; the exact remote revision failed to build.'}
(out/'repeat_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for filename in ['data4_scores.json','data6_scores.json','repeat_summary.json','repeat_comparison.png']:
 shutil.copyfile(out/filename,report/filename)
print(json.dumps(summary,indent=2))
