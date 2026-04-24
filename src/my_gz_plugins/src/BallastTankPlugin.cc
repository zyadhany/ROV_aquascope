#include <algorithm>
#include <atomic>
#include <chrono>
#include <memory>
#include <string>

#include <gz/math/Vector3.hh>
#include <gz/msgs/int32.pb.h>
#include <gz/plugin/Register.hh>
#include <gz/sim/Link.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/System.hh>
#include <gz/transport/Node.hh>

namespace my_plugins
{

class BallastTankPlugin:
  public gz::sim::System,
  public gz::sim::ISystemConfigure,
  public gz::sim::ISystemPreUpdate
{
  public: void Configure(
      const gz::sim::Entity &_entity,
      const std::shared_ptr<const sdf::Element> &_sdf,
      gz::sim::EntityComponentManager &_ecm,
      gz::sim::EventManager & /*_eventMgr*/) override
  {
    this->model = gz::sim::Model(_entity);

    if (!this->model.Valid(_ecm))
    {
      std::cerr << "[BallastTankPlugin] Invalid model entity\n";
      return;
    }

    this->linkName = _sdf->Get<std::string>("link_name", "base_link").first;
    this->topic = _sdf->Get<std::string>("topic", "/rov/ballast_cmd").first;
    this->maxWeight = _sdf->Get<double>("max_weight", 1.0).first;
    this->currentWeight = _sdf->Get<double>("initial_weight", 0.0).first;
    this->fillRate = _sdf->Get<double>("fill_rate", 0.1).first;

    this->currentWeight = std::clamp(this->currentWeight, 0.0, this->maxWeight);

    this->linkEntity = this->model.LinkByName(_ecm, this->linkName);
    if (this->linkEntity == gz::sim::kNullEntity)
    {
      std::cerr << "[BallastTankPlugin] Link [" << this->linkName << "] not found\n";
      return;
    }

    this->node.Subscribe(this->topic, &BallastTankPlugin::OnCmd, this);

    std::cout << "[BallastTankPlugin] Loaded\n";
    std::cout << "  link_name      = " << this->linkName << "\n";
    std::cout << "  topic          = " << this->topic << "\n";
    std::cout << "  max_weight     = " << this->maxWeight << "\n";
    std::cout << "  initial_weight = " << this->currentWeight << "\n";
    std::cout << "  fill_rate      = " << this->fillRate << "\n";
  }

  public: void PreUpdate(
      const gz::sim::UpdateInfo &_info,
      gz::sim::EntityComponentManager &_ecm) override
  {
    if (_info.paused)
      return;

    if (this->linkEntity == gz::sim::kNullEntity)
      return;

    double dt = std::chrono::duration<double>(_info.dt).count();
    if (dt <= 0.0)
      return;

    int cmd = this->command.load();

    if (cmd == 1)
      this->currentWeight += this->fillRate * dt;
    else if (cmd == 2)
      this->currentWeight -= this->fillRate * dt;

    this->currentWeight = std::clamp(this->currentWeight, 0.0, this->maxWeight);

    gz::sim::Link link(this->linkEntity);

    double forceZ = -this->currentWeight * 9.81;

    link.AddWorldWrench(
      _ecm,
      gz::math::Vector3d(0, 0, forceZ),
      gz::math::Vector3d(0, 0, 0));
  }

  private: void OnCmd(const gz::msgs::Int32 &_msg)
  {
    int value = _msg.data();
    if (value == 0 || value == 1 || value == 2)
      this->command.store(value);
  }

  private: gz::sim::Model model{gz::sim::kNullEntity};
  private: gz::sim::Entity linkEntity{gz::sim::kNullEntity};

  private: std::string linkName{"base_link"};
  private: std::string topic{"/rov/ballast_cmd"};

  private: double maxWeight{1.0};
  private: double currentWeight{0.0};
  private: double fillRate{0.1};

  private: std::atomic<int> command{0};

  private: gz::transport::Node node;
};

}  // namespace my_plugins

GZ_ADD_PLUGIN(
    my_plugins::BallastTankPlugin,
    gz::sim::System,
    my_plugins::BallastTankPlugin::ISystemConfigure,
    my_plugins::BallastTankPlugin::ISystemPreUpdate)

GZ_ADD_PLUGIN_ALIAS(
    my_plugins::BallastTankPlugin,
    "my_plugins::BallastTankPlugin")
