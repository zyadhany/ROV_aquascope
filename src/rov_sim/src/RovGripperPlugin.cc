#include <string>

#include <sdf/Element.hh>

#include <gz/common/Console.hh>
#include <gz/msgs/boolean.pb.h>
#include <gz/plugin/Register.hh>
#include <gz/sim/Entity.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/Model.hh>
#include <gz/sim/System.hh>
#include <gz/sim/components/JointForceCmd.hh>
#include <gz/transport/Node.hh>

namespace rov_gz_plugins
{

class RovGripperPlugin:
  public gz::sim::System,
  public gz::sim::ISystemConfigure,
  public gz::sim::ISystemPreUpdate
{
public:
  void Configure(
    const gz::sim::Entity &_entity,
    const std::shared_ptr<const sdf::Element> &_sdf,
    gz::sim::EntityComponentManager &_ecm,
    gz::sim::EventManager &) override
  {
    this->model = gz::sim::Model(_entity);

    if (!this->model.Valid(_ecm))
    {
      gzerr << "[RovGripperPlugin] Invalid model entity\n";
      return;
    }

    this->topic = this->ReadString(_sdf, "topic", "/rov/gripper/open_cmd");

    this->leftJointName =
      this->ReadString(_sdf, "left_joint", "palm_left_finger_joint");

    this->rightJointName =
      this->ReadString(_sdf, "right_joint", "palm_right_finger_joint");

    this->mainForce = this->ReadDouble(_sdf, "main_force", 20.0);

    this->leftCloseSign =
      this->ReadDouble(_sdf, "left_close_sign", -1.0);

    this->rightCloseSign =
      this->ReadDouble(_sdf, "right_close_sign", 1.0);

    this->leftJoint = this->model.JointByName(_ecm, this->leftJointName);
    this->rightJoint = this->model.JointByName(_ecm, this->rightJointName);

    if (this->leftJoint == gz::sim::kNullEntity)
    {
      gzerr << "[RovGripperPlugin] Missing joint: "
            << this->leftJointName << "\n";
      return;
    }

    if (this->rightJoint == gz::sim::kNullEntity)
    {
      gzerr << "[RovGripperPlugin] Missing joint: "
            << this->rightJointName << "\n";
      return;
    }

    this->CreateForceCmd(_ecm, this->leftJoint);
    this->CreateForceCmd(_ecm, this->rightJoint);

    if (!this->node.Subscribe(
      this->topic,
      &RovGripperPlugin::OnCommand,
      this))
    {
      gzerr << "[RovGripperPlugin] Failed to subscribe to "
            << this->topic << "\n";
      return;
    }

    gzmsg << "[RovGripperPlugin] Loaded\n"
          << "  topic       = " << this->topic << "\n"
          << "  left_joint  = " << this->leftJointName << "\n"
          << "  right_joint = " << this->rightJointName << "\n"
          << "  main_force  = " << this->mainForce << "\n";
  }

  void PreUpdate(
    const gz::sim::UpdateInfo &_info,
    gz::sim::EntityComponentManager &_ecm) override
  {
    if (_info.paused)
      return;

    // true = open, false = close
    const double stateSign = this->isOpen ? -1.0 : 1.0;

    const double leftForce =
      stateSign * this->leftCloseSign * this->mainForce;

    const double rightForce =
      stateSign * this->rightCloseSign * this->mainForce;

    this->SetForce(_ecm, this->leftJoint, leftForce);
    this->SetForce(_ecm, this->rightJoint, rightForce);
  }

private:
  void OnCommand(const gz::msgs::Boolean &_msg)
  {
    this->isOpen = _msg.data();

    if (this->isOpen)
      gzmsg << "[RovGripperPlugin] Command: OPEN\n";
    else
      gzmsg << "[RovGripperPlugin] Command: CLOSE\n";
  }

  void CreateForceCmd(
    gz::sim::EntityComponentManager &_ecm,
    gz::sim::Entity _joint)
  {
    if (!_ecm.Component<gz::sim::components::JointForceCmd>(_joint))
    {
      _ecm.CreateComponent(
        _joint,
        gz::sim::components::JointForceCmd({0.0}));
    }
  }

  void SetForce(
    gz::sim::EntityComponentManager &_ecm,
    gz::sim::Entity _joint,
    double _force)
  {
    auto cmd =
      _ecm.Component<gz::sim::components::JointForceCmd>(_joint);

    if (cmd)
    {
      cmd->Data()[0] = _force;
    }
    else
    {
      _ecm.CreateComponent(
        _joint,
        gz::sim::components::JointForceCmd({_force}));
    }
  }

  static std::string ReadString(
    const std::shared_ptr<const sdf::Element> &_sdf,
    const std::string &_name,
    const std::string &_defaultValue)
  {
    if (_sdf->HasElement(_name))
      return _sdf->Get<std::string>(_name);

    return _defaultValue;
  }

  static double ReadDouble(
    const std::shared_ptr<const sdf::Element> &_sdf,
    const std::string &_name,
    double _defaultValue)
  {
    if (_sdf->HasElement(_name))
      return _sdf->Get<double>(_name);

    return _defaultValue;
  }

private:
  gz::sim::Model model{gz::sim::kNullEntity};
  gz::transport::Node node;

  std::string topic{"/rov/gripper/open_cmd"};

  std::string leftJointName{"palm_left_finger_joint"};
  std::string rightJointName{"palm_right_finger_joint"};

  gz::sim::Entity leftJoint{gz::sim::kNullEntity};
  gz::sim::Entity rightJoint{gz::sim::kNullEntity};

  double mainForce{20.0};

  double leftCloseSign{-1.0};
  double rightCloseSign{1.0};

  bool isOpen{true};
};

}

GZ_ADD_PLUGIN(
  rov_gz_plugins::RovGripperPlugin,
  gz::sim::System,
  rov_gz_plugins::RovGripperPlugin::ISystemConfigure,
  rov_gz_plugins::RovGripperPlugin::ISystemPreUpdate)

GZ_ADD_PLUGIN_ALIAS(
  rov_gz_plugins::RovGripperPlugin,
  "rov_gz_plugins::RovGripperPlugin")