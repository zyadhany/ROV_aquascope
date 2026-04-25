from __future__ import annotations

from ..core.ros_interface import RosInterface
from ..flowchart.flowchart_manager import FlowchartManager
from ..services.service_manager import ServiceManager

ros_interface = RosInterface()
flowchart_manager = FlowchartManager(ros_interface)
service_manager = ServiceManager(ros_interface)
