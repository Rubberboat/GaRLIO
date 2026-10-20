# Phase 0 원본 코드 확인

현재 개발 방향은 GaRLIO fork 확장이다. 아래는 비교 소스 확인 이력이며, 기능 변경 전 읽을 논문 목적·의존성·구현 차이는 [design_rationale.md](design_rationale.md)에 기록한다.

2026-10-20 (Asia/Seoul). 아래는 지정 SHA의 **코드에서 확인된 사실**이다. 연구 명세의 수치·논문 해석은 이번 단계에서 재검증하지 않았다.

| 방법 | 입력과 처리 | 실행 파일 / 출력 | 파라미터 공간 |
|---|---|---|---|
| Point-LIO | CustomMsg + IMU → 시간순 처리 → IKFoM → iVox | `point_lio/pointlio_mapping`, `/aft_mapped_to_init` | `ros::NodeHandle("~")`, `/laserMapping/…` |
| FAST-LIO | CustomMsg + IMU → IMU 전파/deskew → scan-to-map | `fast_lio/fastlio_mapping`, `/Odometry` | 전역 |
| GaRLIO | radar/LiDAR 전처리 → `/laser_cloud_surf`, `/filtered_points`, `/eagle_data/outlier_pc2` + IMU → mapping | `garlio/cloudProcess`, `garlio/lidarMapping`, `/aft_mapped_to_init` | 전역 |

Point-LIO `include/common_lib.h`의 출력 상태에는 위치·회전·LiDAR/IMU 외부 보정·속도·각속도·가속도·중력·두 bias가 있다. 입력 상태에는 각속도·가속도 상태가 없다. 이 단계에서는 상태·잔차·자코비안·필터를 수정하지 않는다.

원본 Odometry의 `header.frame_id`는 세 방법 모두 `camera_init`이다. Point-LIO/FAST-LIO의 `child_frame_id`는 `body`, GaRLIO는 `aft_mapped`다. 이름이 비슷하다고 GT와 같은 물리적 원점이라고 가정하지 않는다. recorder는 원본 pose를 그대로 기록하며 GT 레버암 및 정렬은 Phase 1에서 확인한다.

설정에서 확인한 차이:

- Point-LIO Horizon launch의 `init_map_size=10` 등은 YAML에 없다. YAML만 로드하면 소스 기본값 `100` 등이 적용된다. 실행 확인용 설정 생성기가 launch 값을 함께 옮긴다.
- FAST-LIO Horizon은 `mapping/extrinsic_est_en=true`, Point-LIO는 false다. FAST-LIO는 원본 Horizon YAML에서 PCD 저장도 켜져 있다. 실행 확인용 설정은 세 방법 모두 PCD 저장만 끈다. 공정한 비교 설정은 아직 아니다.
- GaRLIO 공식 `loop2.yaml`의 외부 보정은 identity이며 `traj_save_path`는 원저자 절대 경로다. 외부 보정은 검증 전으로 남겨 두고 저장 경로만 실행별 폴더로 override한다.
- GaRLIO mapping의 outlier 구독은 `/eagle_data/outlier_pc2`에 고정되어 있다. 이 토픽을 config에서 바꾸면 전처리/필터 연결이 끊긴다.
- Livox driver 저장소의 ROS 패키지는 한 단계 아래 `livox_ros_driver/`에 있다. SDK가 먼저 설치되지 않으면 driver CMake가 최신 SDK를 clone하는 fallback을 실행하므로 SDK 설치 파일을 명시적으로 검사한다.
- FAST-LIO 상위 gitlink의 ikd-Tree SHA는 `e2e3f4e9d3b95a9e66b1ba83dc98d4a05ed8a3c4`다. branch 최신값으로 바꾸지 않는다.
- Point-LIO와 FAST-LIO는 `ROOT_DIR/Log`에 로그를 연다. 컨테이너 빌드에서 디렉터리를 준비하며 원본 파일을 패치하지 않는다.

원본 링크:

- [GaRLIO](https://github.com/ChiyunNoh/GaRLIO/tree/ff4dfefad2cbd3333824c518d5652f1bf9a5039b)
- [Point-LIO](https://github.com/hku-mars/Point-LIO/tree/4b86a469eb5572e70ed575af25b5f15dd06e8e3c)
- [FAST-LIO](https://github.com/hku-mars/FAST_LIO/tree/7cc4175de6f8ba2edf34bab02a42195b141027e9)
- [NTU4DRadLM](https://github.com/junzhang2016/NTU4DRadLM)
