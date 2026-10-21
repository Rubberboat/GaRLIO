# 검증 오류와 정정 — 2026-10-22

Claude main `2dcc39e70e2e8eb43649820d2315ef78b34a5838`의 최초 네 실행(`claude_2dcc39e_synthetic`, `claude_2dcc39e_data4`, `claude_2dcc39e_data6`, `claude_2dcc39e_data4_r2`)은 **해당 커밋의 유효한 실험이 아니다**. 그 이름으로 사용자에게 보고했던 13.59–13.73cm/data4, 2.96cm/data6 수치는 철회했다. 파일과 로그는 삭제하지 않고 각 experiment.json에 `validation_status: invalid_stale_binary`를 표시했다. 평가 스크립트는 이를 제외한다.

원인: git archive는 소스의 과거 수정 시각(2026-10-20)을 보존한다. 기반 Docker 이미지의 오브젝트는 그보다 새 시각(2026-10-21)이었다. fork의 소스만 교체하고 build/devel을 남겨 두어 catkin이 0.1초 만에 'up to date'로 끝났다. 소스 manifest 검사는 통과했지만 그것만으로 새 바이너리 컴파일을 입증하지 못했다.

실행 파일 SHA-256을 확인하니 잘못된 이미지와 기반 이미지가 둘 다 다음과 같았다.

- cloudProcess: `ba340a7060cf6b57ff1154ec1eb115ee89ca5afac2b5f4e1303a71bb19e85267`
- lidarMapping: `7dbf87a75a6aa8e9dabb32c5494b1152bc90525d73362d31f293136710298ef8`

큐를 멈춰 추가 잘못된 재생을 막았고 진행 중이던 원본 재생은 마친 뒤 큐만 종료했다. fork build/devel/logs까지 비운 clean build를 수행하자 실제 Claude 원격 커밋은 `cv::Mat`의 미해결 심볼로 링크에 실패했다. CMake에서 cv_bridge를 제거한 뒤 cloudProcess에 OpenCV_LIBRARIES를 직접 연결하지 않은 문제다. **원격 커밋 자체의 판정은 빌드 실패**다.

`claude_2dcc39e_opencv.patch`는 cloudProcess의 target_link_libraries에 OpenCV_LIBRARIES 한 항목만 추가한다. 별도 `garlio_2dcc39e_linkfix` 사본과 `claude_linkfix_*` 실행은 이 패치가 적용된 진단 결과이며, 정확한 원격 커밋의 결과로 표기하지 않는다. 원격 브랜치와 Claude 작업 트리는 수정하지 않았다.

시간 경계 개선본도 같은 방식으로 build/devel/logs를 비운 독립 재빌드를 수행했다. 기존과 clean build의 cloudProcess/lidarMapping 해시는 각각 정확히 일치했다. lidarMapping은 `5202204611a1748e3d8b69bf79d2f0f02591c96a8ebb3f441760400b965e5071`이며 실제 시간 경계/속도 guard/지연 진단 문자열도 포함한다. 따라서 해당 후보 실험은 유지한다.

재발 방지: `Dockerfile.revision`은 항상 fork build/devel까지 삭제하고 전체 컴파일 후 manifest와 실행 파일 해시를 남긴다. 실험 runner도 실제 선택된 바이너리 해시를 기록한다. 이 오류와 clean build 실패를 성공 횟수에서 숨기지 않는다. 이 기록의 결과·증거는 최종 보고와 함께 보존한다.
