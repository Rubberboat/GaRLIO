# 연구 프로젝트: GaRLIO 기반 확장 gpt

이 파일은 현재 작업 지침이다. 매 세션 이 파일과 [진행 기록](docs/progress.md)을 읽고 이어서 작업한다. 2026-10-20 사용자의 “따로 fork한 GaRLIO에서 GaRLIO 베이스에 추가하면서 개선” 요청을 반영했다. 이전 Point-LIO 기반 계획은 [원문 보관본](docs/point_lio_plan_original.md)에 남겼으며, 현재 구현 방향은 이 파일을 따른다.

## 0. 개발 기준

1. **개선 대상은 `Rubberboat/GaRLIO` 루트의 GaRLIO 코드다.** `src/`, `include/`, `config/`, `launch/`, `CMakeLists.txt`, `package.xml`에 필요한 변경을 더한다. ROS 패키지 이름 `garlio`와 원작 표기를 유지한다.
2. GaRLIO의 IMU 전파, 레이더 시각 기준 스윕 구성, LiDAR scan-to-map, Doppler 제약, 중력 보정을 출발점으로 삼는다. 새 기능은 하나씩 추가하고 기능별 비교가 가능하도록 구성한다.
3. 원본 비교 소스는 `research_ws_gpt/sources.lock.json`의 SHA로 고정한다. `catkin_ws/src/garlio`, `FAST_LIO`, `Point-LIO`와 Livox 의존성은 직접 수정하지 않는다. 루트 fork는 이 읽기 전용 비교 소스와 구별한다.
4. Point-LIO와 FAST-LIO는 비교·원인 분석 대상이다. Point-LIO를 새 주 시스템으로 복제하지 않는다. 출력 IMU 모델이나 점 단위 갱신을 도입하려면 GaRLIO 상태·오차 정의에 맞는 별도 설계와 검증이 필요하다.
5. 원본 및 개선본을 실험 이름 `garlio`, `garlio_gpt`로 구별한다. `garlio_gpt`는 현재 fork 소스 선택을 뜻하며, 개선 효과가 입증됐다는 이름이 아니다.
6. 기존 JURLIO 구현은 자동으로 복사하지 않는다. 필요한 개별 아이디어는 GaRLIO의 데이터 흐름·좌표계와 비교하고 검증한 뒤 추가한다.

## 1. 작업 원칙

- 사용자와 한국어로 소통하며, **코드에서 확인됨 / 실행으로 확인됨 / 가설**을 구별한다. 미실행 실험의 수치나 성능 우위를 만들지 않는다.
- 모듈 수정 전에 관련 소스를 읽고 데이터 흐름, 상태 정의, 좌표계를 요약한다. 자코비안을 바꿀 때는 해석식과 유한차분을 비교한다.
- **논문에서 왜 기능을 넣었는지 먼저 확인한다.** [설계 근거](docs/design_rationale.md)를 출발점으로 해당 절·식·ablation과 실제 코드를 대조하고, 도입 목적·기능 간 의존성·변경 이유를 기록한다. 근거가 부족하면 기존 기능을 유지한다. 논문과 코드의 차이를 곧바로 버그로 단정하지 않는다.
- 기존 기능을 단순화·빌드 편의를 이유로 삭제하거나 기본 비활성화하지 않는다. 기능 OFF는 별도 ablation 설정이며, 기본 기능 제거와 구별한다. 빌드 성공은 설계 타당성이나 성능 보존의 증거가 아니다.
- 알고리즘 확장은 기본 GaRLIO 동작으로 돌아갈 수 있게 구성한다. 추가 기능을 끈 실행과 원본 실행을 같은 bag·설정으로 비교한다.
- 시간 불일치, 누락 센서, 거부된 측정은 진단 로그에 남긴다. 현재 GaRLIO는 레이더가 필요하다. radar outage fallback은 별도 구현·검증 대상이며 이미 동작한다고 보고하지 않는다.
- 작업 단위마다 `docs/progress.md`에 날짜, 변경, 검증, 남은 문제를 기록하고 git commit 한다.
- 각 연구 Phase 끝에서 결과를 보고하고 다음 Phase로 넘어가기 전 사용자 승인을 받는다. 이번 요청은 개발 기반·빌드·실험 구조를 GaRLIO fork 중심으로 바꾸는 것을 승인한 것이며, 미완료 실험을 완료 처리하는 근거가 아니다.
- 긴 bag 재생은 로그가 남는 스크립트로 제공한다. 데이터나 실행 환경이 없으면 필요한 명령·결과 위치와 미검증 범위를 명시한다.

## 2. 코드에서 확인한 출발점

- `src/pointProcess.cpp`, `src/radar_ego_velocity_estimator.cpp`: LiDAR/레이더 전처리와 레이더 ego-velocity 추정.
- `src/lidarMapping.cpp`: IMU·LiDAR·레이더 버퍼 동기화, LiDAR/점별 Doppler 갱신, 속도 기반 중력 보정.
- `src/imuProcess.hpp`, `include/filter_state.hpp`, `include/S2.hpp`: 전파·deskew·상태 및 중력 방향 관련 표현. Point-LIO의 IKFoM 오차 정의와 동일하다고 가정하지 않는다.
- 원본 `sync_messages()`는 레이더 입력 없이 진행하지 않는다. LiDAR-only 동작이나 레이더 단절 복구는 현재 보장하지 않는다.
- 원본의 저장 절대 경로는 실험 runner에서 실행별 디렉터리로 덮어쓴다. 물리 센서 원점과 GT 원점의 일치는 아직 검증하지 않았다.

비교 원본 SHA와 더 자세한 확인은 [source_review.md](docs/source_review.md), 실제 lock은 [sources.lock.json](sources.lock.json)에 있다. 핵심 기능의 논문 근거와 코드 차이는 [design_rationale.md](docs/design_rationale.md)에 기록했다. 과거 계획의 모든 성능표를 재검증한 것은 아니며, 논문 보고값을 우리 실행 결과로 사용하지 않는다.

## 3. 구조와 실행 구분

```text
GaRLIO/
├── src/, include/                 # ★ 추가·개선할 GaRLIO fork
├── config/, launch/               # fork 설정과 기존 ROS 인터페이스
├── CMakeLists.txt, package.xml     # ROS 패키지는 garlio 유지
└── research_ws_gpt/
    ├── CLAUDE.md                  # 현재 지침
    ├── sources.lock.json          # 읽기 전용 비교 원본
    ├── docker/, scripts/, tests/
    ├── launch/garlio.launch       # 원본/개선본 공통 두 노드 실행
    ├── configs/, results/         # 생성 결과는 Git 제외
    └── docs/
```

Docker 안에서는 서로 다른 build/devel 공간을 쓴다.

| 실험 이름 | 소스 | 실행 환경 |
|---|---|---|
| `garlio` | 고정 SHA의 공식 GaRLIO, `/opt/research/catkin_ws/src/garlio` | `docker/run.sh ros` |
| `garlio_gpt` | 저장소 루트에서 복사한 GaRLIO fork, `/opt/research/fork_ws/src/garlio` | `docker/run.sh garlio_gpt` |
| `point_lio`, `fast_lio` | 고정 SHA의 공식 비교 소스 | `docker/run.sh ros` |

두 GaRLIO는 같은 ROS 패키지 이름을 유지한다. `garlio_gpt` 컨테이너에서만 fork overlay를 source한다. runner는 `rospack find garlio`의 실제 경로를 확인해 원본을 개선본으로 잘못 표기하는 실행을 거부한다. 개선본 파일 SHA-256과 이미지 커밋을 `meta.json`에 기록하며, 호스트의 소스 변경이 이미지와 다르면 재빌드를 요구한다.

ROS Docker 빌드 컨텍스트는 **저장소 루트**다. 분석 이미지 컨텍스트는 `research_ws_gpt`다. 명령은 [README](README.md)에 있다.

## 4. 연구 질문과 단계

**Q1 — 원인 분석:** GaRLIO의 저속·진동 조건 오차가 IMU 처리, 관측 품질, 시간 정합, 갱신 주기 중 무엇과 관련되는가? Point-LIO는 이 질문을 위한 비교군이다.

**Q2 — 점진적 개선:** GaRLIO의 기존 결합 구조에 품질 검사, 이상치 처리, 조건별 공분산 조절 등을 추가했을 때 저속·진동·동적 장면에서 도움이 되는가?

**Q3 — 기능별 분석:** 각 추가 기능이 어떤 조건에서 효과가 있고 언제 해로운가? 원본 성능을 유지하는 조건과 회귀하는 조건은 무엇인가?

### Phase 0: 개발 기반과 실행 환경

- 고정 SHA의 원본 세 방법을 빌드하고, 루트 fork를 별도 overlay로 빌드한다.
- 공통 recorder, N회 runner, CPU/설정/소스 기록을 사용한다.
- 원본/개선본 선택, 잘못된 선택 거부, 수정 소스의 재빌드 요구를 검증한다.
- 추가 알고리즘이 없는 fork를 같은 설정·짧은 bag으로 원본과 비교해 입력/출력 연결을 먼저 확인한다.

`[CHECKPOINT 0]` Linux 이미지, 네 방법 실행, 짧은 bag의 출력 여부를 보고한다. harness 단위 테스트만으로 완료 처리하지 않는다.

### Phase 1: 기준 성능과 동일성 확인

- NTU4DRadLM `calib/`, `gt_odom.txt`의 실제 형식·시각·원점·레버암을 확인한다.
- FAST-LIO2, Point-LIO, GaRLIO 원본, 현재 fork를 {cp, nyl, loop2, loop3}에서 N=5회 실행한다.
- 외부 보정과 재생 속도를 공통으로 적용하며, 설정 차이를 전부 기록한다.
- 고정 scale SE(3) 정렬 후 이동/회전 ATE와 z RMSE, 실행별 수치, 평균±표준편차를 보고한다.
- 추가 기능을 끈 fork의 궤적을 원본과 비교한다. 허용 오차는 반복 실행 변동과 수치 정밀도를 근거로 미리 정한다.

`[CHECKPOINT 1]` 기준 성능, 원본/fork 동일성, 재현 차이와 가설을 보고한다.

### Phase 2: 저속·진동 및 측정 품질 분석

- IMU 가속도·각속도의 Welch PSD와 속도 구간별 진동량을 분석한다.
- 비교용 Point-LIO의 입력/출력 IMU 모델을 전환해 같은 bag에서 차이를 확인한다.
- GaRLIO의 레이더 inlier 분포, 속도 추정 품질, 시간 정합, 측정 거부와 오차의 관계를 조사한다.
- 알고리즘 추가 전에 관측된 문제와 우선순위를 정한다.

`[CHECKPOINT 2]` 원인별 근거와 다음 구현 대상을 보고한다.

### Phase 3: GaRLIO에 기능별 추가

아래는 **구현 후보**이며, 현재 구현돼 있다는 뜻이 아니다.

1. **입력·추정 안정성:** timestamp 정합, 잘못된 프레임·퇴화 검사, 고정 seed와 일관된 inlier/outlier, 진단 기록.
2. **관측 품질 개선:** robust ego-velocity, 동적 후보 신뢰도, Doppler 이상치 가중·공분산 조절. 원본 경로로 돌아갈 수 있는 설정을 함께 둔다.
3. **IMU/중력 보정 개선:** Phase 2 근거에 따라 설계한다. GaRLIO의 상태·오차·중력 제약과 관측성을 먼저 정리하고, 새 자코비안은 수치 검증한다. 중력 보정과 Doppler의 의존성을 검토한다.
4. **선택적 센서 단절 대응:** 레이더 누락 시 시간축·LiDAR 스윕·필터 갱신을 어떻게 유지할지 별도 설계한다. 단순히 레이더 대기 조건을 삭제하는 것으로 완료하지 않는다.

각 후보는 별도 기능 플래그와 회귀 검사, 동일 설정 비교를 갖춘다. 하나씩 구현해 nyl과 loop2에서 N=5회 비교한다. `[CHECKPOINT 3a]`, `[CHECKPOINT 3b]`, `[CHECKPOINT 3c 설계/구현]`에서 결과를 보고한다.

### Phase 4: Ablation과 보고

- GaRLIO 원본 / 현재 fork의 모든 추가 기능 OFF / 추가 기능별 ON 조합을 비교한다. FAST-LIO2와 Point-LIO는 외부 비교군으로 유지한다.
- 튜닝은 cp, garden, 필요시 loop1 일부로 한정한다. nyl·loop2·loop3는 평가 전용이다.
- 두 설정의 평균 차이가 두 표준편차 중 큰 값의 2배를 넘지 않으면 기존 계획의 보수적 보고 규칙에 따라 “차이 확인 안 됨”으로 쓴다. 이를 정식 유의성 검정으로 부르지 않는다.
- 선택적으로 SNAIL-Radar `sl`에서 일반화를 확인한다.
- 결과·실패·한계와 저속 지상 로봇 적용 판단을 기록한다. 센서가 없는 구성의 성능은 별도 검증 없이 주장하지 않는다.

`[CHECKPOINT 4]` 최종 보고. 실제 로봇 적용은 센서 구성과 시간 동기화·보정값을 받은 뒤 별도 범위로 진행한다.
