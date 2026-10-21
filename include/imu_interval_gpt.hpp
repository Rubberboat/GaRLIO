// Clip measured IMU intervals to the sweep; no extrapolation or new messages.
#pragma once
#include <algorithm>
#include <cmath>
namespace garlio_gpt {
struct ImuInterval { double begin, end, midpoint_fraction; };
inline bool clippedImuInterval(double head, double tail, double begin, double end,
                               ImuInterval& interval) {
    if (!std::isfinite(head) || !std::isfinite(tail) || !std::isfinite(begin) ||
        !std::isfinite(end) || tail <= head || end <= begin) return false;
    interval.begin = std::max(head, begin);
    interval.end = std::min(tail, end);
    if (interval.end <= interval.begin) return false;
    interval.midpoint_fraction = ((interval.begin-head)+(interval.end-head))*0.5/(tail-head);
    return true;
}
}
