#!/usr/bin/env bash
set -e
source /opt/ros/noetic/setup.bash
source /opt/research/catkin_ws/devel/setup.bash
exec "$@"
