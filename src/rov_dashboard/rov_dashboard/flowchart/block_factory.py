from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..blocks.base_block import BaseBlock
from ..blocks.hardware_block import HardwareBlock
from ..blocks.node_block import NodeBlock
from ..blocks.topic_block import TopicBlock
from ..core.ros_interface import RosInterface


class BlockFactory:
    _LEGACY_HARDWARE_TYPES = {
        'camera',
        'interface',
        'light',
        'pump',
        'sensor',
        'service',
        'software',
        'thruster',
    }
    _TYPE_ALIASES = {
        'node': 'nodes',
    }
    _TYPE_MAP: dict[str, type[BaseBlock]] = {
        'hardware': HardwareBlock,
        'topic': TopicBlock,
        'nodes': NodeBlock,
    }

    @classmethod
    def _normalize_type(cls, block_type: str) -> str:
        block_type = block_type.strip().lower()
        block_type = cls._TYPE_ALIASES.get(block_type, block_type)

        if block_type in cls._LEGACY_HARDWARE_TYPES:
            return 'hardware'

        return block_type

    @classmethod
    def create_block(
        cls,
        raw_config: dict[str, Any],
        ros_interface: RosInterface | None = None,
    ) -> BaseBlock:
        block_type = cls._normalize_type(str(raw_config.get('type', '')))

        if not block_type:
            raise ValueError('Block config missing required field: type')

        block_class = cls._TYPE_MAP.get(block_type)

        if block_class is None:
            raise ValueError(f'Unknown block type: {block_type}')

        normalized_config = deepcopy(raw_config)
        normalized_config['type'] = block_type
        return block_class(normalized_config, ros_interface=ros_interface)
