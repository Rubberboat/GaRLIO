# GaRLIO 기반 확장 — Phase 0 gpt

GaRLIO의 기존 처리·필터 구조에 개선사항을 추가하고 검증하는 연구 환경이다. **개선할 코드는 이 저장소 루트의 GaRLIO**이며, Point-LIO·FAST-LIO는 비교 기준이다. 현재 작업 지침은 [CLAUDE.md](CLAUDE.md), 상태는 [docs/progress.md](docs/progress.md)에 있다. 이전 Point-LIO 기반 명세는 [원문 보관본](docs/point_lio_plan_original.md)으로 남겼다.

현재 위치는 [`Rubberboat/GaRLIO`의 GPT 브랜치](https://github.com/Rubberboat/GaRLIO/tree/codex/radar-point-lio-phase0-gpt)다. 연구 도구는 `Rubberboat/jurlio`의 `9e31945`에서 옮겼으며 기존 JURLIO 알고리즘은 사용하지 않는다. GaRLIO 기준 커밋은 `ff4dfef`다. 루트의 ROS 패키지 이름은 `garlio`를 유지하고 **ROS Docker 빌드 컨텍스트를 저장소 루트**로 사용한다. `CATKIN_IGNORE`는 바깥 catkin이 연구용 중첩 소스를 검색하지 않도록 한다.

| 실험 이름 | 빌드 소스 | 컨테이너 실행 |
|---|---|---|
| `garlio` | SHA 고정 원본 GaRLIO | `bash docker/run.sh ros …` |
| `garlio_gpt` | 루트 fork의 현재 `src/`, `include/` 등 | `bash docker/run.sh garlio_gpt …` |
| `point_lio`, `fast_lio` | SHA 고정 공식 비교 소스 | `bash docker/run.sh ros …` |

원본은 `/opt/research/catkin_ws`, fork는 `/opt/research/fork_ws`에서 각각 빌드한다. fork를 선택한 컨테이너만 해당 overlay를 로드한다. runner는 ROS가 찾은 실제 패키지를 검사하므로 원본/개선본 이름을 혼용하면 재생 전에 실패한다. `garlio_gpt`는 fork 실행을 뜻하며 성능 개선이 검증됐다는 뜻이 아니다.

**현재는 환경·실행 도구 단계다. [커밋 `8f0427b`의 Linux CI](https://github.com/Rubberboat/GaRLIO/actions/runs/39395984431)에서 원본 세 방법과 fork의 ROS 빌드, 패키지 선택·소스 확인, 테스트 28개, 분석 이미지 import 검사가 통과했다. NTU bag 재생·궤적 동일성·정확도는 아직 미검증이며 Phase 1 이후 실험은 미실행이다.**

알고리즘 변경 전 논문의 기능 도입 이유·의존성과 실제 코드를 대조한다. [설계 근거 기록](docs/design_rationale.md)에 핵심 기능의 논문 절과 코드 위치, 아직 해석하지 않은 차이를 정리했다. 더 나은 대안에는 교체·재설계도 허용하며, push 전에 변경 내용·이유·검증 범위를 설명한다. ablation용 OFF와 설계 변경은 구별한다.

## Linux에서 빌드

실행 대상은 x86-64 Linux + Docker다. `osrf/ros:noetic-desktop-full` 이미지의 ROS 패키지를 사용하고 ROS apt 저장소는 제거한다. 추가 C++ 의존성은 Ubuntu apt, `catkin-tools`는 PyPI에서 설치한다. Livox SDK/driver와 세 비교 방법은 [sources.lock.json](sources.lock.json)의 SHA로 고정한다. FAST-LIO의 ikd-Tree도 상위 커밋의 gitlink에 따라 재귀 복원한다. 원본 소스 패치는 없다. FAST-LIO의 `Pose6D.h` 생성 순서 문제는 메시지 target을 먼저 빌드해 처리한다. fork는 현재 루트 소스를 별도로 복사해 빌드한다.

새로 받을 때:

```bash
git clone --branch codex/radar-point-lio-phase0-gpt https://github.com/Rubberboat/GaRLIO.git
cd GaRLIO
```

이후 저장소 루트에서:

```bash
mkdir -p research_ws_gpt/build_logs
set -o pipefail
docker build --build-arg BUILD_JOBS=2 \
  --build-arg RESEARCH_GIT_COMMIT="$(git rev-parse HEAD)" \
  -f research_ws_gpt/docker/ros/Dockerfile -t radar-point-lio-ros:phase0-gpt . \
  2>&1 | tee research_ws_gpt/build_logs/ros-build.log
docker build -f research_ws_gpt/docker/analysis/Dockerfile \
  -t radar-point-lio-analysis:phase0-gpt research_ws_gpt \
  2>&1 | tee research_ws_gpt/build_logs/analysis-build.log
docker run --rm radar-point-lio-analysis:phase0-gpt
cd research_ws_gpt
```

이미지 태그와 브랜치 이름은 기존 `gpt` 작업의 연속성을 위해 유지했다. 루트 소스를 수정하면 ROS 이미지를 다시 빌드한다. wrapper는 현재 저장소를 `/repo:ro`로 연결하며 runner는 빌드 시 기록한 파일 hash와 비교한다. 소스가 다르면 오래된 바이너리를 새 코드 결과로 기록하지 않고 재빌드를 요구한다. 커밋하지 않은 코드도 파일 hash로 구별하며 문서만 바꾼 경우에는 재빌드가 필요 없다.

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

fork도 자체 설정으로 준비하고 실행한다:

```bash
bash docker/run.sh garlio_gpt bash -c '
  mkdir -p /results/smoke-configs &&
  python3 /work/scripts/prepare_smoke_config.py garlio_gpt \
    --output /results/smoke-configs/garlio_gpt.yaml &&
  bash /work/scripts/run_experiment.sh garlio_gpt cp \
    --bag /data/cp/example.bag \
    --config /results/smoke-configs/garlio_gpt.yaml \
    --output /results/checkpoint0 --runs 1 --duration 30 --rate 0.5'
```

fork 설정은 `/opt/research/fork_ws/src/garlio/config/loop2.yaml`에서 만든다. 원본과 동일 설정의 비교를 할 때는 두 실행에 같은 검증된 YAML을 전달한다. 현재 C++ 알고리즘은 기준 버전과 같으며, 이 단계는 fork를 빌드·실행하는 경로를 마련한다. 추가 기능의 구현 순서와 검증은 `CLAUDE.md`의 Phase 2–3에 있다.

재실행할 때는 새 `--output` 경로를 쓰고, 설정 생성도 새 `--output` 파일명을 사용하거나 이미 생성한 설정을 재사용한다. 입력 topic/메시지 타입/시각 검사에 실패하면 ROS를 시작하지 않는다. Horizon CustomMsg를 대상으로 하며 두 GaRLIO에는 radar topic이 필수다. 전체 센서 헤더 검사와 bag SHA-256 계산은 N회 반복 앞에서 한 번씩 하므로 큰 bag에서는 시간이 걸린다. `--duration`은 bag 기록 시각 기준 초이며 궤적 시각은 Odometry `header.stamp`다.

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

GaRLIO 실행의 `meta.json.garlio_source`에는 실제 선택한 패키지 경로와 원본/fork 구분을 저장한다. fork에는 이미지 커밋, 빌드 입력 파일별 SHA-256, 전체 소스 hash, 현재 checkout과의 비교 여부도 남긴다. 원본은 고정 SHA와 clean 상태를 확인한다.

단독 기록은 다음과 같다(ROS 환경에서 실행):

```bash
python3 scripts/record_traj.py --topic /Odometry \
  --output /results/manual.tum --stats /results/manual.json
```

## 장시간 실행

Phase 1의 공통 보정·입력 검증 후 `--duration`을 생략하고 `--runs 5`를 사용한다. 예를 들어 Linux 호스트에서 아래 형식으로 실행하면 터미널과 분리된다. Phase 0에서는 짧은 확인에 사용한다:

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

테스트는 TUM 보존, timestamp/수치/프레임 검증, 누락 센서, 설정 namespace, 실패 메타데이터, 프로세스 정리, 원본/fork 선택과 소스 변경 검출을 확인한다. ROS 필터 알고리즘·실데이터 정확도 테스트를 대신하지 않는다. GitHub의 `GaRLIO Extensions Phase 0 gpt` workflow는 Linux 이미지와 원본/fork package 선택을 검사한다. 루트 C++·설정 변경도 CI를 시작한다. 실제 NTU bag은 업로드하지 않는다.
