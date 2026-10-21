# SNAIL 2026-10-22 재검증

This directory preserves the exact experiment design and replay/evaluation utilities. It is an experiment-specific record, not a generic dataset downloader. Data4 is now development data. No learned thresholds or bag messages were changed between methods.

Workspace: sibling `GaRLIO/`, `jurlio/`, and `output/`. Set `LIO_WORKSPACE` if those live elsewhere. Bags, references, initial baselines and output locations are explicitly enumerated in the scripts. Install NumPy/PyYAML for scoring; Docker images contain ROS. The pinned baseline is GaRLIO `ff4dfefad2cbd3333824c518d5652f1bf9a5039b`.

```bash
# Build the standard image from the GaRLIO repository root (includes pinned + fork).
docker build --build-arg BUILD_JOBS=2 \
  --build-arg RESEARCH_GIT_COMMIT="$(git rev-parse HEAD)" \
  -f research_ws_gpt/docker/ros/Dockerfile -t radar-point-lio-ros:phase0-gpt .
# Choose a fresh case name: an existing output directory is never overwritten.
python3 research_ws_gpt/experiments/snail_2026_10_22/run_case.py my_data4_run \
  --method garlio_gpt --image radar-point-lio-ros:phase0-gpt --dataset data4 \
  --config research_ws_gpt/experiments/snail_2026_10_22/configs/data4_time.yaml
python3 research_ws_gpt/experiments/snail_2026_10_22/score_cases.py --dataset data4
```

`--source` selects an archived remote revision rather than the local checkout. Its core source hashes must match the image. Image IDs are resolved before replay. Runs use 1x playback, 4 CPU, 8 GiB, no network, isolated ROS masters and read-only inputs. Original and candidate runs are sequential in this experiment; the host is not reserved exclusively.

Evaluation transforms the IMU position to the LiDAR origin, resamples at reference timestamps without extrapolation or interpolation across gaps larger than 0.2 s, and fits one scale-fixed SE(3) transform for the full sequence. It reports both the common valid timestamps across all listed methods and each method's own coverage/metrics. Data4's added valid points are harder; never report only the lower common-time error as the error over all 1,509 reference points. Each attempt, including failed runs, remains in its own folder. A successful process exit means completed replay, not improved accuracy.

`configs/*_time.yaml` adds only the time-consistent-sweep option to the existing comparison configuration. Emergency radar consistency defaults on; set `mapping/refine_velocity_consistency: false` to ablate it. Set `mapping/time_consistent_sweeps: false` for the legacy sweep timing. Numerical results and all repeat outcomes are in the report linked from the progress log.

Remote monitoring is an app heartbeat (id `push-snail`, five minutes). It fetches new revisions into separate source snapshots and runs the same protocol; it does not pull into Claude's dirty worktree or merge unverified commits. The current targets and completed SHA are recorded in `output/improvement_2026-10-22/push_watch_state.json`. Until the user specifies a different branch, watch GaRLIO main and the creation/update of jurlio-hunger. The remote main snapshot tested initially is `2dcc39e70e2e8eb43649820d2315ef78b34a5838`.


Build provenance correction: the first `claude_2dcc39e_*` attempts were invalid because archived source mtimes allowed stale objects to be reused. They are excluded, not deleted. The unmodified remote SHA then failed a clean build because cloudProcess did not link OpenCV. `claude_linkfix_2dcc39e_*` is a separately labelled one-line-link-patched diagnostic copy. See [the incident record](BUILD_CACHE_INCIDENT.md) and [the exact patch](claude_2dcc39e_opencv.patch). Future remote snapshots must use `docker/ros/Dockerfile.revision`, which clears build/devel before compilation. A source hash alone is not proof that the executable was rebuilt.
