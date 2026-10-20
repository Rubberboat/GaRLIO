# Radar-aided Point-LIO — Phase 0 gpt

Point-LIO 출력 모델과 GaRLIO의 레이더 기능을 비교·결합하기 위한 별도 연구 워크스페이스다. 사용자 명세 원문은 [CLAUDE.md](CLAUDE.md), 현재 상태는 [docs/progress.md](docs/progress.md)에 있다. 기존 JURLIO를 베이스라인으로 사용하지 않으며 세 공식 저장소를 지정 커밋 그대로 빌드한다.

현재 위치는 [`Rubberboat/GaRLIO`의 GPT 브랜치](https://github.com/Rubberboat/GaRLIO/tree/codex/radar-point-lio-phase0-gpt)다. `Rubberboat/jurlio`의 `9e31945`에서 연구 환경과 전용 CI를 옮겼다. 대상 GaRLIO의 기준 커밋은 연구 명세와 같은 `ff4dfef`다. 저장소 루트의 GaRLIO ROS 패키지는 그대로 두고, 이 디렉터리를 Docker 빌드 컨텍스트로 사용한다. `CATKIN_IGNORE`는 바깥 catkin 워크스페이스가 연구용 중첩 소스를 검색하지 않도록 하며, 컨테이너 안의 명시적 `catkin_ws/src` 빌드에는 영향을 주지 않는다.

**현재는 환경·실행 도구 구현 단계다. Linux ROS 전체 빌드와 NTU bag 재생 성공을 아직 확인하지 않았다. 정확도 결과는 없다. Phase 1 이상으로 진행하지 않았다.**

## Linux에서 빌드

실행 대상은 x86-64 Linux + Docker다. `osrf/ros:noetic-desktop-full` 이미지의 ROS 패키지를 사용하고 ROS apt 저장소는 제거한다. 추가 C++ 의존성은 Ubuntu apt, `catkin-tools`는 PyPI에서 설치한다. Livox SDK/driver와 세 방법은 [sources.lock.json](sources.lock.json)의 SHA로 고정한다. FAST-LIO의 ikd-Tree도 상위 커밋의 gitlink에 따라 재귀 복원한다. 소스 수정 패치는 없다.

새로 받을 때:

```bash
git clone --branch codex/radar-point-lio-phase0-gpt https://github.com/Rubberboat/GaRLIO.git
cd GaRLIO
```

이후 저장소 루트에서:

```bash
cd research_ws_gpt
mkdir -p build_logs
set -o pipefail
docker build --build-arg BUILD_JOBS=2 \
  --build-arg RESEARCH_GIT_COMMIT="$(git rev-parse HEAD)" \
  -f docker/ros/Dockerfile -t radar-point-lio-ros:phase0-gpt . \
  2>&1 | tee build_logs/ros-build.log
docker build -f docker/analysis/Dockerfile -t radar-point-lio-analysis:phase0-gpt . \
  2>&1 | tee build_logs/analysis-build.log
docker run --rm radar-point-lio-analysis:phase0-gpt
```

소스만 로컬에서 읽으려면 `python3 scripts/bootstrap_sources.py`. 기존 checkout이 다른 커밋이거나 수정되어 있으면 덮어쓰지 않고 중단한다. 다운로드한 소스는 `.gitignore` 대상이다. Point-LIO/FAST-LIO CMake는 내부적으로 Debug와 `-O3`를 지정하므로 바깥의 Release 요청만으로 Release라고 보고하지 않는다. 바이너리 존재와 빌드 로그로 확인해야 한다.

기반 Docker 태그·Ubuntu 패키지·전이 Python 의존성까지 완전히 고정한 환경은 아니다. 이미지 안에 실제 `dpkg-query`/`pip freeze` 기록을 남긴다. 성능 비교 전에 사용할 이미지 ID와 머신을 고정해야 한다. Apple Silicon의 에뮬레이션 결과를 x86 Linux 처리시간과 섞지 않는다.

## 실제 bag으로 CHECKPOINT 0 확인

데이터 기본 위치는 `~/datasets/NTU4DRadLM`. 다르면 `export DATASET_ROOT=/absolute/path/NTU4DRadLM`로 설정한다. `/data`는 읽기 전용, `results/`는 `/results`에 연결한다. **아래 `cp/example.bag`는 실제 bag 파일명으로 바꿔야 한다.**

먼저 각 공식 Horizon 설정과 launch 파라미터를 합쳐 실행 확인용 설정을 만든다:

```bash
bash docker/run.sh ros bash -c '
  mkdir -p /results/smoke-configs
  for method in fast_lio point_lio garlio; do
    python3 /work/scripts/prepare_smoke_config.py "$method" \
      --output "/results/smoke-configs/$method.yaml" || exit
  done'
```

GaRLIO는 공식 `loop2.yaml`을 사용한다. 세 설정 모두 PCD 저장을 끈다. GaRLIO의 잘못된 절대 저장 경로는 매 실행 폴더로 덮어쓰며 원본 파일은 수정하지 않는다. **이 설정은 연결·출력 확인용이다. 공식 설정끼리도 extrinsic과 온라인 추정 여부가 다르므로 성능 비교에 사용하면 안 된다.** NTU `calib/`를 이용한 공통 보정값과 GT 프레임 확인은 Phase 1 작업이다.

짧은 실제 bag 구간을 세 방법에 재생한다. 초기 정지 구간이 포함된 시작 부분을 사용한다:

```bash
bash docker/run.sh ros bash -c '
  for method in fast_lio point_lio garlio; do
    bash /work/scripts/run_experiment.sh "$method" cp \
      --bag /data/cp/example.bag \
      --config "/results/smoke-configs/$method.yaml" \
      --output /results/checkpoint0 --runs 1 --duration 30 --rate 0.5 || exit
  done'
```

재실행할 때는 새 `--output` 경로를 쓴다. 입력 topic/메시지 타입/시각 검사에 실패하면 ROS를 시작하지 않는다. Horizon CustomMsg를 대상으로 하며 GaRLIO에는 radar topic이 필수다. 전체 센서 헤더 검사와 bag SHA-256 계산은 N회 반복 앞에서 한 번씩 하므로 큰 bag에서는 시간이 걸린다. `--duration`은 bag 기록 시각 기준 초이며 궤적 시각은 Odometry `header.stamp`다.

각 실행에 다음 파일을 저장한다:

```text
results/checkpoint0/<method>/cp/run_1/
  trajectory.tum             # t x y z qx qy qz qw; 좌표계 변환 없음
  meta.json                  # 완료/실패, commit, config 전문, bag hash, 머신, 명령, 실제 ROS 파라미터
  config.requested.yaml
  config.effective.yaml      # GaRLIO 저장 경로를 적용한 설정
  recorder.json              # pose 수, 첫/끝 header stamp, frame, 오류
  cpu.csv                    # roslaunch + 자손 노드; 100% = CPU 코어 하나
  master.log launch.log recorder.log player.log roslog/
```

메타데이터 `status=completed`는 재생·출력 검사를 통과했다는 뜻이다. 정확도 검증이 아니다. recorder 오류, 5개 미만 pose, 노드 종료, 마지막 센서와 마지막 pose의 시각 차이가 기본 2초를 넘으면 실패한다. 초기화 지연은 `start_lag_seconds`로 보고한다. 초기화와 처리 지연 때문에 출력을 놓칠 수 있으므로 full-run 성공만으로 모든 메시지 처리를 보증하지 않는다. ROS TCP 큐의 완전한 무손실도 현재 도구로 증명하지 않는다.

단독 기록은 다음과 같다(ROS 환경에서 실행):

```bash
python3 scripts/record_traj.py --topic /Odometry \
  --output /results/manual.tum --stats /results/manual.json
```

## 장시간 실행

Phase 1 승인·공통 보정 후 `--duration`을 생략하고 `--runs 5`를 사용한다. 예를 들어 Linux 호스트에서 아래 형식으로 실행하면 터미널과 분리된다. Phase 0에서는 짧은 확인에 사용한다:

```bash
nohup bash docker/run.sh ros bash /work/scripts/run_experiment.sh point_lio cp \
  --bag /data/cp/example.bag --config /results/smoke-configs/point_lio.yaml \
  --output /results/checkpoint0-background --runs 1 --duration 30 \
  > results/checkpoint0-background.log 2>&1 &
echo $! > results/checkpoint0-background.pid
```

중단은 해당 Docker 컨테이너에 `docker stop`을 사용한다. runner는 SIGTERM을 받으면 자신이 시작한 process group을 정리하고 실패 상태를 기록한다. 다른 실험의 ROS 프로세스를 종료하지 않는다. 기본은 GUI 없는 실행이다. X11이 설정된 Linux에서는 `WITH_X11=1 DISPLAY=...`로 연결할 수 있다. 이 wrapper 자체는 RViz를 자동 실행하지 않는다.

## 로컬 검사

```bash
python3 -m pip install PyYAML==6.0.3 psutil==7.0.0
python3 -m unittest discover -s tests -v
bash -n docker/run.sh docker/ros/entrypoint.sh scripts/run_experiment.sh
```

테스트는 TUM 보존, timestamp/수치/프레임 검증, 누락 센서, 설정 namespace, 실패 메타데이터, 프로세스 정리를 확인한다. ROS 필터 알고리즘·실데이터 정확도 테스트를 대신하지 않는다. GitHub의 `Radar Point-LIO Phase 0 gpt` workflow는 Linux 이미지 빌드와 import/package 검사를 제공한다. 실제 NTU bag은 업로드하지 않는다.
