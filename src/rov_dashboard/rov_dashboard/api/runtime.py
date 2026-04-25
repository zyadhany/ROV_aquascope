from __future__ import annotations

from ..core.ros_interface import RosInterface
from ..flowchart.flowchart_manager import FlowchartManager
from ..services.node_manager import NodeManager
from ..services.service_manager import ServiceManager

ros_interface = RosInterface()
node_manager = NodeManager(ros_interface)
flowchart_manager = FlowchartManager(ros_interface)
service_manager = ServiceManager(ros_interface, node_manager)
