#!/usr/bin/env python3
"""Record nav_msgs/Odometry header timestamps and poses verbatim as TUM."""
import argparse
import json
import math
from pathlib import Path
import threading


class TumWriter:
    def __init__(self, path):
        self.file = Path(path).open("x", buffering=1024 * 1024)
        self.lock = threading.Lock()
        self.stats = {"poses": 0, "first_stamp_ns": None, "last_stamp_ns": None,
                      "frame_id": None, "child_frame_id": None, "error": None}

    def write(self, sec, nsec, values, frame_id, child_frame_id):
        with self.lock:
            stamp = sec * 1_000_000_000 + nsec
            if not 0 <= nsec < 1_000_000_000 or stamp <= 0:
                raise ValueError("Invalid/zero header timestamp")
            if len(values) != 7 or not all(math.isfinite(x) for x in values):
                raise ValueError("Nonfinite/malformed pose")
            if abs(sum(x*x for x in values[3:]) - 1.0) > 0.002:
                raise ValueError("Quaternion is not unit length")
            if self.stats["poses"]:
                if stamp <= self.stats["last_stamp_ns"]:
                    raise ValueError("Repeated or backward Odometry header timestamp")
                if (frame_id, child_frame_id) != (self.stats["frame_id"], self.stats["child_frame_id"]):
                    raise ValueError("Odometry frame changed during recording")
            else:
                self.stats.update(first_stamp_ns=stamp, frame_id=frame_id, child_frame_id=child_frame_id)
            self.file.write(f"{sec}.{nsec:09d} " + " ".join(f"{x:.12g}" for x in values) + "\n")
            self.stats["poses"] += 1
            self.stats["last_stamp_ns"] = stamp

    def close(self):
        with self.lock:
            self.file.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--topic", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--stats", type=Path, required=True)
    args = p.parse_args()
    import rospy
    from nav_msgs.msg import Odometry
    writer = TumWriter(args.output)
    rospy.init_node("trajectory_recorder", anonymous=False)

    def callback(message):
        pose = message.pose.pose
        try:
            writer.write(message.header.stamp.secs, message.header.stamp.nsecs,
                         [pose.position.x, pose.position.y, pose.position.z,
                          pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w],
                         message.header.frame_id, message.child_frame_id)
        except (OSError, ValueError) as error:
            writer.stats["error"] = str(error)
            rospy.logfatal("Trajectory recording failed: %s", error)
            rospy.signal_shutdown(str(error))

    subscriber = rospy.Subscriber(args.topic, Odometry, callback, queue_size=200000,
                                  buff_size=64 * 1024 * 1024, tcp_nodelay=True)
    rospy.loginfo("Recording %s to %s using message header time", args.topic, args.output)
    try:
        rospy.spin()
    finally:
        subscriber.unregister()
        writer.close()
        if not writer.stats["poses"] and writer.stats["error"] is None:
            writer.stats["error"] = "No odometry received"
        args.stats.write_text(json.dumps(writer.stats, indent=2) + "\n")
    return 2 if writer.stats["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
