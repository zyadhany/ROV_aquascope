from __future__ import annotations

from copy import deepcopy
from typing import Any

from .block_factory import BlockFactory
from ..blocks.base_block import BaseBlock
from ..core.config_loader import load_blocks_config, load_dashboard_settings
from ..core.ros_interface import RosInterface


class BlockManager:
    """Own loaded block objects and connection data for the dashboard runtime."""

    def __init__(self, ros_interface: RosInterface | None = None) -> None:
        self.ros_interface = ros_interface or RosInterface()
        self._blocks: list[BaseBlock] = []
        self._blocks_by_id: dict[str, BaseBlock] = {}
        self._connections: list[dict[str, Any]] = []
        self.config_version = 0
        self._settings = load_dashboard_settings()
        self.load_from_config()
        self.ros_interface.set_rosout_log_handler(self.route_rosout_log)

    def _normalize_block_id(self, block_id: str) -> str:
        block_id = str(block_id).strip()
        if not block_id:
            raise ValueError('Block ID cannot be empty')
        return block_id if block_id.startswith('/') else f'/{block_id}'

    def load_from_config(self) -> None:
        blocks_config = load_blocks_config()
        blocks: list[BaseBlock] = []
        blocks_by_id: dict[str, BaseBlock] = {}

        for raw_block in blocks_config.get('blocks', []):
            if not isinstance(raw_block, dict):
                continue

            block_config = deepcopy(raw_block)
            block_config.setdefault(
                'max_logs_stored',
                self._settings['max_logs_stored'],
            )
            block = BlockFactory.create_block(block_config, self.ros_interface)
            blocks.append(block)
            if block.id:
                blocks_by_id[block.id] = block

        connections = blocks_config.get('connections', [])
        self._blocks = blocks
        self._blocks_by_id = blocks_by_id
        self._connections = [
            deepcopy(connection)
            for connection in connections
            if isinstance(connection, dict)
        ] if isinstance(connections, list) else []
        self.config_version += 1

    def list_blocks(self) -> list[BaseBlock]:
        return list(self._blocks)

    def list_block_ids(self) -> list[str]:
        return [block.id for block in self._blocks if block.id]

    def get_block(self, block_id: str) -> BaseBlock:
        normalized_id = self._normalize_block_id(block_id)
        block = self._blocks_by_id.get(normalized_id)
        if block is None:
            raise KeyError(f'Block not found: {normalized_id}')
        return block

    def get_connections(self) -> list[dict[str, Any]]:
        return deepcopy(self._connections)

    def set_connections(self, connections: list[dict[str, Any]]) -> None:
        self._connections = [
            deepcopy(connection)
            for connection in connections
            if isinstance(connection, dict)
        ]

    def list_node_blocks(self) -> list[BaseBlock]:
        return [
            block for block in self._blocks
            if str(block.type).strip().lower() in {'node', 'nodes'}
        ]

    def route_rosout_log(self, entry: dict[str, Any]) -> None:
        for block in self.list_node_blocks():
            matches_log = getattr(block, 'matches_rosout_log', None)
            add_log = getattr(block, 'add_rosout_log', None)
            if not callable(matches_log) or not callable(add_log):
                continue

            if matches_log(entry):
                add_log(entry)
                return
