FROM osrf/ros:noetic-desktop-full
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# ROS dependencies are already in desktop-full. Do not contact the EOL ROS apt
# repository; install additional packages from Ubuntu and PyPI only.
RUN rm -f /etc/apt/sources.list.d/ros*.list /etc/apt/sources.list.d/ros*.sources \
    && ! grep -R -E 'packages\.ros\.org|snapshots\.ros\.org' /etc/apt/sources.list /etc/apt/sources.list.d \
    && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       build-essential cmake git ca-certificates pkg-config libeigen3-dev \
       libceres-dev libopencv-dev libpcl-dev libapr1-dev python3-dev \
       python3-pip python3-numpy python3-yaml python3-psutil \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m pip install --no-cache-dir catkin-tools==0.9.5

WORKDIR /opt/research
COPY sources.lock.json ./
COPY scripts/bootstrap_sources.py scripts/bootstrap_sources.py
RUN python3 scripts/bootstrap_sources.py
ARG BUILD_JOBS=2
RUN cmake -S third_party/Livox-SDK -B /tmp/livox-build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /tmp/livox-build --parallel "${BUILD_JOBS}" \
    && cmake --install /tmp/livox-build \
    && test -f /usr/local/lib/liblivox_sdk_static.a
# Keep the upstream CMakeLists untouched (some force Debug with -O3).
# Isolated catkin builds also avoid cross-package CMake target collisions.
RUN source /opt/ros/noetic/setup.bash \
    && cd catkin_ws \
    && catkin config --extend /opt/ros/noetic --cmake-args -DCMAKE_BUILD_TYPE=Release \
    && catkin build livox_ros_driver --no-status --jobs "${BUILD_JOBS}" \
    && catkin build garlio fast_lio point_lio --no-status --jobs "${BUILD_JOBS}" \
    && test -x devel/lib/garlio/cloudProcess \
    && test -x devel/lib/garlio/lidarMapping \
    && test -x devel/lib/fast_lio/fastlio_mapping \
    && test -x devel/lib/point_lio/pointlio_mapping
COPY . /opt/research
RUN python3 scripts/bootstrap_sources.py --verify-only \
    && mkdir -p catkin_ws/src/Point-LIO/Log catkin_ws/src/Point-LIO/PCD \
                catkin_ws/src/FAST_LIO/Log catkin_ws/src/FAST_LIO/PCD \
    && dpkg-query -W > /opt/research/build-packages.txt \
    && python3 -m pip freeze > /opt/research/build-python.txt
ARG RESEARCH_GIT_COMMIT=unknown
ENV RESEARCH_IMAGE_COMMIT=${RESEARCH_GIT_COMMIT}
LABEL org.opencontainers.image.revision=${RESEARCH_GIT_COMMIT}
ENV MPLBACKEND=Agg
ENTRYPOINT ["bash", "/opt/research/docker/ros/entrypoint.sh"]
CMD ["bash"]
