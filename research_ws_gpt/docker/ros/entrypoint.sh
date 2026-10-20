#!/usr/bin/env bash
set -e
source /opt/ros/noetic/setup.bash
source /opt/research/catkin_ws/devel/setup.bash
case "${RESEARCH_GARLIO_VARIANT:-baseline}" in
  baseline) ;;
  fork) source /opt/research/fork_ws/devel/setup.bash ;;
  *) echo "RESEARCH_GARLIO_VARIANT must be baseline or fork." >&2; exit 2 ;;
esac
exec "$@"
