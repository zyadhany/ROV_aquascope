from __future__ import annotations

from typing import Any

from ..blocks.base_block import BaseBlock
from ..blocks.camera_block import CameraBlock
from ..blocks.light_block import LightBlock
from ..blocks.node_block import NodeBlock
from ..blocks.pump_block import PumpBlock
from ..blocks.sensor_block import SensorBlock
from ..blocks.thruster_block import ThrusterBlock
from ..blocks.topic_block import TopicBlock
from ..core.ros_interface import RosInterface


class BlockFactory:
    _TYPE_MAP: dict[str, type[BaseBlock]] = {
        'thruster': ThrusterBlock,
        'pump': PumpBlock,
        'light': LightBlock,
        'camera': CameraBlock,
        'sensor': SensorBlock,
        'topic': TopicBlock,
        'node': NodeBlock,
        'interface': BaseBlock,
        'software': BaseBlock,
        'service': BaseBlock,
    }

    @classmethod
    def create_block(
        cls,
        raw_config: dict[str, Any],
        ros_interface: RosInterface | None = None,
    ) -> BaseBlock:
        block_type = str(raw_config.get('type', '')).strip().lower()

        if not block_type:
            raise ValueError('Block config missing required field: type')

        block_class = cls._TYPE_MAP.get(block_type)

        if block_class is None:
            raise ValueError(f'Unknown block type: {block_type}')

        return block_class(raw_config, ros_interface=ros_interface)
