#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <mutex>
#include <random>
#include <sstream>
#include <string>

#include <gz/common/Console.hh>
#include <gz/msgs/laserscan.pb.h>
#include <gz/msgs/stringmsg.pb.h>
#include <gz/plugin/Register.hh>
#include <gz/sim/System.hh>
#include <gz/transport/Node.hh>

namespace rov_gz_plugins
{
class ScanningSonarPlugin:
  public gz::sim::System,
  public gz::sim::ISystemConfigure,
  public gz::sim::ISystemPostUpdate
{
public:
  void Configure(
    const gz::sim::Entity &,
    const std::shared_ptr<const sdf::Element> &_sdf,
    gz::sim::EntityComponentManager &,
    gz::sim::EventManager &) override
  {
    this->inputScanTopic = this->ReadString(
      _sdf, "input_scan_topic", "/rov/scanning_sonar/internal_scan");

    this->outputTopic = this->ReadString(
      _sdf, "topic", "/rov/scanning_sonar/reading");

    this->minAngle = this->ReadDouble(_sdf, "min_angle", -M_PI);
    this->maxAngle = this->ReadDouble(_sdf, "max_angle", M_PI);

    // Support both names.
    this->frequency = this->ReadDouble(_sdf, "frequency", 10.0);
    this->frequency = this->ReadDouble(_sdf, "update_rate", this->frequency);

    this->angleStep = this->ReadDouble(_sdf, "angle_step", 0.0872665); // 5 deg

    this->minDistance = this->ReadDouble(_sdf, "min_distance", 0.10);
    this->maxDistance = this->ReadDouble(_sdf, "max_distance", 8.0);
    this->resolution = this->ReadDouble(_sdf, "resolution", 0.01);
    this->noiseStdDev = this->ReadDouble(_sdf, "noise_stddev", 0.0);
    this->pingPong = this->ReadBool(_sdf, "ping_pong", false);

    if (this->frequency <= 0.0)
      this->frequency = 10.0;

    if (this->angleStep <= 0.0)
      this->angleStep = 0.0872665;

    if (this->maxAngle < this->minAngle)
      std::swap(this->minAngle, this->maxAngle);

    if (this->maxDistance < this->minDistance)
      std::swap(this->minDistance, this->maxDistance);

    this->currentAngle = this->minAngle;
    this->direction = 1;

    this->publisher = this->node.Advertise<gz::msgs::StringMsg>(
      this->outputTopic);

    if (!this->node.Subscribe(
      this->inputScanTopic,
      &ScanningSonarPlugin::OnScan,
      this))
    {
      gzerr << "[ScanningSonarPlugin] Failed to subscribe to "
            << this->inputScanTopic << "\n";
    }

    this->noise = std::normal_distribution<double>(0.0, this->noiseStdDev);

    gzmsg << "[ScanningSonarPlugin] Loaded\n"
          << "  input_scan_topic = " << this->inputScanTopic << "\n"
          << "  topic            = " << this->outputTopic << "\n"
          << "  min_angle        = " << this->minAngle << "\n"
          << "  max_angle        = " << this->maxAngle << "\n"
          << "  frequency        = " << this->frequency << "\n"
          << "  angle_step       = " << this->angleStep << "\n"
          << "  min_distance     = " << this->minDistance << "\n"
          << "  max_distance     = " << this->maxDistance << "\n"
          << "  resolution       = " << this->resolution << "\n"
          << "  noise_stddev     = " << this->noiseStdDev << "\n";
  }

  void PostUpdate(
    const gz::sim::UpdateInfo &_info,
    const gz::sim::EntityComponentManager &) override
  {
    if (_info.paused)
      return;

    const double simTime =
      std::chrono::duration<double>(_info.simTime).count();

    const double period = 1.0 / this->frequency;

    if (simTime < this->nextPublishTime)
      return;

    this->nextPublishTime = simTime + period;

    gz::msgs::LaserScan scanCopy;
    {
      std::lock_guard<std::mutex> lock(this->scanMutex);

      if (!this->hasScan)
        return;

      scanCopy = this->lastScan;
    }

    const auto result = this->DistanceAtAngle(scanCopy, this->currentAngle);

    this->PublishReading(
      simTime,
      this->currentAngle,
      result.first,
      result.second);

    this->AdvanceAngle();
  }

private:
  static double ReadDouble(
    const std::shared_ptr<const sdf::Element> &_sdf,
    const std::string &_name,
    double _defaultValue)
  {
    if (_sdf->HasElement(_name))
      return _sdf->Get<double>(_name);

    return _defaultValue;
  }

  static bool ReadBool(
    const std::shared_ptr<const sdf::Element> &_sdf,
    const std::string &_name,
    bool _defaultValue)
  {
    if (_sdf->HasElement(_name))
      return _sdf->Get<bool>(_name);

    return _defaultValue;
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

  void OnScan(const gz::msgs::LaserScan &_msg)
  {
    std::lock_guard<std::mutex> lock(this->scanMutex);
    this->lastScan = _msg;
    this->hasScan = true;
  }

  std::pair<double, bool> DistanceAtAngle(
    const gz::msgs::LaserScan &_scan,
    double _angle)
  {
    const int rangeCount = _scan.ranges_size();

    if (rangeCount <= 0)
      return {this->maxDistance, false};

    const double scanMin = _scan.angle_min();
    const double scanMax = _scan.angle_max();

    if (_angle < scanMin || _angle > scanMax)
      return {this->maxDistance, false};

    const double angleStep =
      rangeCount > 1
        ? (scanMax - scanMin) / static_cast<double>(rangeCount - 1)
        : 0.0;

    if (angleStep <= 0.0)
      return {this->maxDistance, false};

    int index = static_cast<int>(
      std::round((_angle - scanMin) / angleStep));

    index = std::clamp(index, 0, rangeCount - 1);

    double distance = _scan.ranges(index);

    bool valid =
      std::isfinite(distance) &&
      distance >= this->minDistance &&
      distance <= this->maxDistance;

    if (!valid)
    {
      distance = this->maxDistance;
    }
    else
    {
      if (this->noiseStdDev > 0.0)
      {
        distance += this->noise(this->rng);
      }

      distance = std::clamp(
        distance,
        this->minDistance,
        this->maxDistance);

      if (this->resolution > 0.0)
      {
        distance =
          std::round(distance / this->resolution) * this->resolution;
      }
    }

    return {distance, valid};
  }

  void PublishReading(
    double _simTime,
    double _angleRad,
    double _distance,
    bool _valid)
  {
    const double angleDeg = _angleRad * 180.0 / M_PI;

    std::ostringstream json;
    json << std::fixed << std::setprecision(4)
         << "{"
         << "\"stamp\":" << _simTime << ","
         << "\"angle_rad\":" << _angleRad << ","
         << "\"angle_deg\":" << angleDeg << ","
         << "\"distance_m\":" << _distance << ","
         << "\"valid\":" << (_valid ? "true" : "false")
         << "}";

    gz::msgs::StringMsg msg;
    msg.set_data(json.str());

    this->publisher.Publish(msg);
  }

  void AdvanceAngle()
  {
    if (this->pingPong)
    {
      this->currentAngle += this->direction * this->angleStep;

      if (this->currentAngle >= this->maxAngle)
      {
        this->currentAngle = this->maxAngle;
        this->direction = -1;
      }
      else if (this->currentAngle <= this->minAngle)
      {
        this->currentAngle = this->minAngle;
        this->direction = 1;
      }

      return;
    }

    this->currentAngle += this->angleStep;

    if (this->currentAngle > this->maxAngle)
      this->currentAngle = this->minAngle;
  }

private:
  gz::transport::Node node;
  gz::transport::Node::Publisher publisher;

  std::string inputScanTopic;
  std::string outputTopic;

  double minAngle{-M_PI};
  double maxAngle{M_PI};
  double frequency{10.0};
  double angleStep{0.0872665};

  double minDistance{0.10};
  double maxDistance{8.0};
  double resolution{0.01};
  double noiseStdDev{0.0};

  bool pingPong{false};

  double currentAngle{-M_PI};
  int direction{1};

  double nextPublishTime{0.0};

  std::mutex scanMutex;
  gz::msgs::LaserScan lastScan;
  bool hasScan{false};

  std::default_random_engine rng{std::random_device{}()};
  std::normal_distribution<double> noise{0.0, 0.0};
};
}

GZ_ADD_PLUGIN(
  rov_gz_plugins::ScanningSonarPlugin,
  gz::sim::System,
  rov_gz_plugins::ScanningSonarPlugin::ISystemConfigure,
  rov_gz_plugins::ScanningSonarPlugin::ISystemPostUpdate)

GZ_ADD_PLUGIN_ALIAS(
  rov_gz_plugins::ScanningSonarPlugin,
  "rov_gz_plugins::ScanningSonarPlugin")