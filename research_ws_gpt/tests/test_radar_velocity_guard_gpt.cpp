#include "radar_velocity_guard_gpt.hpp"
#include <array>
#include <limits>
#include <stdexcept>
int main() {
    using V = std::array<double, 3>;
    using garlio_gpt::radarVelocityConsistent;
    auto require=[](bool ok){ if (!ok) throw std::runtime_error("radar guard regression"); };
    require(radarVelocityConsistent(V{4,0,0}, V{4.1,0.1,-0.1}));
    require(radarVelocityConsistent(V{0,0,0}, V{0.5,-0.5,0.5}));
    require(!radarVelocityConsistent(V{4,0,0}, V{4,0,0.500001}));
    require(!radarVelocityConsistent(V{4,0,0}, V{8,0,0}));
    require(!radarVelocityConsistent(V{0,0,0}, V{0,std::numeric_limits<double>::quiet_NaN(),0}));
    require(!radarVelocityConsistent(V{std::numeric_limits<double>::infinity(),0,0}, V{0,0,0}));
}
