from __future__ import annotations

from typing import Any

from .base_block import BaseBlock


class NodeBlock(BaseBlock):
    def get_status(self) -> dict[str, Any]:
        node_name = str(self.raw_config.get('ros_node', self.id)).strip()
        node_info = self.ros_interface.get_node_info(node_name)
        state = node_info.get('status', 'unknown')
        return {
            'state': state,
            'message': (
                'ROS node is active.'
                if state == 'active'
                else 'ROS node was not found in the current graph.'
            ),
            'node': node_name,
            'last_update': self._timestamp(),
        }

    def get_data(self) -> dict[str, Any]:
        node_name = str(self.raw_config.get('ros_node', self.id)).strip()
        return self.ros_interface.get_node_info(node_name)

    def get_logs(self, limit: int | None = None) -> dict[str, Any]:
        logs_config = self._dict_config('logs')
        source = str(logs_config.get('source', self.raw_config.get('ros_node', self.id))).strip()
        return self.ros_interface.get_logs(source, limit=limit)
