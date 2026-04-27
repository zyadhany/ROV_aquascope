from __future__ import annotations

from ..core.ros_interface import RosInterface
from ..flowchart.block_manager import BlockManager
from ..flowchart.flowchart_manager import FlowchartManager
from ..services.node_manager import NodeManager
from ..services.service_manager import ServiceManager

ros_interface = RosInterface()
block_manager = BlockManager(ros_interface)
node_manager = NodeManager(ros_interface, block_manager)
flowchart_manager = FlowchartManager(ros_interface, block_manager)
service_manager = ServiceManager(ros_interface, node_manager)
