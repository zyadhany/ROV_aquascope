from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import logging
from typing import Any

from .block_factory import BlockFactory
from ..blocks.base_block import BaseBlock
from ..core.config_loader import load_blocks_config, load_dashboard_config
from ..core.layout_store import load_layout, save_layout
from ..core.ros_interface import RosInterface


logger = logging.getLogger(__name__)


class FlowchartManager:
    def __init__(self, ros_interface: RosInterface | None = None) -> None:
        self.ros_interface = ros_interface or RosInterface()
        self._cached_block_items: list[dict[str, Any]] | None = None
        self._cached_blocks: list[BaseBlock] = []
        self._cached_blocks_by_id: dict[str, BaseBlock] = {}

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _normalize_block_id(self, block_id: str) -> str:
        block_id = str(block_id).strip()
        if not block_id:
            raise ValueError('Block ID cannot be empty')
        return block_id if block_id.startswith('/') else f'/{block_id}'

    def _load_block_items(self) -> list[dict[str, Any]]:
        blocks_config = load_blocks_config()
        return [
            raw_block
            for raw_block in blocks_config.get('blocks', [])
            if isinstance(raw_block, dict)
        ]

    def _refresh_block_cache(
        self,
        block_items: list[dict[str, Any]] | None = None,
    ) -> None:
        if block_items is None:
            block_items = self._load_block_items()

        if self._cached_block_items == block_items:
            return

        blocks: list[BaseBlock] = []
        blocks_by_id: dict[str, BaseBlock] = {}

        for raw_block in block_items:
            block = BlockFactory.create_block(raw_block, self.ros_interface)
            blocks.append(block)

            if block.id:
                blocks_by_id[block.id] = block

        self._cached_block_items = deepcopy(block_items)
        self._cached_blocks = blocks
        self._cached_blocks_by_id = blocks_by_id

    def _get_blocks(self) -> list[BaseBlock]:
        self._refresh_block_cache()
        return self._cached_blocks

    def _get_blocks_by_id(self) -> dict[str, BaseBlock]:
        self._refresh_block_cache()
        return self._cached_blocks_by_id

    def _get_block_or_raise(self, block_id: str) -> BaseBlock:
        normalized_id = self._normalize_block_id(block_id)
        block = self._get_blocks_by_id().get(normalized_id)

        if block is None:
            raise KeyError(f'Block not found: {normalized_id}')

        return block

    def get_flowchart(self) -> dict[str, Any]:
        blocks_config = load_blocks_config()
        print('Loaded blocks config:')
        block_items = [
            raw_block
            for raw_block in blocks_config.get('blocks', [])
            if isinstance(raw_block, dict)
        ]

        self._refresh_block_cache(block_items)

        logger.info('Loaded blocks config: %s', len(block_items))

        return {
            'config': load_dashboard_config(),
            'blocks': [block.to_dict() for block in self._cached_blocks],
            'connections': blocks_config.get('connections', []),
            'layout': load_layout(),
        }

    def get_block(self, block_id: str) -> dict[str, Any]:
        return self._get_block_or_raise(block_id).to_dict()

    def get_block_state(self, block_id: str) -> dict[str, Any]:
        block = self._get_block_or_raise(block_id)

        status_detail = block.get_status()
        status = status_detail.get('state', 'placeholder')

        return {
            'id': block.id,
            'status': status,
            'status_detail': status_detail,
            'data': block.get_data(),
            'controls': block.get_controls(),
            'last_update': self._timestamp(),
        }

    def get_block_data(self, block_id: str) -> dict[str, Any]:
        return self._get_block_or_raise(block_id).get_data()

    def send_command(self, block_id: str, command: dict[str, Any]) -> dict[str, Any]:
        return self._get_block_or_raise(block_id).send_command(command)

    def get_block_logs(self, block_id: str) -> dict[str, Any]:
        return self._get_block_or_raise(block_id).get_logs()

    def save_layout(self, layout_data: dict[str, Any]) -> dict[str, Any]:
        return save_layout(layout_data)
