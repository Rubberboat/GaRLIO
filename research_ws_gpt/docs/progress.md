# 진행 기록

현재 작업 위치: [`Rubberboat/GaRLIO`, `codex/radar-point-lio-phase0-gpt`](https://github.com/Rubberboat/GaRLIO/tree/codex/radar-point-lio-phase0-gpt). 아래 기존 JURLIO 링크·커밋·CI 결과는 이식 전 이력이다.

현재 개발 방향은 **GaRLIO 기반 확장**이다. 최신 작업은 문서 끝의 “GaRLIO fork 기반 확장으로 전환”을 확인한다. 이전 Point-LIO 기반 명세는 `point_lio_plan_original.md`에 보관했고 현재 지침은 `../CLAUDE.md`다.

## 2026-10-20 — Phase 0 구현, CHECKPOINT 0 검증 대기

사용자 요청: 첨부 연구 계획을 그대로 수행하고 `Rubberboat/jurlio`에 새 브랜치로 업로드. 현재 작업 브랜치는 `codex/radar-point-lio-phase0-gpt`, 원문은 `CLAUDE.md`로 보존했다. 기존 JURLIO와 구분해 `research_ws_gpt/`에서 작업한다.

완료한 구현:

- ROS Noetic desktop-full 기반 Dockerfile, ROS apt 제거, SDK → driver → 세 공식 알고리즘의 catkin 순차 빌드.
- 사용자 지정 세 SHA와 추가 Livox SDK/driver SHA 고정. FAST-LIO 재귀 submodule 복원·검증.
- Python 3.11 분석 Dockerfile (`evo`, `rosbags`, NumPy/SciPy/pandas/Matplotlib).
- 공통 Odometry → TUM recorder와 반복 실행 도구. 기본 rate=0.5, N=5, 독립 master, process cleanup, 센서 preflight, 실행별 CPU·로그·config·원본 커밋·bag hash·머신 기록.
- 공식 YAML + launch 값으로 smoke 설정 생성. GaRLIO 저장 경로만 실행별 override. 세 방법 모두 smoke PCD 저장 비활성화.
- 로컬 테스트와 Linux 빌드용 GitHub Actions workflow, 실행 명령·결과 위치 문서.

검증 상태:

- **코드에서 확인됨:** 지정 세 원본 SHA, Livox SDK/driver SHA, FAST-LIO ikd-Tree gitlink를 실제 checkout하고 소스 검토. 상세는 `source_review.md`.
- 로컬 테스트·복원 스크립트·CI의 최종 결과는 이 기록 아래에 실행 후 추가한다.
- **실험 미실행:** 현재 호스트는 macOS arm64이고 Docker/ROS가 설치되어 있지 않다. `~/datasets/NTU4DRadLM`도 없다. 실데이터 토픽 출력·궤적·ATE 수치는 생성하지 않았다.

결정 및 남은 문제:

1. CHECKPOINT 0은 실제 빌드와 짧은 NTU bag 출력 확인 전까지 통과로 표시하지 않는다.
2. Phase 1의 GT 열 순서·프레임·레버암과 공통 calibration, N=5 베이스라인 실험은 착수하지 않았다.
3. smoke 설정은 NTU 보정 검증 전이며 성능 비교에 쓸 수 없다. FAST-LIO의 외부 보정 추정 플래그 차이도 Phase 1에서 공정하게 정해야 한다.
4. Docker 태그/apt/전이 의존성은 완전한 lock이 아니다. 실제 빌드 패키지 목록을 기록하고 이후 이미지 ID를 고정할 것.
5. 입력 헤더 검사와 bag hash는 전체 데이터에서 비용이 들지만 반복 전 한 번만 수행한다. TCP 손실 여부·실시간 성능은 실제 실행으로 확인해야 한다.
6. 사용자 계획의 `[CHECKPOINT]` 지시에 따라 Phase 0 보고 후 다음 Phase 승인까지 대기한다.

### 로컬 검증 결과

- **실행으로 확인됨:** `python3 -m unittest discover -s research_ws/tests -v` — 18개 통과. Python compileall, shell `bash -n`, `git diff --check` 통과.
- **실행으로 확인됨:** 새 워크스페이스에서 `bootstrap_sources.py`로 다섯 저장소를 다운로드하고 SHA/clean 상태/FAST-LIO submodule 검증. `--verify-only` 재검사 통과.
- **실행으로 확인됨:** 실제 복원한 소스로 세 smoke YAML 생성 성공. 생성 결과는 `configs/generated/`에 있으며 Git에 포함하지 않는다.
- 최초 로컬 테스트는 샌드박스의 포트 bind/프로세스 검사 제한 때문에 실패했다. 권한을 갖춘 실행으로 재검사했고, 종료 대기 로직을 psutil의 자식 프로세스 확인으로 보완한 후 18개가 통과했다. 이 기록은 ROS 실행 성공을 의미하지 않는다.

### GitHub 업로드 및 CHECKPOINT 0 보고

- 구현 커밋 `367bb44a06b93fcd83afbaa4ed75be84ebdbb51d`를 `origin/codex/radar-point-lio-phase0`에 push했다.
- [Phase 0 CI 실행](https://github.com/Rubberboat/jurlio/actions/runs/39369905947)의 `images`, `harness` 두 job은 step이 하나도 시작되지 않았다. GitHub check annotation은 계정 결제 실패 또는 spending limit 증가 필요를 사유로 반환했다. 코드 빌드 실패로 해석하지 않으며 빌드 성공으로도 보고하지 않는다.
- 로컬 Docker/ROS 및 NTU 데이터 부재와 CI 실행 제한 때문에 **전체 빌드·짧은 실제 bag 토픽 확인은 미검증**이다. `README.md`의 Linux 명령을 실행한 뒤 `build_logs/`와 `results/checkpoint0/`를 확인해야 CHECKPOINT 0을 판정할 수 있다.
- Phase 1 이후는 진행하지 않았다. 원문 §0.3 및 `[CHECKPOINT 0]`에 따라 이 상태를 사용자에게 보고한다.

## 2026-10-20 — GPT 결과물 이름 구분

- 사용자 요청에 따라 연구 폴더를 `research_ws_gpt/`, 작업 브랜치를 `codex/radar-point-lio-phase0-gpt`로 변경한다.
- Docker 이미지 태그는 `phase0-gpt`, workflow는 `research-phase0-gpt.yml`, CI 결과 이름은 `research-phase0-build-logs-gpt`로 구분한다. README와 실행 스크립트의 관련 경로도 갱신한다.
- 이전 절의 커밋·CI·테스트 명령은 당시 실행 기록이다. 사용자 명세 원문 `CLAUDE.md`와 원본 알고리즘 코드는 수정하지 않는다.
- **실행으로 확인됨:** 새 경로에서 기존 단위 테스트 18개, 원본 SHA/submodule 검증, shell 구문 검사, `git diff --check` 통과.

## 2026-10-20 — Rubberboat/GaRLIO로 이식

- 사용자 요청에 따라 `Rubberboat/jurlio`의 `codex/radar-point-lio-phase0-gpt`, 커밋 `9e319452debf5b5215fa75dac7ad4c04d4d6669b`에서 추적된 `research_ws_gpt/`와 `.github/workflows/research-phase0-gpt.yml`을 옮겼다. 생성물·다운로드 소스·기존 JURLIO 알고리즘은 이식 대상이 아니다.
- 대상 `main`은 `ff4dfefad2cbd3333824c518d5652f1bf9a5039b`이며, 연구 환경이 고정한 GaRLIO SHA와 같다. 대상의 `CMakeLists.txt`, `package.xml`, `src/`, `include/`, `config/`, `launch/`를 검토했고 기존 빌드 설정과 연구용 Docker 컨텍스트는 분리되어 있다.
- `gpt` 접미사를 유지하고 새 저장소 clone 명령과 안내 링크를 갱신했다. 바깥 catkin 검색에서 중첩 연구 소스를 제외하도록 연구 폴더에 `CATKIN_IGNORE`를 추가했다. 컨테이너에서는 `catkin_ws/src`를 명시적으로 빌드한다.
- 호환성 판정은 소스·패키지 구성과 로컬 실행 도구에 한정한다. Docker/ROS와 NTU bag 부재로 전체 ROS 빌드·재생은 여전히 미검증이며, Phase 0 체크포인트 상태는 바뀌지 않는다.
- **실행으로 확인됨:** 대상 저장소에서 기존 테스트 18개, compileall, shell 구문 검사, diff 공백 검사 통과. 이식한 실행 코드·설정·workflow는 원본 브랜치와 바이트 단위로 같고, 대상의 기존 파일은 README 안내 추가 외에 변경되지 않았음을 비교했다.
- 이식 커밋 `d208ac05b6445457b1e1022c1b21f9e67f6763f2`를 대상의 동일한 이름의 GPT 브랜치에 push했고, 원격 `main`이 `ff4dfef`로 유지됨을 확인했다.
- [GaRLIO 저장소 CI](https://github.com/Rubberboat/GaRLIO/actions/runs/39373898864)는 정상 시작되었고 Linux `harness` job(18개 테스트)이 통과했다. 이 기록 시점에는 `images` job의 ROS 빌드가 진행 중이다. 이식 전 JURLIO에서 발생했던 계정 결제/한도 차단은 이 실행에서는 발생하지 않았다. 전체 빌드 성공으로 기록하지 않는다.

## 2026-10-20 — GaRLIO fork 기반 확장으로 전환

사용자 요청: `Rubberboat/GaRLIO` fork에서 GaRLIO를 기반으로 기능을 더해 개선한다. 추가 지시: 논문에서 기능을 넣은 이유를 계속 확인하며, 이유가 있는 기능을 근거 없이 없애지 않는다.

구현·결정:

- 개선 대상은 루트 GaRLIO 코드다. Point-LIO와 FAST-LIO는 비교군으로 유지한다. 현재 `CLAUDE.md`의 연구 질문·단계·디렉터리 구성을 이에 맞췄고, 이전 명세는 바이트 단위로 보존했다.
- `AGENTS.md`와 `docs/design_rationale.md`에 논문 목적·식·ablation 및 실제 구현 대조 원칙을 기록했다. 논문 IV-A~D, V-E를 읽고 주요 기능의 이유와 의존성을 확인했다. 논문과 다른 sentinel 기반 제거·추가 gate·상태 표현 등은 미확인 차이로 기록했으며 알고리즘을 변경하지 않았다.
- 루트 C++/헤더/기본 config/launch/CMake/package는 `ff4dfef`와 동일하다. 현재 변경은 향후 기능 추가를 위한 빌드·실험 구조다.
- ROS 이미지는 저장소 루트 컨텍스트에서 비교 원본 `catkin_ws`와 루트 fork의 `fork_ws` overlay를 빌드한다. 기존 ROS 패키지 이름을 유지하며 실험 이름만 `garlio`/`garlio_gpt`로 구별한다.
- runner에 fork 모드를 추가했다. 실제 ROS package 경로와 원본 SHA/clean 상태, fork의 파일별 hash·전체 hash를 확인한다. 호스트 코드와 빌드 입력이 다르면 재빌드를 요구하며, 선택 소스를 실행 메타데이터에 남긴다.
- CI가 루트 소스·설정 변경에도 실행되며 두 환경의 package 선택·manifest 검사를 수행하도록 변경했다.
- 기존 CI `39373898864`의 최종 실패를 확인했다. GaRLIO 빌드는 통과했으나 FAST-LIO가 `fast_lio/Pose6D.h` 누락으로 실패했고 Point-LIO는 abandoned였다. 원본 CMake를 패치하지 않고 메시지 target을 먼저 빌드하도록 Docker 순서를 수정했다. 수정 후 전체 Linux 결과는 아래에 별도로 기록한다.

검증:

- **실행으로 확인됨:** 로컬 Python 테스트 28개 통과. 최초 sandbox 실행에서는 기존 포트 bind/프로세스 조회 검사가 권한 제한으로 실패했으며, 허용된 실행으로 전체 재검증했다.
- **실행으로 확인됨:** Python compileall(임시 cache 경로), shell 구문, workflow YAML 파싱, `git diff --check` 통과.
- **실행으로 확인됨:** 현재 fork와 기존 다운로드 원본의 package 파일 hash 및 smoke 설정 일치. wrapper의 세 모드별 이미지·환경 인자 확인. 이전 명세가 당시 HEAD와 바이트 단위로 같음을 확인했다.
- 현재 호스트에 Docker/ROS와 실제 NTU bag이 없어 로컬 ROS 빌드·실데이터 재생은 실행하지 않았다. 궤적 동일성·정확도·추가 알고리즘 효과는 미검증이다.
- Phase 1 이후의 실험이나 기존 기능 삭제는 수행하지 않았다.

### 추가 사용자 지시 — 자율 개선과 push 전 설명

- 논문에 있는 기능도 더 나은 대안이 있으면 추천·교체·재설계할 수 있다. “논문 기능 보존” 자체가 목표는 아니며, 도입 의도와 상호작용을 이해하고 설명 가능한 개선을 진행한다.
- 연구 체크포인트에서 매번 승인을 기다리는 이전 지침을 해제했다. 미실행 실험의 완료·성능을 주장하지 않는 원칙은 유지한다.
- 매 push 전에 변경 내용·방법, 기존 방식을 바꾸는 이유, 기대 효과와 실제 검증 결과·미검증 범위를 사용자에게 먼저 설명한다. 별도 승인을 기다리라는 요청은 아니다.
- 첫 추천 후보는 Doppler 가중 분모의 양수·유한값 보장, 다음은 동적 점 제거의 명시적 공분산 gate 비교다. 구체적 코드 근거를 `design_rationale.md`에 기록했다. 이 두 알고리즘 변경은 아직 구현하지 않았다.
- 기반 변경 커밋 `8f0427b`는 이 추가 지시 전에 기존 GPT 브랜치에 push됐다. [해당 Linux CI](https://github.com/Rubberboat/GaRLIO/actions/runs/39395984431)의 harness는 통과했고, 이미지 결과는 확인 후 아래에 기록한다.

### Linux CI 최종 결과

- **실행으로 확인됨:** 커밋 `8f0427b0201a748a69db7ad5c1d4a80355968cea`, [실행 `39395984431`](https://github.com/Rubberboat/GaRLIO/actions/runs/39395984431)의 `harness`, `images` 모두 성공했다.
- 원본 GaRLIO·FAST-LIO·Point-LIO와 GaRLIO fork overlay 빌드 및 실행 파일 존재 검사가 통과했다. 이전 FAST-LIO 메시지 헤더 누락 실패가 이번 빌드에서는 재발하지 않았다.
- 원본 환경과 fork 환경에서 package 탐색, smoke 설정 생성, source manifest·호스트 소스 일치 검사가 통과했다. 28개 테스트는 Linux 호스트와 ROS 컨테이너에서 통과했다.
- Python 3.11 분석 이미지 빌드와 evo/rosbags/NumPy/SciPy/pandas/Matplotlib import 검사가 통과했다.
- 실제 NTU bag을 재생한 것은 아니다. 토픽 발행, 궤적 동일성, 정확도는 미검증이므로 CHECKPOINT 0의 실제 데이터 확인 항목은 남아 있다.
- 이후 커밋은 사용자 개발 원칙·개선 후보·이 CI 결과의 문서 갱신이며 실행 코드는 바꾸지 않는다. 이 문서 변경은 `[skip ci]`로 기록한다.

## 2026-10-21 — 로컬 Linux 센서 재생과 GaRLIO/JURLIO 비교

- 사용자 허가에 따라 SNAIL `20231105/data6` 원본과 기준 궤적을 다운로드했다. 공식 MD5 일치, SDK와 LiDAR·레이더 6프레임의 모든 점·필드 값 일치를 확인했다. 126.135초 bag에 LiDAR 1,261·레이더 1,822·IMU 11,200 메시지가 있다.
- GaRLIO의 기존 Hesai 지원 경로를 harness에서 허용하고 필드·시각 검사를 추가했다. JURLIO와 공통 실행 도구, CPU 측정용 활성 재생 시각, 보간 평가·그래프를 추가했다. 알고리즘 C++는 양쪽 모두 변경하지 않았다.
- 기존 Linux 이미지의 바이너리 입력 소스 hash와 로컬 소스를 대조해 재사용했다. GaRLIO 원본 `ff4dfef`의 핵심 패키지 파일 31개가 fork와 일치했다. JURLIO 바이너리는 `465a538`이다. 원본과 다른 fork 알고리즘을 실행한 것으로 표기하지 않는다.
- **실행으로 확인됨:** 12초 합성 bag, 4방법×3회 성공. 최초 GaRLIO는 컨테이너 Git 소유권 검사에서 실패했고 임시 HOME 설정 후 재실행했다. 같은 bag hash와 실패 로그를 보존했다.
- **실행으로 확인됨:** 실제 data6를 4 CPU·8 GiB·1배속으로 실행. GaRLIO, JURLIO baseline, robust 완주. 동일 기준 시각 1,248개·원점 변환·SE(3) 정렬의 위치 RMSE는 각각 2.974/2.863/2.818 cm다. 기존 최근접 시각 평가의 5.367/5.336/5.314 cm도 보존했다. 단일 실측 구간이며 확실한 우위 주장은 하지 않는다.
- **실패 확인:** dynamic은 위치 갱신이 약 38초에서 끊긴 뒤 49초에 LiDAR backlog 보호 종료. 0.5배속에서도 약 43초에서 출력이 끊기고 53초에 같은 실패가 발생했다. stale prior 거부와 radar 필수 동기화의 순환 의존성을 기록했다. 제한 제거로 우회하지 않았다.
- **검증:** 컨테이너 Python 31개(GaRLIO harness)·17개(JURLIO), JURLIO C++ 수치 검사 7개 통과. 실제 replay·변환 대조·그래프 렌더 확인은 단위 시험과 별도로 수행했다.
- [전체 보고서](sensor_comparison_2026-10-21.md)에 단계별 구조, 데이터·이미지 식별자, 결과 폴더와 재실행 명령을 남겼다. 대용량 데이터·원시 로그·그래프는 작업 폴더의 `output/simulation_comparison_2026-10-21/`에 있다.
- 남은 일: dynamic의 불확실성 있는 복구 경로 설계·검증, 여러 실제 시퀀스 반복, NTU 및 Point-LIO 비교. 이번 결과만으로 기존 연구 계획의 전체 체크포인트를 완료 처리하지 않는다. 이번 변경은 로컬 commit으로 보관하며 push하지 않는다.

## 2026-10-21 — JURLIO dynamic 거부·복구 후속 검증

- 사용자 요청에 따라 실제로 실패한 GaRLIO 파생 JURLIO의 순환 의존성을 수정했다. 이 GaRLIO 저장소의 알고리즘은 공식 원본 비교군으로 유지했다.
- 레이더 측정이 거부돼도 원래 시각의 빈 inlier/outlier 쌍으로 스윕 경계를 전달하고 LiDAR·IMU 갱신을 계속한다. 이때 Doppler·레이더 기반 마스킹·속도 덮어쓰기를 제외하고, 유효한 연속 속도 끝점이 다시 확보될 때까지 속도 기반 중력 보정을 제외한다. 논문 IV-A의 스윕 경계와 IV-C/D의 유효 관측 의존성을 구분했으며 기존 gate·버퍼 보호·공분산 수식은 유지했다.
- **실행으로 확인됨:** 같은 data6의 1배속 2회·0.5배속 1회 모두 1,817개 pose, tail lag 0초로 완주했다. 공통 기준 시각 1,248개에서 위치 RMSE 2.225–2.234 cm, 최대 위치 오차 9.066–9.122 cm다. robust 진단 대조군은 RMSE 2.770 cm, 최대 39.262 cm다.
- **실행으로 확인됨:** 합성 bag의 레이더 40프레임을 4초간 비운 대조 시험에서 복구 ON은 116개 pose·RMSE 4.628mm·최대 출력 간격 0.100초로 통과했다. OFF는 27개 pose 뒤 정지해 기존 종료 검사를 실패했다. 정상 레이더 복귀 후 재결합과 중력의 한 프레임 지연 재개를 확인했다.
- **검증:** JURLIO ROS 재빌드·C++ 수치 검사 7개, 최신 Python 18개, GaRLIO harness 31개 통과. 정상 합성 입력의 baseline/robust/dynamic이 완주했고 이전 결과와 눈에 띄는 차이가 없었다. 원격 CI는 이번 로컬 검사에 포함하지 않았다.
- 상세 기록은 별도 저장소 `jurlio/docs/RECOVERY_2026-10-21.md`, 실행 명령·이미지 ID·소스 hash·로그·그래프는 부모 작업 폴더 `output/recovery_2026-10-21/`에 있다. 수정 전 실패 기록은 보존한다.
- 한계: data6는 수정에 사용한 개발·회귀 구간이며 미사용 평가 구간의 일반화 검증이 아니다. 장치 단절로 레이더 메시지 자체가 오지 않는 경우와 장기 LiDAR 퇴화는 미해결 범위다. baseline/robust 및 기본 모드는 유지했다. 이번 수정과 보고서는 로컬 commit으로 보관하며 push하지 않는다.

## 2026-10-21 — 사용자 요청에 따른 push 및 전체 재검증

- 사용자 요청으로 GaRLIO `405e858`, JURLIO `4272ec6`를 각 기존 GPT 브랜치에 push했다. 이 PC의 GitHub 인증 부재로 최초 push는 실패했고, 사용자가 GitHub CLI 인증을 완료한 뒤 성공했다.
- GaRLIO 수동 CI `39616806450`의 harness가 `test_interpolation`을 가져올 때 NumPy 누락으로 실패했다. ROS 컨테이너에는 NumPy가 이미 있어 로컬 검사만으로 이 설치 목록 누락을 발견하지 못했다. workflow와 README에 `numpy==1.26.4`를 명시했다. C++ 알고리즘 변경은 없다.
- **실행으로 확인됨:** PyYAML 6.0.3·psutil 7.0.0·NumPy 1.26.4를 설치한 깨끗한 Python 환경에서 harness 31개 통과. 최신 push 커밋으로 공식 GaRLIO·FAST-LIO·Point-LIO 및 fork overlay를 로컬 재빌드하고 원본/fork 패키지 선택·소스 manifest·분석 이미지 import 검사까지 통과했다.
- JURLIO 원격 CI `39616406276`는 GitHub 계정 결제 실패 또는 spending limit 때문에 단계가 시작되지 않았다. GaRLIO harness의 의존성 오류와 구분한다. JURLIO의 최신 커밋 로컬 ROS 빌드·수치 검사 7개·Python 18개 및 합성 네 방법×3회는 통과했다.
- 실측 반복·미사용 시퀀스 평가와 추가 장애 시험은 계속 진행 중이다. 결과 파일은 부모 작업 폴더 `output/push_validation_2026-10-21/`에 보존한다. 이 설정 수정의 원격 CI 성공 여부는 후속 결과에 기록한다.

## 2026-10-22 — push 이후 전체 재생 및 추가 구간 평가 완료

- **실행으로 확인됨:** 합성 네 방법×3회, 실측 data6 네 방법, 새 data4 네 방법과 dynamic 0.5배속, 장애 ON/OFF·메시지 제거, CI dynamic 0.5배속, 원본 data6 추가 2회로 총 27회 ROS 재생을 마쳤다. 26회 실행 완료와 의도한 복구 OFF 실패 1회이며 정확도·연속성 26회 합격을 뜻하지 않는다.
- 새 SNAIL `20231007/data4` 152.566초를 다운로드해 공식 MD5·SDK 6프레임·IMU 27,428개의 모든 필드·시각을 대조했다. X36D 원본의 서로 다른 값에 중복 시각 3쌍이 있어 변환기가 올바르게 거부했다. 알고리즘 결과를 보기 전에 ZED2i IMU와 공식 외부 보정으로 비교 구성을 정했고 모든 방법에 동일하게 적용했다. 최대 0.941초·0.2초 초과 31곳의 실제 입력 공백을 보존했다.
- **정확도 한계 확인:** data4 공통 기준점 1,369/1,509개에서 원본 GaRLIO/baseline/robust/dynamic RMSE 14.225/40.810/37.408/38.639cm. dynamic 0.5배속도 34.554cm로 원본보다 나빴다. 입력 공백만을 성능 차이의 원인으로 단정하지 않으며 추가 구간을 보고 C++를 튜닝하지 않았다.
- data6 이번 원본/dynamic RMSE는 2.439/2.228cm다. 원본 최초 실행까지 포함한 4회 범위는 RMSE 2.427–2.974cm·최대 오차 9.350–39.610cm다. 원본의 RANSAC 난수 초기화와 비동기는 원인 후보이며 분리 입증하지 않았다. 최초 39cm→9cm 차이를 고정된 개선 폭으로 표현하지 않는다.
- 빈 레이더 40프레임 복구 ON은 116 pose·RMSE 4.628mm·최대 간격 0.100초로 통과했다. OFF는 27 pose 뒤 멈췄다. 레이더 메시지 자체를 4초 제거한 경우 복귀 후 실행은 마쳤으나 4.100초 출력 공백이 남았다.
- **CI 확인:** NumPy 설치 목록을 고친 `7940232`의 [GitHub CI](https://github.com/Rubberboat/GaRLIO/actions/runs/39618646610) harness·images 모두 성공했다. 로컬 GaRLIO harness 31개, 원본/fork/FAST-LIO/Point-LIO 빌드·패키지·소스 검사, 분석 이미지 import 검사를 통과했다. FAST-LIO·Point-LIO 실측 궤적 비교는 수행하지 않았다.
- JURLIO `4272ec6`·`fe57169`는 push됐고 로컬 ROS 빌드·C++ 수치 7개·Python 18개를 통과했다. [원격 CI](https://github.com/Rubberboat/jurlio/actions/runs/39620280440)는 계정 결제 실패 또는 spending limit으로 job 단계가 시작되지 않았다. 코드 실패나 원격 CI 성공으로 기록하지 않는다. 최종 `jurlio:validated-gpt`의 두 ROS 실행 파일은 전체 재생에 사용한 바이너리와 hash가 같다.
- 이 GaRLIO의 핵심 패키지 파일 31개는 고정 공식 원본 `ff4dfef`와 동일하다. 논문 기능을 임의로 제거하지 않았다. 최종 결과는 [JURLIO 보고서](https://github.com/Rubberboat/jurlio/blob/codex/integration-audit-gpt/docs/FULL_VALIDATION_2026-10-21.md), 부모 폴더 `output/push_validation_2026-10-21/`에 원시 성공·실패 로그와 입력·소스·이미지 식별자를 보존한다. 보고서에는 구조 설명의 이전 문서, 비교 그래프, 수치 JSON, 재현 분석 코드를 연결했다.
- 남은 연구는 JURLIO 공통 변경 ablation, IMU 공백에서 전파·중력 의존성, fused prior의 시각 정합과 레이더 메시지 단절 시 스윕 생성이다. 이번 요청의 실행·보고를 완료하되 NTU·Point-LIO 비교를 포함한 전체 연구 계획 완료나 실사용 성능 우위를 주장하지 않는다.


## 2026-10-22 — 실제 GaRLIO fork 개선 재개: 속도 보정의 품질 검사 우회 방지

- 사용자가 개선될 때까지 SNAIL 재실행·비교를 요청했다. 개선 대상은 GaRLIO 루트이며 공식 고정 소스는 계속 분리한다. 이전 data4도 실패를 분석한 개발 데이터로 재분류하며 새로운 미사용 평가라고 부르지 않는다.
- `Angle Refine`가 Doppler의 기존 축별 0.5 m/s 품질 기준을 벗어난 레이더 속도를 공분산 갱신 없이 상태에 직접 대입할 수 있음을 확인했다. 같은 작업 폴더의 별도 `jurlio-hunger/docs/REVIEW_CLAUDE.md`가 먼저 이 우회 경로를 지적했으며, 해당 작업 트리는 수정하지 않았다. GaRLIO에 필요한 최소 조건만 독립 구현했다.
- `mapping/refine_velocity_consistency` 기본 true: 이전 IMU 예측과 일치하는 레이더에만 기존 긴급 속도 대입을 허용한다. false는 기존 동작 대조군이다. 앞선 LiDAR 재갱신과 정상 Doppler·중력 단계는 유지한다. `radar_guard.csv`는 요청·허용·실제 대입을 별도로 기록한다.
- **실행:** 경계·축별 이상치·NaN/Inf 거부 수치 시험과 ROS fork 빌드 통과. data6 첫 실행은 위치 RMSE 2.352cm, 최대 9.939cm, 1,817 pose다. 기존 원본 단일 실행 2.439cm·9.872cm와 비교하며, 반복 검증 전 개선 확정으로 처리하지 않는다. data4 실행은 진행 중이다.
- 별도 JURLIO의 한 IMU 스윕 폐기 조건만 바꾼 대조는 data4 RMSE 40.810→16.254cm, 최대 487.193→119.428cm, 2,051→2,095 pose를 보였다. 다른 갱신 수식은 그대로여서 이 조건의 영향이 확인됐다. 원본보다 우월하다고 주장하지 않는다.
- 실험 계획·소스 hash·명령·실패 포함 로그는 부모 폴더 `output/improvement_2026-10-22/`에 보존한다. 후속 시간 경계 후보는 현재 재생 바이너리와 별도로 준비한다.

## 2026-10-22 — 시간 경계를 맞춘 GaRLIO 후보와 Claude 커밋 검증

- 논문 III-B/IV-A/IV-D의 적분 구간 의존성을 검토하고 `mapping/time_consistent_sweeps`를 추가했다. 기본 false, SNAIL 실험 프로필에서 true다. 실측 IMU 양 끝점을 보존해 전파·deskew·중력 적분을 레이더 스윕 구간에 맞춘다. 단순한 프레임 폐기 제거와 다르며 미래 샘플 대기 지연을 수반한다. 설명·공분산 근사 한계는 설계 근거 문서에 남겼다.
- 경계/비유한값 거부, 불규칙 샘플의 정확한 적분 구간, 선형 가속도 적분, 분할 구동 분산 합 검사 및 ROS 빌드를 통과했다. Docker 빌드에서도 두 신규 C++ 검사를 실행한다. 초기 후보 이미지 `4348dba4`의 합성 RMSE는 3.804mm로 기존 3.662mm보다 0.142mm 크다. 이 작은 회귀도 보존한다.
- 첫 data4 실행: 기존 방법 전체 공통 1,369점에서 원본/guard만/시간 후보 RMSE 14.225/13.159/5.069cm, 최대 119.385/101.121/37.105cm. 후보는 기준 시각 1,509개 모두를 덮으며 이 **전체 기준점** RMSE는 8.993cm, 최대 46.476cm다. 원본은 1,393개만 덮는다. 최대 출력 시각 간격은 0.933→0.191초다. 실제 0.941초 IMU 공백을 보간하므로 즉시 실시간 출력이라는 의미는 아니다.
- 첫 data6 실행: 공통 1,248점에서 원본/guard만/시간 후보 RMSE 2.439/2.352/2.134cm, 최대 9.872/9.939/9.404cm. 출력 1,817개 유지. 모두 첫 후보 결과이며 반복 검증 전 확정된 성능 우위로 취급하지 않는다.
- 사용자가 Claude의 새 push마다 검증하도록 요청했다. 현재 GaRLIO main `2dcc39e70e2e8eb43649820d2315ef78b34a5838`를 별도 archive 소스·이미지로 빌드해 비교 중이다. Claude 작업 트리를 수정하거나 이 브랜치에 자동 병합하지 않았다. 5분 간격 확인을 설정하고 커밋별 상태와 실패 포함 로그를 보존한다.
- 후보 수치 변경 없이 ROS 입력 시각 지연 진단을 추가한 뒤 최종 이미지와 반복 실행을 진행한다. data4는 이미 원인을 분석한 개발 구간이며 미사용 평가가 아니다. 자원 제한은 각 실행 4 CPU/8 GiB/1배속, 이 작업의 estimator끼리는 순차 실행한다. 다른 사용자의 컨테이너가 같은 호스트에서 실행될 수 있어 호스트 독점 성능 시험으로 해석하지 않는다.


## 2026-10-22 — 반복 검증 완료, Claude 빌드 오류 및 검증 캐시 오류 정정

- GaRLIO 원본/시간 후보/Claude 링크 수정 사본을 각 두 SNAIL 구간에서 3회씩 비교했다. data4 공통 1,369점 평균±SD는 원본 13.773±0.651cm, 시간 후보 4.991±0.114cm다. 후보는 1,509점 전체를 덮고 자체 RMSE는 8.716–9.027cm이며 최대 센서 시각 출력 간격은 0.933→0.191초다. 실제 미래 IMU 대기로 최대 ROS 입력 시각 지연 약 0.97초가 발생한다.
- data6 원본/시간 후보 평균은 2.790/2.194cm이나 감소 0.596cm가 사전의 2×큰 SD 기준 0.607cm에 못 미친다. 긍정적 방향과 확정된 우위를 구별한다. 기능 모두 OFF data4는 13.837cm·2,095 pose·0.933초로 원본 범위에 돌아왔다. 시간 기능은 기본 false이며 실험 프로필에서 켠다.
- **중요 정정:** 초기 `claude_2dcc39e_*` 네 실행은 오래된 git archive 시각 때문에 기존 오브젝트/실행 파일이 재사용된 무효 결과였다. 앞서 보고했던 Claude 수치를 철회했고, 소스만 같은 것으로 컴파일을 입증할 수 없음을 확인했다. build/devel/logs를 비워 재빌드하자 정확한 원격 2dcc39e는 OpenCV 링크 누락으로 실패했다. 로그와 무효 기록을 보존하고 평가에서 제외한다.
- OpenCV_LIBRARIES 한 항목만 연결한 별도 Claude 진단 사본은 빌드·합성·SNAIL 두 구간 각3회를 완료했다. data4 평균13.202±2.558cm, data6 2.697±0.369cm로 두 구간 모두 보수적인 차이 기준에 미달한다. 정확한 원격 커밋의 성공으로 표기하지 않는다. Claude의 브랜치/작업 트리는 수정하지 않았다.
- 유효 재생27회와 무효4회, 정확한 Claude 커밋 clean build 실패1건을 구별해 보존했다. Python31+18개, C++수치 프로그램2+7개, 원본/fork/JURLIO 공용 실행기 실제 합성 재생을 통과했다. 시간 후보의 최종 합성3.802mm는 원본3.662mm보다 소폭 나쁘다. GaRLIO와 JURLIO 모두 독립 clean build 바이너리가 실험본과 정확히 일치했다.
- 원격 revision 전용 Dockerfile은 기존 fork build/devel을 반드시 비운다. 실행기는 실제 바이너리 해시를 기록하며, 공용 비교기에 별도 fork 소스/이미지를 추가하고 원본 검사를 현재 fork와 잘못 비교하던 조건을 수정했다. `garlio_gpt` 실제 합성 재생으로 확인했다.
- 사용자 요청대로 `push-snail` heartbeat를 5분 간격 설정했다. 사용자 대상 답변 전 기본 감시는 GaRLIO main 및 jurlio-hunger 신규 생성/업데이트다. SHA별 별도 스냅샷·실패 포함 원장·실행 상태로 중복 재생을 막는다. [최종 보고서](SNAIL_REVALIDATION_2026-10-22.md), [재현 코드/프로필/수치/실패 증거](../experiments/snail_2026_10_22/README.md)를 확인한다. data4는 개발 구간이며 전체 NTU/Point-LIO 연구 완료나 실로봇 성능 우위를 뜻하지 않는다.
