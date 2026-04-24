#include <memory>

#include <gz/msgs/boolean.pb.h>
#include <gz/plugin/Register.hh>
#include <gz/sim/System.hh>
#include <gz/sim/components/Light.hh>
#include <gz/sim/components/Name.hh>
#include <gz/transport/Node.hh>

namespace mysim
{
class HeadlightToggle
  : public gz::sim::System,
    public gz::sim::ISystemConfigure,
    public gz::sim::ISystemPreUpdate
{
  public:
    void Configure(
        const gz::sim::Entity &,
        const std::shared_ptr<const sdf::Element> &,
        gz::sim::EntityComponentManager &,
        gz::sim::EventManager &) override
    {
      // Only subscribe here.
      this->node.Subscribe("/headlight_cmd",
                           &HeadlightToggle::OnCmd, this);
    }

    void PreUpdate(
        const gz::sim::UpdateInfo &,
        gz::sim::EntityComponentManager &_ecm) override
    {
      // Keep searching until the light is found.
      if (this->lightEntity == gz::sim::kNullEntity)
      {
        _ecm.Each<gz::sim::components::Name, gz::sim::components::Light>(
          [&](const gz::sim::Entity &_entity,
              const gz::sim::components::Name *_name,
              const gz::sim::components::Light *) -> bool
          {
            if (_name->Data() == "headlight")
            {
              this->lightEntity = _entity;
              return false;
            }
            return true;
          });
      }

      if (this->lightEntity == gz::sim::kNullEntity)
        return;

      auto lightComp =
        _ecm.Component<gz::sim::components::Light>(this->lightEntity);

      if (!lightComp)
        return;

      auto light = lightComp->Data();
      light.SetLightOn(this->lampOn);

      _ecm.SetComponentData<gz::sim::components::Light>(
        this->lightEntity, light);
    }

  private:
    void OnCmd(const gz::msgs::Boolean &_msg)
    {
      this->lampOn = _msg.data();
    }

  private:
    gz::transport::Node node;
    gz::sim::Entity lightEntity{gz::sim::kNullEntity};
    bool lampOn{true};
};
}

GZ_ADD_PLUGIN(
  mysim::HeadlightToggle,
  gz::sim::System,
  gz::sim::ISystemConfigure,
  gz::sim::ISystemPreUpdate)