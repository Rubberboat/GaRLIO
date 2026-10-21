#include "imu_interval_gpt.hpp"
#include <cmath>
#include <limits>
#include <stdexcept>
int main() {
    using namespace garlio_gpt;
    auto close=[](double x,double y){if(std::abs(x-y)>1e-10)throw std::runtime_error("interval integration mismatch");};
    auto require=[](bool x){if(!x)throw std::runtime_error("invalid interval handling");};
    ImuInterval v;
    require(!clippedImuInterval(1,1,0,2,v));
    require(!clippedImuInterval(2,1,0,2,v));
    require(!clippedImuInterval(0,1,1,2,v));
    require(!clippedImuInterval(0,std::numeric_limits<double>::infinity(),0,1,v));
    require(clippedImuInterval(0,1,0.2,0.4,v));
    close(v.begin,.2);close(v.end,.4);close(v.midpoint_fraction,.3);
    // Sparse measured acceleration a(t)=2t over [0,1], split by radar sweeps.
    double duration=0, delta_velocity=0, driving_variance=0;
    for(int k=0;k<10;++k) {
        require(clippedImuInterval(0,1,k*.1,(k+1)*.1,v));
        const double dt=v.end-v.begin;
        duration+=dt;delta_velocity+=2*v.midpoint_fraction*dt;
        driving_variance+=dt*dt*(1/dt);
    }
    close(duration,1);close(delta_velocity,1);close(driving_variance,1);
    // Irregular IMU sampling must cover exactly the requested sweep window.
    const double stamps[]={0,.017,.031,.08,.2,.7,1.1};duration=0;delta_velocity=0;
    for(int k=0;k<6;++k)if(clippedImuInterval(stamps[k],stamps[k+1],.025,.9,v)) {
        const double middle=stamps[k]+v.midpoint_fraction*(stamps[k+1]-stamps[k]);
        duration+=v.end-v.begin;delta_velocity+=2*middle*(v.end-v.begin);
    }
    close(duration,.875);close(delta_velocity,.9*.9-.025*.025);
}
