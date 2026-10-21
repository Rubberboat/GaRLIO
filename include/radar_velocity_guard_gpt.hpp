// GaRLIO fork: keep emergency velocity refinement consistent with Doppler gating.
// The existing 0.5 m/s per-axis quality gate is unchanged.
#pragma once
#include <cmath>
namespace garlio_gpt {
template <typename Vector>
bool radarVelocityConsistent(const Vector& predicted_body, const Vector& radar_body) {
    for (int i = 0; i < 3; ++i) {
        if (!std::isfinite(predicted_body[i]) || !std::isfinite(radar_body[i]) ||
            std::abs(predicted_body[i] - radar_body[i]) > 0.5) return false;
    }
    return true;
}
}  // namespace garlio_gpt
