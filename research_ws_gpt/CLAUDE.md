# 연구 프로젝트: Radar-aided Point-LIO (Point-LIO × GaRLIO)

이 파일은 이 저장소에서 일하는 코딩 에이전트를 위한 작업 지시서다. 매 세션 시작 시 이 파일과 `docs/progress.md`를 먼저 읽고, 지난번에 어디까지 했는지 확인한 뒤 이어서 진행한다.

---

## 0. 역할과 작업 원칙

너는 로봇 상태추정(LiDAR-Inertial Odometry) 연구를 돕는 엔지니어다. 사용자와는 **한국어**로 소통한다.

반드시 지킬 원칙:

1. **수치를 지어내지 않는다.** 실행하지 않은 실험의 결과를 추정해서 쓰지 않는다. 데이터셋이 없거나 실행이 불가능하면, 사용자가 실행할 명령과 결과 파일 위치를 알려주고 결과를 받은 뒤 분석한다.
2. **가설과 사실을 구분한다.** 문서와 보고에서 "실험으로 확인됨", "코드/논문에서 확인됨", "가설"을 명시적으로 표기한다.
3. **체크포인트에서 멈춘다.** 각 Phase 끝의 `[CHECKPOINT]`에서 결과를 요약 보고하고, 사용자 승인 후 다음 Phase로 넘어간다.
4. **코드 수정 전에 읽는다.** 어떤 모듈을 고치거나 이식하기 전에 관련 소스를 읽고, 이해한 내용(데이터 흐름, 상태 정의, 좌표계)을 먼저 요약한다.
5. **진행 기록을 남긴다.** 작업 단위마다 `docs/progress.md`에 날짜, 한 일, 결정 사항, 남은 문제를 적고 git commit 한다.
6. **오래 걸리는 실험은 스크립트로 넘긴다.** bag 재생처럼 수십 분 걸리는 작업은 백그라운드 실행 스크립트(로그 포함)로 만들어 사용자에게 실행 방법을 안내하고, 끝난 뒤 결과 파일을 분석한다.

---

## 1. 연구 질문

**Q1 (검증)**: GaRLIO 논문(ICRA 2025)에서 NTU4DRadLM의 `nyl` 시퀀스만 Point-LIO가 GaRLIO보다 좋았다. 논문은 그 이유를 "핸드카트 진동 + Point-LIO가 가속도·각속도를 상태로 추정(IMU를 관측으로 다루는 출력 모델)"이라고 설명하지만 실험 근거는 없다. 이 설명이 맞는가?

**Q2 (확장)**: Point-LIO(출력 모델 + 점 단위 갱신)를 기반으로 GaRLIO의 레이더 기능 세 가지(레이더 기반 동적 물체 제거, 점별 도플러 속도 잔차, 속도 기반 중력 잔차)를 얹으면, 느리고 진동이 큰 조건(핸드카트)과 빠르고 고저차가 큰 조건(차량) 모두에서 두 원본 방법보다 나은가?

**Q3 (분석)**: 각 기능은 어떤 조건(속도, 진동, 고저차, 동적 물체)에서 효과가 있고, 어디서 효과가 없거나 해로운가?

**최종 관심**: 저속 지상 로봇에 적용할 때 어떤 구성을 택해야 하는가. 로봇에 4D 레이더가 없을 수도 있으므로, 새 시스템은 **레이더 없이도 순수 Point-LIO로 정상 동작**해야 한다.

---

## 2. 이미 확인된 사실 (소스 코드와 논문에서 직접 확인함)

### 2.1 GaRLIO (https://github.com/ChiyunNoh/GaRLIO, commit `ff4dfefad2cbd3333824c518d5652f1bf9a5039b`)

- ROS1 Noetic / catkin / C++17. 의존성: PCL, OpenCV, Ceres, `livox_ros_driver`.
- 노드 2개:
  - `cloudProcess` (`src/pointProcess.cpp`, `src/radar_ego_velocity_estimator.cpp`): LiDAR·레이더 전처리, 레이더 ego-velocity 추정(REVE 기반 3-point RANSAC-LSQ), 레이더 시각 기준 스윕 재구성. `/laser_cloud_surf`, `/filtered_points`, `/eagle_data/inlier_pc2`, `/eagle_data/outlier_pc2`, `/eagle_data/twist` 발행.
  - `lidarMapping` (`src/lidarMapping.cpp`, `include/filter_state.hpp`, `include/S2.hpp`, `src/imuProcess.hpp`): Invariant EKF(right-invariant error) 기반. 1단계 갱신(point-to-plane + 점별 도플러 속도 잔차), 2단계 갱신(속도 기반 중력 잔차, S2 매니폴드).
- `sync_messages()`가 IMU·LiDAR·레이더 버퍼가 **모두** 차야 진행한다. 레이더가 없으면 에러 없이 아무것도 출력하지 않는다.
- config의 `pcd_save/traj_save_path`가 원저자 PC 경로(`/home/vdcl/Downloads/PCD`)로 하드코딩되어 있다. 고치지 않으면 `garlio_mapped.txt`가 저장되지 않는다.
- 레이더 타입: `radar_type 0` = `sensor_msgs/PointCloud`(NTU의 `/radar_enhanced_pcl`), `1` = `PointCloud2`.

### 2.2 Point-LIO (https://github.com/hku-mars/Point-LIO, commit `4b86a469eb5572e70ed575af25b5f15dd06e8e3c`)

- ROS1 catkin, IKFoM(ESIKF on manifolds) 기반. `livox_ros_driver` 의존.
- `include/common_lib.h`:
  - `state_output` = pos, rot, offset_R_L_I, offset_T_L_I, vel, **omg, acc**, **gravity**, bg, ba
  - `state_input` = pos, rot, offset_R_L_I, offset_T_L_I, vel, bg, ba, gravity
- 파라미터 `use_imu_as_input` (기본 0 = 출력 모델, 1 = FAST-LIO2와 같은 입력 모델). 이 스위치 하나로 IMU 모델만 바꾸고 나머지(점 단위 갱신, iVox 맵 등)는 그대로 유지할 수 있다. **Q1 검증의 핵심 도구.**
- Livox Horizon용 설정 `config/horizon.yaml`, `launch/mapping_horizon.launch` 제공 (`acc_norm: 1.0` = g 단위, `imu_meas_acc_cov/omg_cov: 0.01`, `satu_acc: 3.0`, `satu_gyro: 35`).
- 오도메트리 토픽: `/aft_mapped_to_init` (nav_msgs/Odometry).
- 주요 파일: `src/laserMapping.cpp`(메인 루프, 시간순 측정 처리), `src/Estimator.cpp/.h`(측정 모델·자코비안), `src/IMU_Processing.cpp`, `src/parameters.cpp`, `src/preprocess.cpp`.

### 2.3 FAST-LIO2 (https://github.com/hku-mars/FAST_LIO, commit `7cc4175de6f8ba2edf34bab02a42195b141027e9`)

- ROS1 catkin, `livox_ros_driver` 의존. **`include/ikd-Tree`가 git submodule**이므로 `--recursive`로 받아야 한다.
- `config/horizon.yaml` 제공 (`mapping/acc_cov: 0.1`, `gyr_cov: 0.1`).
- 오도메트리 토픽: `/Odometry`.

### 2.4 데이터셋: NTU4DRadLM (https://github.com/junzhang2016/NTU4DRadLM)

- 토픽: `/livox/lidar` (livox_ros_driver/CustomMsg, Livox Horizon), `/livox/imu` (Livox 내장 IMU), `/radar_enhanced_pcl` (sensor_msgs/PointCloud, Oculii Eagle 4D 레이더), `/vectornav/imu` (VectorNav VN100, 교차 검증용).
- 시퀀스 폴더마다 `gt_odom.txt`, `calib/`에 외부 보정값. **`gt_odom.txt`의 열 순서와 기준 좌표계는 아직 확인 안 됨** → Phase 1에서 직접 확인하고 문서화할 것.
- 논문 기준 플랫폼: cp, nyl = 핸드카트(저속, 진동), loop2, loop3 = 차량(고속, 고저차). garden, loop1은 논문 미사용.
- 데이터 위치(사용자 PC): `~/datasets/NTU4DRadLM/{cp,garden,nyl,loop1,loop2,loop3,calib}/`

### 2.5 논문 기준 수치 (재현 목표, ATE RMSE: 이동 m / 회전 deg, evo 사용)

| 시퀀스 | FAST-LIO2 | Point-LIO | DLIO | GaRLIO |
|---|---|---|---|---|
| cp | 0.103 / 0.574 | 0.162 / 0.706 | 0.174 / 1.697 | 0.107 / 0.750 |
| nyl | 1.259 / 0.996 | **0.507 / 0.722** | 1.214 / 1.688 | 0.973 / 1.454 |
| loop3 | 11.94 / 1.714 | 9.548 / 2.082 | 8.332 / 2.101 | **4.271 / 1.496** |
| loop2 | 15.81 / 2.176 | 20.27 / 4.188 | 10.38 / 2.525 | **3.976 / 1.043** |

GaRLIO ablation (ATE 이동 m; g = 중력 잔차, v = 속도 잔차, d = 동적 제거):

| 변형 | cp | loop3 | loop2 | nyl |
|---|---|---|---|---|
| w/o g&v&d | 0.101 | 12.44 | 9.163 | 1.281 |
| w/o g&v | 0.115 | 10.83 | 8.573 | 1.280 |
| w/o g | 0.107 | 9.952 | 5.985 | 1.135 |
| w/o v | 0.098 | 11.28 | 11.17 | 0.991 |
| FULL | 0.107 | 4.271 | 3.976 | 0.973 |

여기서 읽히는 것 (논문 수치에서 확인됨, 원인은 가설):
- IMU 입력 모델 필터 세 개(FAST-LIO2, DLIO, GaRLIO 기본형)가 nyl에서 1.2~1.3 m에 모이고 Point-LIO만 0.5 m.
- 저속(cp, nyl)에서는 GaRLIO의 레이더 기능 효과가 미미하고, 고속(loop2, loop3)에서 크다.
- **속도 잔차 없이 중력 잔차만 넣으면 loop2/loop3에서 오히려 나빠진다** (w/o v vs w/o g&v). 중력 잔차는 속도 잔차에 의존한다.
- 논문은 베이스라인 파라미터 설정과 반복 실행 횟수를 밝히지 않았다.

---

## 3. 저장소 구조 (목표)

```
research_ws/
├── CLAUDE.md                     # 이 파일
├── docker/
│   ├── ros/Dockerfile            # Noetic + 모든 알고리즘 빌드 (기존 garlio_docker 확장)
│   ├── analysis/Dockerfile       # Python 3.11 + evo + rosbags + numpy/scipy/pandas/matplotlib
│   └── run.sh                    # 컨테이너 실행 (X11, 데이터 마운트)
├── catkin_ws/src/
│   ├── livox_ros_driver/         # 고정 커밋
│   ├── garlio/                   # 업스트림 그대로 (경로 패치만)
│   ├── FAST_LIO/                 # 업스트림 그대로
│   ├── Point-LIO/                # 업스트림 그대로
│   └── radar_point_lio/          # ★ 우리 패키지 (Point-LIO 포크)
├── configs/<method>/<seq>.yaml   # 방법·시퀀스별 설정 (외부 보정값은 공통 파일에서)
├── scripts/
│   ├── record_traj.py            # 임의 Odometry 토픽 → TUM 파일
│   ├── run_experiment.sh         # (method, seq, config, N회) 일괄 실행 + 로그
│   ├── convert_gt.py             # gt_odom.txt → TUM
│   ├── evaluate.py               # evo로 ATE(이동/회전/z) 계산, 표·그림 생성
│   └── imu_vibration.py          # IMU 진동 스펙트럼 분석
├── results/<exp_id>/<method>/<seq>/run_<k>.tum + meta.json
└── docs/
    ├── progress.md
    ├── derivation_doppler.md     # 도플러 잔차 측정모델·자코비안 유도
    ├── design_gravity.md         # 중력 잔차 설계안 (승인 필요)
    └── report.md                 # 최종 보고서
```

업스트림 저장소는 **직접 수정하지 않는다**(GaRLIO의 `traj_save_path` 경로 패치만 예외). 우리 구현은 전부 `radar_point_lio`에 둔다. `meta.json`에는 git 커밋 해시, 사용한 config 전문, bag 재생 속도, 실행 시각, 머신 정보를 기록한다.

---

## 4. 단계별 작업

### Phase 0: 환경 구축

1. `docker/ros/Dockerfile`: `osrf/ros:noetic-desktop-full` 기반. Livox-SDK → livox_ros_driver → GaRLIO, FAST_LIO(`--recursive`), Point-LIO를 2.x절의 커밋으로 고정해 한 catkin 워크스페이스에서 `catkin build`. Noetic은 EOL이므로 ROS apt 저장소에 의존하지 않도록 한다(추가 패키지는 Ubuntu 저장소와 pip에서).
2. `docker/analysis/Dockerfile`: Python 3.11. `evo`(Python ≥3.10 필요하므로 ROS 컨테이너에 넣지 않음), `rosbags`(ROS 없이 bag 읽기), numpy, scipy, pandas, matplotlib.
3. `scripts/record_traj.py`: 토픽 이름을 인자로 받아 Odometry를 TUM(`t x y z qx qy qz qw`, 메시지 header 시각)으로 저장. 세 알고리즘 모두 이 스크립트로 기록해 형식을 통일한다.
4. `scripts/run_experiment.sh`: roslaunch → 대기 → `rosbag play -r <rate>` → 종료 → 결과·meta 저장을 N회 반복. 기본 재생 속도는 모든 방법에 동일하게 `-r 0.5`(실시간 처리 누락 방지). 실행마다 CPU 사용률도 기록.

`[CHECKPOINT 0]` 빌드 성공 여부, 각 패키지 실행 확인(짧은 bag 일부로 토픽 발행 확인), 남은 문제 보고.

### Phase 1: 베이스라인 재현

1. `gt_odom.txt` 형식 확인 → `convert_gt.py` 작성. GT 기준 프레임과 IMU 프레임의 차이(레버암)가 있으면 문서화.
2. 외부 보정값은 NTU `calib/`에서 읽어 세 방법에 **동일하게** 적용. 각 방법의 공식 Horizon 설정을 출발점으로 하고, 바꾼 파라미터는 전부 `configs/`와 보고서에 기록.
3. FAST-LIO2, Point-LIO, GaRLIO × {cp, nyl, loop2, loop3} × N=5회 실행.
4. `evaluate.py`: evo로 SE(3) 정렬 후 ATE RMSE(이동 m, 회전 deg) + **z축 오차**(정렬 후 높이 차이의 RMSE, 별도 계산). 시퀀스별 평균 ± 표준편차, 개별 실행값 전부 표로 출력.

`[CHECKPOINT 1]` 논문 수치와의 비교표. 재현이 안 되는 항목은 가능한 원인을 가설로 제시(설정 차이, 재생 속도, 실행 편차 등).

### Phase 2: Q1 검증 (nyl에서 Point-LIO가 이긴 이유)

| 실험 | 내용 | 판정 기준 |
|---|---|---|
| H1 IMU 모델 | Point-LIO `use_imu_as_input` 0 vs 1, nyl·cp·loop2, N=5 | 1로 바꿨을 때 nyl 오차가 IMU 입력 모델 필터 수준(약 1.2 m)으로 올라가면 논문 설명 지지. 0.5 m대 유지되면 원인은 점 단위 갱신 등 다른 요소 |
| H2 진동량 | `imu_vibration.py`: 시퀀스별 가속도·각속도의 Welch PSD, 대역 에너지(예: 5–20, 20–50, 50 Hz–Nyquist), 속도 구간별 비교. `/vectornav/imu`로 교차 확인 | nyl의 고주파 에너지가 cp·loop2보다 뚜렷이 크지 않으면 "진동 때문" 설명 약화 |
| H3 노이즈 공분산 | FAST-LIO2 `acc_cov`, `gyr_cov`를 여러 배율로 키워 nyl 실행 | 진동이 원인이면 공분산을 키울수록 일부 개선되어야 함 |
| H4 실행 편차 | Phase 1 결과의 반복 실행 표준편차 | 방법 간 차이가 편차 대비 충분히 큰지 |

유의성 규칙: 두 설정의 평균 차이가 두 표준편차 중 큰 값의 2배를 넘지 않으면 "차이 없음"으로 보고한다. 이 규칙은 모든 Phase에 적용.

`[CHECKPOINT 2]` H1~H4 결과와 Q1에 대한 결론(지지 / 기각 / 판단 불가) 보고.

### Phase 3: radar_point_lio 구현

Point-LIO를 `radar_point_lio`로 포크한다. 모든 기능은 config 플래그로 켜고 끈다: `radar/enable`, `radar/dynamic_removal`, `radar/doppler_residual`, `radar/gravity_residual`. **레이더 토픽이 없거나 `radar/enable: false`면 원본 Point-LIO와 동일하게 동작**해야 하며, 이를 회귀 테스트로 확인한다(같은 bag에서 원본과 궤적 비교).

**3a. 레이더 전처리 + 동적 물체 제거**
- GaRLIO의 `pointProcess.cpp`(레이더 핸들러), `radar_ego_velocity_estimator.*`를 읽고, 레이더 부분만 독립 노드(`radar_preproc`)로 이식: 정적 점(도플러 포함) / 동적 점 분리, ego-velocity 발행. `/filtered_points`와 `/eagle_data/*`가 정확히 무엇을 담는지 코드에서 확인 후 기록.
- LiDAR 동적 제거: GaRLIO 방식(레이더 동적 점과 LiDAR 점을 XY 평면에 투영, 레이더 점 불확실성 기반 Mahalanobis 거리 임계값). Point-LIO의 입력 스캔 단계에서 적용. 레이더·LiDAR 시각이 다르므로 사용한 시간 정합 방식과 근사를 문서화.

**3b. 점별 도플러 속도 잔차**
- GaRLIO 논문 식 (10)~(11)과 `lidarMapping.cpp` 구현을 읽고, Point-LIO의 상태 정의와 오차 정의(IKFoM 매니폴드 오차, GaRLIO는 right-invariant 오차)에 맞게 측정 모델과 자코비안을 **다시 유도**해 `docs/derivation_doppler.md`에 쓴다.
- 출력 모델에서는 각속도 `omg`가 상태이므로 레버암 항(ω × p_R)의 자코비안이 `omg`에도 걸린다. 입력 모델용도 가능하면 함께 구현(레버암 항은 IMU 측정값 − bias 사용).
- 레이더 프레임 시각에 맞춰 Point-LIO의 시간순 측정 처리 흐름에 비동기 갱신으로 넣는다(스윕 재구성 불필요).
- 이상치 가중: GaRLIO처럼 ego-velocity 대비 modified z-score로 점별 공분산 조정.
- **유한차분 수치 자코비안과 해석 자코비안을 비교하는 단위 테스트 필수.**

**3c. 속도 기반 중력 잔차 — 구현 전 설계 승인 필요**
- `docs/design_gravity.md`에 다음을 분석해 설계안을 쓰고 `[CHECKPOINT 3c]`에서 멈춘다.
  - Point-LIO는 중력을 상태로 추정하고, GaRLIO는 초기 중력을 고정 기준으로 두고 roll/pitch를 보정한다. 중력이 자유 상태면 roll/pitch 오차가 중력 방향 추정으로 흡수될 수 있다. 관측성 관점에서 어느 쪽이 맞는지.
  - 선택지 예: (A) 중력 상태 유지 + 속도 기반 중력 추정치를 의사 측정으로 추가, (B) 초기화 후 중력 고정(또는 강한 prior) + GaRLIO식 S2 잔차로 roll/pitch 제약.
  - β(레이더 프레임 간 IMU 사전적분)를 출력 모델에서 무엇으로 계산할지(원시 IMU vs 추정 `acc` 상태).
- 제약: **중력 잔차는 도플러 잔차가 켜져 있을 때만 활성화** (논문 ablation 근거). 플래그 조합이 이를 어기면 경고 후 비활성화.

각 하위 단계마다 nyl(저속)과 loop2(고속)에서 N=5회 실행해 직전 단계와 비교하고 `progress.md`에 기록한다.

`[CHECKPOINT 3a]`, `[CHECKPOINT 3b]`, `[CHECKPOINT 3c 설계]`, `[CHECKPOINT 3c 구현]`에서 각각 보고.

### Phase 4: Ablation과 보고서

1. 변형: Point-LIO 원본 / +d / +d+v / +d+v+g, 그리고 같은 조합의 `use_imu_as_input=1` 버전(결합 시스템에서도 출력 모델이 의미가 있는지 확인). 비교 대상: FAST-LIO2, Point-LIO, GaRLIO.
2. 과적합 방지: 파라미터 튜닝은 cp, garden(+ 필요시 loop1 일부)에서만 하고, nyl, loop2, loop3는 **평가 전용**으로 둔다. 튜닝에 쓴 시퀀스와 시도 횟수를 기록한다.
3. 선택: Snail-Radar `sl` 시퀀스로 일반화 확인 (Hesai LiDAR, PointCloud2 레이더; GaRLIO `config/sl.yaml` 참고).
4. `docs/report.md`: 연구 질문별 결론, 표(평균 ± 표준편차), 궤적·z 오차 그림, 실패 사례, 한계, 저속 지상 로봇에 대한 권고. 각 주장 옆에 근거 유형(실험 / 코드 / 논문 / 가설) 표기.

`[CHECKPOINT 4]` 최종 보고.

### Phase 5 (사용자 요청 시): 실제 로봇 적용

사용자 로봇의 센서 구성(LiDAR 기종, IMU, 레이더 유무, 주행 속도, 환경)을 받아 config 템플릿과 외부 보정·시간 동기화 체크리스트를 만든다.

---

## 5. 하지 말 것

- 실행하지 않은 실험의 수치를 쓰거나, 단일 실행 결과로 우열을 주장하기.
- 베이스라인을 기본값 그대로 두고 우리 방법만 튜닝하기. 튜닝 예산은 공정하게, 모든 변경은 기록.
- 평가 전용 시퀀스(nyl, loop2, loop3)로 파라미터 튜닝하기.
- 업스트림 저장소(GaRLIO, Point-LIO, FAST_LIO) 직접 수정.
- 센서 데이터가 빠졌을 때 조용히 멈추거나 조용히 건너뛰기. 반드시 경고 로그를 남긴다.
- 체크포인트를 건너뛰고 다음 Phase 진행.
- 자코비안을 수치 검증 없이 사용.
