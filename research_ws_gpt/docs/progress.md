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
