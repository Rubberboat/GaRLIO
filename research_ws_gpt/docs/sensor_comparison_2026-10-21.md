# GaRLIO·JURLIO 센서 재생 비교 — 2026-10-21

> 2026-10-22 추가 검증: 복구 수정 후 총 27회 재생을 완료했다(26회 실행 완료, 복구 OFF 1회 예상 실패). 새 data4에서는 원본 GaRLIO RMSE 14.225cm, JURLIO dynamic 38.639cm로 정확도가 악화됐다. 개발 data6 원본도 4회 RMSE 2.427–2.974cm·최대 오차 9.350–39.610cm로 편차가 있어 최초 결과만으로 개선 폭을 확정할 수 없다. [최종 보고서와 그래프](https://github.com/Rubberboat/jurlio/blob/codex/integration-audit-gpt/docs/FULL_VALIDATION_2026-10-21.md)를 우선 참고한다. 아래 최초 결과는 이력을 위해 보존한다.

> 후속 수정: 아래는 수정 전 비교 기록이다. 같은 날 JURLIO dynamic의 레이더 측정 거부 후 복구를 추가해 실측 126초를 3회 완주했다. 위치 RMSE는 2.225–2.234 cm, 최대 오차는 9.066–9.122 cm였다. 상세 설계·대조 시험·한계는 별도 `jurlio/docs/RECOVERY_2026-10-21.md`, 원시 결과는 부모 작업 폴더의 `output/recovery_2026-10-21/`에 있다. 이 GaRLIO 저장소의 원본 알고리즘은 변경하지 않았다.

**기본 궤적 추정은 정상 작동했다. JURLIO robust의 개선은 작으며, dynamic은 실측 데이터에서 실패했다.** 연구 기반으로는 쓸 만하지만, 새 기능이 원본보다 확실히 좋거나 실사용 준비가 끝났다고 말할 결과는 아니다.

이번 작업은 합성 센서 bag 재생과 공개 실측 센서 bag 재생이다. Gazebo 물리 시뮬레이션, 실제 로봇 제어, 동적 객체 영상 인식은 수행하지 않았다. C++ 알고리즘·기본 기능은 변경하지 않았다.

## 실제 데이터 결과

[SNAIL-Radar](https://snail-radar.github.io/)의 `20231105/data6`를 내려받아 XT32 LiDAR, Oculii 원시 레이더, MTi3DK IMU를 동일 설정으로 입력했다. 실제 bag 길이는 **126.135초**다. Linux x86-64, ROS Noetic 컨테이너, 4 CPU 제한·8 GiB, 1배속이며 방법별 1회 실행했다.

아래 오차는 출력 IMU 원점을 LiDAR 원점으로 변환하고, 세 완주 방법에 공통인 기준 시각 1,248개에 보간한 결과다. 1,251개 기준점의 99.76%를 포함한다. 위치는 선형 보간, 자세는 quaternion SLERP이며 외삽하거나 0.2초보다 긴 출력 공백을 연결하지 않았다. 고정 scale=1의 SE(3) 정렬을 사용했다.

| 방법 | 완주 | 위치 RMSE | 높이 RMSE | 자세 RMSE | 평균 CPU | 최대 RSS 합계 |
|---|---|---:|---:|---:|---:|---:|
| 공식 GaRLIO | 성공 | 2.974 cm | 1.701 cm | 0.2274° | 115.85% | 1,593 MiB |
| JURLIO baseline | 성공 | 2.863 cm | 1.610 cm | 0.2230° | 72.99% | 271 MiB |
| JURLIO robust | 성공 | 2.818 cm | 1.538 cm | 0.2211° | 75.59% | 267 MiB |
| JURLIO dynamic | 실패 | 전체 구간 비교 불가 | — | — | 비교에서 제외 | — |

robust의 위치 RMSE는 GaRLIO보다 약 5.2%, **절대값으로 1.56 mm** 작다. baseline과의 차이는 0.45 mm다. 한 시퀀스·한 번의 실측 실행이며 기준 궤적도 오차가 있으므로 확실한 성능 우위로 해석하지 않는다. 최대 위치 오차는 세 방법 모두 약 **39 cm**로, 평균만으로 순간적인 오차를 숨기면 안 된다.

세 완주 방법은 각각 1,817개 pose를 생성했다. 마지막 출력은 마지막 기준 센서 시각과 거의 일치했고, 최대 pose 간격은 약 0.310초였다. 모든 원시 메시지가 내부에서 무손실 처리됐다는 보증은 아니다.

CPU는 `cloudProcess + lidarMapping` 두 프로세스의 활성 재생 중 평균이며 한 논리 코어가 100%다. 초기 3초와 종료 후 drain을 제외했다. RSS 합계는 공유 페이지를 중복 계산할 수 있다. GaRLIO와 JURLIO는 OpenMP 설정과 기존 메모리 관리가 다르므로 CPU·메모리 차이를 robust 알고리즘 하나의 효과라고 할 수 없다. robust는 JURLIO baseline보다 CPU를 약 2.6%p 더 사용했다.

### 처음 안내한 5.4 cm와 다른 이유

기존 평가기는 50 ms 이내의 가장 가까운 시각을 일대일로 연결한다. 출력은 약 15 Hz, 기준 궤적은 약 10 Hz여서 시간 차이로 인한 이동량도 오차에 섞였다. 이 기존 방식의 결과는 GaRLIO **5.367 cm**, baseline **5.336 cm**, robust **5.314 cm**다. 원래 `metrics.json`은 그대로 보존했다.

시간을 맞춘 표는 별도 `common_reference_metrics`다. 데이터를 골라 오차를 줄인 것이 아니라 세 방법에 같은 기준 시각·보간 제한을 적용했다. 두 평가 방식을 혼용하지 않는다. real 그래프는 공통 시각 평가를 표시하고, synthetic 그래프는 기존 연결 방식을 표시한다.

### 기준 궤적의 의미

공식 `fwd_bwd_loc/20231105/data6/ref_tls_T_xt32.csv`에서 시간·위치·quaternion 8열을 사용했다. 이는 XT32 원점의 TLS 지도 기반 전후방 LIO 평균 궤적이며, 오차 없는 절대 정답은 아니다. 공식 설명은 [기준 궤적 문서](https://snail-radar.github.io/docs/groundtruth.html)에 있다. 함께 배포된 전후방 편차의 위치 중앙값은 약 6.62 mm, 최대는 30.88 mm였다. 이 편차를 기준 궤적의 보장 오차 상한으로 해석하지 않는다.

## dynamic 실패와 의미

| 재생 속도 | 마지막 위치 출력: bag 시작 후 | 종료 전 관측한 센서 시간 | 연속 레이더 거부 최대 |
|---|---:|---:|---:|
| 1배속 | 38.280초 | 49.128초 | 162프레임 |
| 0.5배속 진단 재실행 | 42.952초 | 53.402초 | 154프레임 |

두 실행 모두 `LiDAR synchronization backlog exceeded 2M points`로 보호 종료됐다. 절반 속도에서도 재현되므로 단순한 처리량 부족으로 설명하기 어렵다. 실패 시점은 스케줄링과 입력 수신 시점에 따라 달랐다.

코드와 로그에서 확인한 연결은 다음과 같다.

1. `pointProcess.cpp::prepare_velocity_prior()`는 과거 융합 속도로 현재 레이더 후보를 제한한다. 기본 유효기간은 0.35초다.
2. `radar_ego_velocity_estimator.cpp`는 prior를 받은 이후 prior가 만료되면 `stale_or_missing_prior`로 거부한다. 잘못된 동적 다수결을 정적으로 받아들이지 않으려는 보수적 설계다.
3. 거부된 레이더는 `filtered_points`를 발행하지 않는다. `lidarMapping.cpp::sync_messages()`는 레이더가 없으면 진행하지 않는다.
4. 새 융합 위치가 나오지 않으면 `publish_odometry()`의 새 prior도 나오지 않는다. **거부 → 갱신 정지 → prior 만료 → 지속 거부**가 된다.
5. LiDAR 입력은 계속 쌓여 200만 점 제한에 도달한다.

이번 비교에서는 보호 제한이나 prior 검사를 없애서 완주시키지 않았다. 다음 개선 후보는 **레이더 측정의 채택 여부와 필터의 시간 진행을 분리**하고, 불확실성을 포함한 IMU 예측·LiDAR 갱신 또는 보수적 재초기화로 복구 경로를 만드는 것이다. GaRLIO 스윕 구성과 중력 보정이 레이더에 의존하므로 동기화 조건 한 줄만 삭제해서는 안 된다. 해당 복구 기능은 아직 구현·검증하지 않았다.

## 합성 센서 시험

12초 동안 정적인 방에서 자세를 고정하고 직선 이동하는 결정적 입력이다. 레이더 Doppler에 인공 이상치 20%를 넣었다. 물리적인 군중·차량 움직임이나 센서 잡음을 충실하게 재현한 시험은 아니다. 2 CPU·6 GiB·1배속으로 방법별 3회 실행했다.

| 방법 | 위치 RMSE 평균 | 자세 RMSE 평균 | 높이 RMSE 평균 | 평균 CPU |
|---|---:|---:|---:|---:|
| GaRLIO | 3.662 mm | 0.02829° | 1.162 mm | 39.73% |
| JURLIO baseline | 3.676 mm | 0.02752° | 1.073 mm | 19.78% |
| JURLIO robust | 3.537 mm | 0.03085° | 1.263 mm | 19.94% |
| JURLIO dynamic | 3.537 mm | 0.03085° | 1.263 mm | 19.92% |

정렬 없이 계산했으며 각 실행은 116개 pose를 생성했다. 3회 결과 차이는 표시 정밀도보다 작다. robust·dynamic의 위치 오차는 조금 작지만 자세·높이 오차는 더 컸다. 이 단순 시험의 성공만으로 실제 환경에서 dynamic이 안전하다고 판단할 수 없다는 점이 실측 실패로 확인됐다.

최초 GaRLIO 3회는 컨테이너 내부 Git 소유권 검사에서 실행 전에 실패했다. 컨테이너 안 임시 HOME에만 `safe.directory`를 지정한 후 재실행해 성공했다. 원래 실패 로그를 보존했다. 재생성한 합성 bag의 SHA-256은 원래 bag과 동일하다: `fb1ade8fae07d3014f5a2e89c139fb68d2d7e633ad9c6f40e7abe4f90c8acb4d`.

## 구조를 단계별로 읽는 방법

| 단계 | 하는 일과 필요한 이유 | 주요 파일 |
|---|---|---|
| 1. 데이터 준비 | 센서 기록의 값과 시각을 유지한 채 ROS bag으로 묶는다. LiDAR·레이더·IMU 사이 좌표 변환도 같은 시퀀스의 보정값에서 얻는다. | JURLIO `scripts/snail_subset_bag.py`, `scripts/calibrate.py`, 생성 `data6.yaml` |
| 2. 전처리 | LiDAR 점별 시각과 유효 점을 읽고, 레이더 Doppler로 자차 속도와 inlier/outlier를 구한다. 움직이는 물체가 자기 속도로 오인되는 일을 줄이는 단계다. | 양쪽 `src/pointProcess.cpp`, `src/radar_ego_velocity_estimator.cpp`; JURLIO `include/robust_velocity.hpp`, `include/dynamic_velocity.hpp` |
| 3. 시간 정합·IMU | 레이더 시각에 맞춰 LiDAR 구간과 IMU를 모은다. IMU로 위치·자세를 예측하고, 스캔 중 움직임에 따른 점군 왜곡을 보정한다. | `src/lidarMapping.cpp::sync_messages()`, `src/imuProcess.hpp` |
| 4. 필터 보정 | LiDAR 점과 지도 평면의 거리, 점별 Doppler를 이용해 예측을 수정한다. 추가 속도·중력 보정은 자세 오차와 높이 드리프트를 줄이려는 구조다. | `src/lidarMapping.cpp::processIESKF()`, `include/filter_state.hpp`, `include/S2.hpp` |
| 5. 지도·출력 | 보정된 점을 ikd-Tree 지도에 추가하고 위치·자세와 경로를 ROS 토픽에 보낸다. | `map_incremental()`, `publish_odometry()`, `include/ikd-Tree/`; `/aft_mapped_to_init`, `/aft_mapped_path` |
| 6. 기록·평가 | TUM 궤적, CPU, 오류, 설정·소스 hash를 저장하고 같은 좌표 원점·시각에서 비교한다. | GaRLIO `scripts/run_sensor_comparison.py`, `run_experiment.py`, `plot_sensor_comparison.py`, `interpolate_trajectory.py`; JURLIO `scripts/run_replay.py`, `evaluate.py` |

표의 `src/`, `include/`는 각 저장소 루트이며 GaRLIO의 실험 스크립트는 `research_ws_gpt/scripts/` 아래다. 논문의 동기는 [GaRLIO IV-A~D와 V-E](https://arxiv.org/html/2502.07703v2), 구현과의 차이는 [design_rationale.md](design_rationale.md)에 정리돼 있다. 이번에는 Doppler·중력 보정·동적 점 처리를 빌드 편의로 제거하지 않았다.

PCD 지도 파일 저장은 공통 설정에서 꺼져 있다. 저장된 GIF는 **계산한 궤적을 약 10배속으로 보여주는 재생 영상**이며, 카메라 영상이나 3D 지도 영상이 아니다. 지도 구축은 추정 과정 내부에서 실행됐다.

## 소스·데이터·검증 기록

- 공식 GaRLIO: `ff4dfefad2cbd3333824c518d5652f1bf9a5039b`. 현 GaRLIO fork의 핵심 패키지 파일 31개가 이미지 원본과 일치함을 확인했다. 별도 개선 알고리즘의 효과를 비교한 것이 아니다.
- JURLIO 실행 바이너리: `465a53870768539213780a502463e3ba0ccc47cb`. baseline에도 기존 공통 mapper 수정이 포함되어 원본 GaRLIO와 같지 않다. 별도 Point-LIO 패키지는 실행하지 않았다.
- 기존 Linux 빌드 로그와 이미지 소스 hash를 검증하고 이미지 ID를 고정해 재사용했다. 이번 Python 도구 변경 때문에 동일한 C++를 다시 빌드하지 않았다. GaRLIO 이미지 ID는 `sha256:b2fe475d60b79bd748da294ddd7a774808ecac0e5f2c3638a6be7365f19383d4`, JURLIO는 `sha256:33fbde250ba9c753d30da4394e56b6ae2c716e3685ec644878491c0864c51c14`다.
- `data6.zip`: 1,808,391,791 bytes. 공식 MD5 `97450c91bc7f884898f0e34e238dc061` 일치. 배포 수정일 2025-08-02. 시각 보정을 중복 적용하지 않았다. bag에는 LiDAR 1,261·레이더 1,822·IMU 11,200 메시지가 들어 있다.
- 공식 [dataset_tools](https://github.com/snail-radar/dataset_tools) `d2498a14756c59fc60213518f242cf95b9db991a`의 파서와 LiDAR·레이더 각각 첫·중간·마지막 프레임의 모든 점·필드 값을 대조해 일치했다. 전체 원본 PCD와 IMU 파일 hash도 보존했다.
- ROS 컨테이너에서 GaRLIO harness Python 31개, JURLIO Python 17개 통과. JURLIO C++ 수치 검사 7개를 다시 실행해 통과했다. 300개 RANSAC 인공 사례와 Doppler Jacobian 유한차분 900회도 포함한다. 단위 시험 성공은 dynamic의 실측 실패를 상쇄하지 않는다.

## 결과 파일과 재실행

두 저장소를 포함한 `lio` 작업 폴더 기준 `output/simulation_comparison_2026-10-21/`에 보존했다. 대용량 데이터는 Git에 넣지 않았다.

```text
real_data/                  원본 zip, 변환 bag, 시퀀스 보정, 기준 궤적, 변환 검증
comparison/                 최초 합성 비교: JURLIO 9회 성공, GaRLIO 준비 단계 실패
garlio_retry/               Git 소유권 설정 후 GaRLIO 합성 3회 성공
real_comparison/            실측 네 모드의 설정·명령·로그·CPU·궤적·기존 metrics
dynamic_half_rate/          dynamic 0.5배속 실패를 보존한 진단 실행
dynamic_failure_diagnosis.json  두 실패의 시각·pose 수·레이더 거부 사유
figures/                   PNG/PDF 비교 그래프, 궤적 GIF, summary.json
host.json                  호스트 정보
numeric_tests.log           Linux C++ 수치 검사 결과
plot_requirements.txt      사용한 분석 환경 패키지 목록
```

`real_comparison/source_snapshot/`에 실행 당시 스크립트·launch를 복사했다. `source_hashes.json`, `images.json`, `commands.json`, `experiment.json`, 실행별 `run.json`/`meta.json`으로 입력·코드·환경을 구분할 수 있다. `summary.json`은 실패 시도를 성공 평균에 넣지 않으며, 전체 결과 표와 공통 시각 평가를 포함한다.

같은 이미지와 데이터를 보유한 Linux 호스트에서, `lio` 폴더를 현재 위치로 하여 실행한다. Docker 접근이 이미 가능한 셸이면 `sg docker -c` 없이 아래 Python 명령을 사용한다. 새 출력 폴더가 필요하다.

```bash
python3 GaRLIO/research_ws_gpt/scripts/run_sensor_comparison.py \
  --jurlio-root jurlio --output output/new-comparison \
  --bag output/simulation_comparison_2026-10-21/real_data/data6_sensors.bag \
  --config output/simulation_comparison_2026-10-21/real_data/data6.yaml \
  --groundtruth output/simulation_comparison_2026-10-21/real_data/reference_lidar.tum \
  --runs 1 --cpus 4 --memory 8g --rate 1
```

`--bag/--config/--groundtruth`를 모두 생략하면 합성 bag을 만든다. `--methods dynamic --rate 0.5`는 실패 진단의 재생 조건이다. 바이너리 입력 소스와 로컬 소스가 다르면 runner는 중단하므로 C++ 변경 후에는 이미지를 다시 빌드해야 한다. 원본 GaRLIO와 다른 fork 알고리즘 비교에는 별도 fork 이미지 실행 경로를 사용해야 한다.

이번 변경은 Hesai 입력 사전 검사, 동일 조건 실행·시간 기록, 공식 파일의 bag 변환, 공통 시각 평가와 그림 생성이다. **새 알고리즘을 구현해 성능을 올렸다는 변경이 아니다.** 실측 여러 시퀀스 반복, 동적 장면 성능, 레이더 단절 복구, NTU/Point-LIO 비교는 남아 있다.
