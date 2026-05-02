#include <mutex>
#include <string>

#include <gz/plugin/Register.hh>

#include <gz/sim/System.hh>
#include <gz/sim/Entity.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/Conversions.hh>

#include <gz/sim/components/Light.hh>
#include <gz/sim/components/LightCmd.hh>
#include <gz/sim/components/Name.hh>

#include <gz/msgs/boolean.pb.h>
#include <gz/msgs/light.pb.h>

#include <gz/transport/Node.hh>

namespace rov_gz_plugins
{
class RovSpotLightPlugin:
  public gz::sim::System,
  public gz::sim::ISystemConfigure,
  public gz::sim::ISystemPreUpdate
{
public:
  void Configure(
    const gz::sim::Entity &_entity,
    const std::shared_ptr<const sdf::Element> &_sdf,
    gz::sim::EntityComponentManager &,
    gz::sim::EventManager &) override
  {
    this->modelEntity = _entity;

    if (_sdf->HasElement("light_name"))
      this->lightName = _sdf->Get<std::string>("light_name");

    if (_sdf->HasElement("topic"))
      this->topicName = _sdf->Get<std::string>("topic");

    if (_sdf->HasElement("on_intensity"))
      this->onIntensity = _sdf->Get<double>("on_intensity");

    this->gzNode.Subscribe(
      this->topicName,
      &RovSpotLightPlugin::OnLightCmd,
      this);
  }

  void PreUpdate(
    const gz::sim::UpdateInfo &,
    gz::sim::EntityComponentManager &_ecm) override
  {
    bool shouldUpdate = false;
    bool turnOn = false;

    {
      std::lock_guard<std::mutex> lock(this->mutex);
      shouldUpdate = this->hasNewCommand;
      turnOn = this->lightOn;
      this->hasNewCommand = false;
    }

    if (!shouldUpdate)
      return;

    if (this->lightEntity == gz::sim::kNullEntity)
      this->FindLight(_ecm);

    if (this->lightEntity == gz::sim::kNullEntity)
      return;

    auto lightComp =
      _ecm.Component<gz::sim::components::Light>(this->lightEntity);

    if (!lightComp)
      return;

    // Build a full light message from the existing SDF light.
    // This avoids resetting direction, color, range, and spot parameters.
    gz::msgs::Light msg =
      gz::sim::convert<gz::msgs::Light>(lightComp->Data());

    msg.set_name(this->lightName);
    msg.set_type(gz::msgs::Light::SPOT);

    if (turnOn)
    {
      msg.set_intensity(this->onIntensity);
      msg.set_is_light_off(false);
    }
    else
    {
      msg.set_intensity(0.0);
      msg.set_is_light_off(true);
    }

    _ecm.SetComponentData<gz::sim::components::LightCmd>(
      this->lightEntity,
      msg);

    _ecm.SetChanged(
      this->lightEntity,
      gz::sim::components::LightCmd::typeId,
      gz::sim::ComponentState::PeriodicChange);
  }

private:
  void OnLightCmd(const gz::msgs::Boolean &_msg)
  {
    std::lock_guard<std::mutex> lock(this->mutex);
    this->lightOn = _msg.data();
    this->hasNewCommand = true;
  }

  void FindLight(gz::sim::EntityComponentManager &_ecm)
  {
    _ecm.Each<gz::sim::components::Light, gz::sim::components::Name>(
      [&](const gz::sim::Entity &_entity,
          const gz::sim::components::Light *,
          const gz::sim::components::Name *_name) -> bool
      {
        if (_name->Data() == this->lightName)
        {
          this->lightEntity = _entity;
          return false;
        }

        return true;
      });
  }

private:
  gz::transport::Node gzNode;

  gz::sim::Entity modelEntity{gz::sim::kNullEntity};
  gz::sim::Entity lightEntity{gz::sim::kNullEntity};

  std::string lightName{"front_led_light"};
  std::string topicName{"/rov/light/cmd"};

  double onIntensity{1.0};

  std::mutex mutex;
  bool lightOn{false};
  bool hasNewCommand{false};
};
}

GZ_ADD_PLUGIN(
  rov_gz_plugins::RovSpotLightPlugin,
  gz::sim::System,
  rov_gz_plugins::RovSpotLightPlugin::ISystemConfigure,
  rov_gz_plugins::RovSpotLightPlugin::ISystemPreUpdate)

GZ_ADD_PLUGIN_ALIAS(
  rov_gz_plugins::RovSpotLightPlugin,
  "rov_gz_plugins::RovSpotLightPlugin")