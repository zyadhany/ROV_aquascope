from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .block_manager import BlockManager
from ..core.config_loader import load_dashboard_config
from ..core.layout_store import load_layout, save_layout
from ..core.ros_interface import RosInterface


class FlowchartManager:
    def __init__(
        self,
        ros_interface: RosInterface | None = None,
        block_manager: BlockManager | None = None,
    ) -> None:
        self.ros_interface = ros_interface or RosInterface()
        self.block_manager = block_manager or BlockManager(self.ros_interface)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_flowchart(self) -> dict[str, Any]:
        return {
            'config': load_dashboard_config(),
            'blocks': [
                block.to_dict()
                for block in self.block_manager.list_blocks()
            ],
            'connections': self.block_manager.get_connections(),
            'layout': load_layout(),
        }

    def get_block(self, block_id: str) -> dict[str, Any]:
        return self.block_manager.get_block(block_id).to_dict()

    def list_block_ids(self) -> list[str]:
        return self.block_manager.list_block_ids()

    def get_block_state(self, block_id: str) -> dict[str, Any]:
        block = self.block_manager.get_block(block_id)

        status_detail = block.get_status()
        status = status_detail.get('state', 'unknown')

        return {
            'id': block.id,
            'status': status,
            'status_detail': status_detail,
            'data': block.get_data(),
            'controls': block.get_controls(),
            'last_update': self._timestamp(),
        }

    def get_block_data(self, block_id: str) -> dict[str, Any]:
        return self.block_manager.get_block(block_id).get_data()

    def send_command(self, block_id: str, command: dict[str, Any]) -> dict[str, Any]:
        return self.block_manager.get_block(block_id).send_command(command)

    def get_block_logs(self, block_id: str, limit: int | None = None) -> dict[str, Any]:
        return self.block_manager.get_block(block_id).get_logs(limit=limit)

    def save_layout(self, layout_data: dict[str, Any]) -> dict[str, Any]:
        return save_layout(layout_data)
