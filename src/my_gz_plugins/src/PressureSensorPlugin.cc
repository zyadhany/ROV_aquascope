#include <algorithm>
#include <chrono>
#include <cmath>
#include <iostream>
#include <memory>
#include <random>
#include <string>

#include <sdf/Element.hh>

#include <gz/math/Pose3.hh>
#include <gz/math/Vector3.hh>
#include <gz/msgs/double.pb.h>
#include <gz/msgs/fluid_pressure.pb.h>
#include <gz/plugin/Register.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/System.hh>
#include <gz/sim/Util.hh>
#include <gz/transport/Node.hh>

namespace my_plugins
{

class PressureSensorPlugin
    : public gz::sim::System,
      public gz::sim::ISystemConfigure,
      public gz::sim::ISystemPostUpdate
{
public:
  void Configure(const gz::sim::Entity &_entity,
                 const std::shared_ptr<const sdf::Element> &_sdf,
                 gz::sim::EntityComponentManager &_ecm,
                 gz::sim::EventManager &) override
  {
    this->model = gz::sim::Model(_entity);

    if (_sdf->HasElement("parent_link_name"))
      this->parentLinkName = _sdf->Get<std::string>("parent_link_name");

    if (_sdf->HasElement("port_offset"))
      this->portOffset = _sdf->Get<gz::math::Vector3d>("port_offset");

    if (_sdf->HasElement("port_axis_local"))
      this->portAxisLocal = _sdf->Get<gz::math::Vector3d>("port_axis_local");

    if (_sdf->HasElement("water_surface_z"))
      this->waterSurfaceZ = _sdf->Get<double>("water_surface_z");

    if (_sdf->HasElement("atmospheric_pressure_pa"))
      this->atmosphericPressurePa =
          _sdf->Get<double>("atmospheric_pressure_pa");

    if (_sdf->HasElement("water_density_kgpm3"))
      this->waterDensity = _sdf->Get<double>("water_density_kgpm3");

    if (_sdf->HasElement("gravity_mps2"))
      this->gravity = _sdf->Get<double>("gravity_mps2");

    if (_sdf->HasElement("update_rate_hz"))
      this->updateRateHz = _sdf->Get<double>("update_rate_hz");

    if (_sdf->HasElement("bias_pa"))
      this->biasPa = _sdf->Get<double>("bias_pa");

    if (_sdf->HasElement("noise_stddev_pa"))
      this->noiseStddevPa = _sdf->Get<double>("noise_stddev_pa");

    if (_sdf->HasElement("drift_stddev_pa_per_sqrt_s"))
      this->driftStddevPaPerSqrtS =
          _sdf->Get<double>("drift_stddev_pa_per_sqrt_s");

    if (_sdf->HasElement("tau_seconds"))
      this->tauSeconds = _sdf->Get<double>("tau_seconds");

    if (_sdf->HasElement("quantization_pa"))
      this->quantizationPa = _sdf->Get<double>("quantization_pa");

    if (_sdf->HasElement("dynamic_pressure_coeff"))
      this->dynamicPressureCoeff =
          _sdf->Get<double>("dynamic_pressure_coeff");

    if (_sdf->HasElement("clamp_above_surface"))
      this->clampAboveSurface = _sdf->Get<bool>("clamp_above_surface");

    if (_sdf->HasElement("pressure_topic"))
      this->pressureTopic = _sdf->Get<std::string>("pressure_topic");

    if (_sdf->HasElement("depth_topic"))
      this->depthTopic = _sdf->Get<std::string>("depth_topic");

    this->parentLinkEntity = this->model.LinkByName(_ecm, this->parentLinkName);

    if (this->parentLinkEntity == gz::sim::kNullEntity)
    {
      std::cerr << "[PressureSensorPlugin] Could not find link ["
                << this->parentLinkName << "]\n";
      return;
    }

    if (this->portAxisLocal.Length() < 1e-9)
      this->portAxisLocal = gz::math::Vector3d::UnitX;
    else
      this->portAxisLocal.Normalize();

    this->pressurePub =
        this->node.Advertise<gz::msgs::FluidPressure>(this->pressureTopic);

    this->depthPub =
        this->node.Advertise<gz::msgs::Double>(this->depthTopic);
  }

  void PostUpdate(const gz::sim::UpdateInfo &_info,
                  const gz::sim::EntityComponentManager &_ecm) override
  {
    if (_info.paused)
      return;

    if (this->parentLinkEntity == gz::sim::kNullEntity)
      return;

    const double simTimeSec = this->ToSec(_info.simTime);

    const gz::math::Pose3d linkPose =
        gz::sim::worldPose(this->parentLinkEntity, _ecm);

    const gz::math::Vector3d portPosWorld =
        linkPose.Pos() + linkPose.Rot().RotateVector(this->portOffset);

    const gz::math::Vector3d portAxisWorld =
        linkPose.Rot().RotateVector(this->portAxisLocal);

    double dt = 0.0;
    gz::math::Vector3d portVelWorld(0, 0, 0);

    if (this->initialized)
    {
      dt = simTimeSec - this->lastSimTimeSec;
      if (dt > 1e-9)
        portVelWorld = (portPosWorld - this->lastPortPosWorld) / dt;
    }

    this->lastSimTimeSec = simTimeSec;
    this->lastPortPosWorld = portPosWorld;

    const double rawDepthM =
        this->clampAboveSurface
            ? std::max(0.0, this->waterSurfaceZ - portPosWorld.Z())
            : (this->waterSurfaceZ - portPosWorld.Z());

    double hydrostaticPressurePa =
        this->atmosphericPressurePa + this->waterDensity * this->gravity * rawDepthM;

    if (this->clampAboveSurface && rawDepthM <= 0.0)
      hydrostaticPressurePa = this->atmosphericPressurePa;

    double flowPressurePa = 0.0;
    if (dt > 1e-9 && this->dynamicPressureCoeff > 0.0)
    {
      const double vn = portVelWorld.Dot(portAxisWorld);

      if (vn > 0.0)
      {
        flowPressurePa = this->dynamicPressureCoeff *
                         0.5 * this->waterDensity * vn * vn;
      }
    }

    if (dt > 1e-9 && this->driftStddevPaPerSqrtS > 0.0)
    {
      this->randomWalkBiasPa +=
          this->driftStddevPaPerSqrtS * std::sqrt(dt) * this->Gaussian();
    }

    double measuredPressurePa =
        hydrostaticPressurePa +
        flowPressurePa +
        this->biasPa +
        this->randomWalkBiasPa;

    if (this->noiseStddevPa > 0.0)
      measuredPressurePa += this->noiseStddevPa * this->Gaussian();

    if (this->quantizationPa > 0.0)
    {
      measuredPressurePa =
          std::round(measuredPressurePa / this->quantizationPa) *
          this->quantizationPa;
    }

    if (!this->initialized)
    {
      this->filteredPressurePa = measuredPressurePa;
      this->initialized = true;
    }
    else
    {
      if (this->tauSeconds <= 1e-9 || dt <= 1e-9)
      {
        this->filteredPressurePa = measuredPressurePa;
      }
      else
      {
        const double alpha = 1.0 - std::exp(-dt / this->tauSeconds);
        this->filteredPressurePa +=
            alpha * (measuredPressurePa - this->filteredPressurePa);
      }
    }

    if (this->updateRateHz > 0.0)
    {
      const double minPeriod = 1.0 / this->updateRateHz;
      if ((simTimeSec - this->lastPublishTimeSec) < minPeriod)
        return;
    }

    this->lastPublishTimeSec = simTimeSec;

    double estimatedDepthM =
        (this->filteredPressurePa - this->atmosphericPressurePa) /
        (this->waterDensity * this->gravity);

    if (this->clampAboveSurface)
      estimatedDepthM = std::max(0.0, estimatedDepthM);

    gz::msgs::FluidPressure pressureMsg;
    pressureMsg.set_pressure(this->filteredPressurePa);
    pressureMsg.set_variance(this->noiseStddevPa * this->noiseStddevPa);
    this->pressurePub.Publish(pressureMsg);

    gz::msgs::Double depthMsg;
    depthMsg.set_data(estimatedDepthM);
    this->depthPub.Publish(depthMsg);
  }

private:
  double ToSec(const std::chrono::steady_clock::duration &_dur) const
  {
    return std::chrono::duration_cast<std::chrono::duration<double>>(_dur).count();
  }

  double Gaussian()
  {
    return this->normalDist(this->rng);
  }

private:
  gz::sim::Model model{gz::sim::kNullEntity};
  gz::sim::Entity parentLinkEntity{gz::sim::kNullEntity};

  std::string parentLinkName{"base_link"};
  gz::math::Vector3d portOffset{0.0, 0.0, 0.0};
  gz::math::Vector3d portAxisLocal{1.0, 0.0, 0.0};

  double waterSurfaceZ{0.0};
  double atmosphericPressurePa{101325.0};
  double waterDensity{997.0};
  double gravity{9.81};

  double updateRateHz{30.0};

  double biasPa{0.0};
  double noiseStddevPa{120.0};                 // ~1.2 cm water
  double driftStddevPaPerSqrtS{3.0};          // slow random walk
  double tauSeconds{0.08};                    // sensor lag
  double quantizationPa{10.0};                // ADC / quantization
  double dynamicPressureCoeff{0.0};           // 0 = ideal depth port
  bool clampAboveSurface{true};

  std::string pressureTopic{"/rov/pressure"};
  std::string depthTopic{"/rov/depth"};

  bool initialized{false};
  double filteredPressurePa{101325.0};
  double randomWalkBiasPa{0.0};
  double lastSimTimeSec{0.0};
  double lastPublishTimeSec{-1e9};
  gz::math::Vector3d lastPortPosWorld{0.0, 0.0, 0.0};

  std::mt19937 rng{std::random_device{}()};
  std::normal_distribution<double> normalDist{0.0, 1.0};

  gz::transport::Node node;
  gz::transport::Node::Publisher pressurePub;
  gz::transport::Node::Publisher depthPub;
};

}  // namespace my_plugins

GZ_ADD_PLUGIN(
    my_plugins::PressureSensorPlugin,
    gz::sim::System,
    my_plugins::PressureSensorPlugin::ISystemConfigure,
    my_plugins::PressureSensorPlugin::ISystemPostUpdate)