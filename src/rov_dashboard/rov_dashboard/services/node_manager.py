from __future__ import annotations
from ..core.node_handler import NodeHandler

from copy import deepcopy
from datetime import datetime, timezone
import os
import shlex
import subprocess
from typing import Any

from .process_registry import ProcessRegistry
from ..core.ros_interface import RosInterface
from ..flowchart.block_manager import BlockManager


class NodeManager:
    """Manage dashboard-started ROS processes from configured node entries."""

    def __init__(
        self,
        ros_interface: RosInterface | None = None,
        block_manager: BlockManager | None = None,
    ) -> None:
        self.ros_interface = ros_interface or RosInterface()
        self.block_manager = block_manager or BlockManager(self.ros_interface)
        self._node_handler = NodeHandler()
        self._processes = ProcessRegistry(
            self._popen,
            lambda pid, sig: os.killpg(pid, sig),
            subprocess.TimeoutExpired,
        )
        self._entry_cache_version = -1
        self._entry_cache: dict[str, dict[str, Any]] = {}

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _normalize_node_ref(self, node_name: str) -> str:
        clean_name = str(node_name).strip()
        if not clean_name:
            raise ValueError('Node name cannot be empty.')
        return clean_name.lstrip('/')

    def _node_entries(self) -> dict[str, dict[str, Any]]:
        config_version = getattr(self.block_manager, 'config_version', 0)
        if self._entry_cache_version == config_version:
            return self._entry_cache

        entries: dict[str, dict[str, Any]] = {}
        for block in self.block_manager.list_node_blocks():
            block_config = block.to_dict()
            block_id = str(block_config.get('id', '')).strip()
            node_name = str(block_config.get('ros_node', block_id)).strip()
            if not block_id or not node_name:
                continue

            aliases = block_config.get('aliases', [])
            if not isinstance(aliases, list):
                aliases = []
            block_copy = deepcopy(block_config)
            block_copy.update({
                'id': block_id,
                'block_id': block_id,
                'node_name': node_name,
                'package': str(block_config.get('package', '')).strip(),
                'executable': str(
                    block_config.get('executable') or node_name.lstrip('/'),
                ).strip(),
                'aliases': [str(alias).strip() for alias in aliases],
            })
            block_copy['start_command'] = self._start_command(block_copy)
            block_copy['_refs'] = self._node_refs(block_copy)
            entries[block_id.lstrip('/')] = block_copy

        self._entry_cache = entries
        self._entry_cache_version = config_version
        return entries

    def _start_command(self, node_config: dict[str, Any]) -> str:
        configured_command = str(node_config.get('start_command', '')).strip()
        if configured_command:
            return configured_command

        package = str(node_config.get('package', '')).strip()
        executable = str(node_config.get('executable', '')).strip()
        if not package or not executable:
            return ''

        return f'ros2 run {package} {executable}'

    def _popen(self, command: list[str]) -> subprocess.Popen[Any]:
        return subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=os.environ.copy(),
        )

    def _node_refs(self, entry: dict[str, Any]) -> set[str]:
        refs = {
            entry['id'].lstrip('/'),
            entry['id'].rstrip('/').split('/')[-1],
            entry.get('block_id', '').lstrip('/'),
            entry.get('block_id', '').rstrip('/').split('/')[-1],
            str(entry.get('node_name', '')).lstrip('/'),
        }
        refs.update(alias.lstrip('/') for alias in entry.get('aliases', []))
        return {ref for ref in refs if ref}

    def _find_node_config(self, node_name: str) -> dict[str, Any]:
        normalized = self._normalize_node_ref(node_name)
        for entry in self._node_entries().values():
            if normalized in entry['_refs']:
                return entry

        raise KeyError(f'Node not found: {node_name}')

    def _graph_running(self, node_name: str) -> bool:
        node_info = self.ros_interface.get_node_info(node_name)
        return node_info.get('status') == 'active'

    def _status_payload(self, node_config: dict[str, Any]) -> dict[str, Any]:
        tracked_process = self._processes.running(node_config['id'])
        tracked_running = tracked_process is not None
        graph_running = self._graph_running(node_config['node_name'])
        running = tracked_running or graph_running

        return {
            'node': node_config['node_name'].lstrip('/'),
            'node_name': node_config['node_name'],
            'block_id': node_config['block_id'],
            'service_id': node_config['id'],
            'package': node_config.get('package', ''),
            'executable': node_config.get('executable', ''),
            'start_command': node_config.get('start_command', ''),
            'running': running,
            'status': 'running' if running else 'stopped',
            'tracked': tracked_running,
            'ros_graph_running': graph_running,
            'last_update': self._timestamp(),
        }

    def list_nodes(self) -> list[dict[str, Any]]:
        return [
            self._status_payload(node_config)
            for node_config in self._node_entries().values()
        ]

    def get_status(self, node_name: str) -> dict[str, Any]:
        return self._status_payload(self._find_node_config(node_name))

    def start_node(self, node_name: str) -> dict[str, Any]:
        node_config = self._find_node_config(node_name)

        result = self._node_handler.start_node_from_config(node_config)

        status = self._status_payload(node_config)

        return {
            **status,
            "success": result.success,
            "message": result.message,
            "pid": result.pid,
            "package": result.package,
            "executable": result.executable,
        }

    def stop_node(self, node_name: str) -> dict[str, Any]:
        node_config = self._find_node_config(node_name)

        result = self._node_handler.stop_node_from_config(node_config)

        status = self._status_payload(node_config)

        return {
            **status,
            "success": result.success,
            "message": result.message,
            "pids": result.pids,
            "force_killed_pids": result.force_killed_pids,
        }

    def get_logs(self, node_name: str, limit: int | None = None) -> dict[str, Any]:
        node_config = self._find_node_config(node_name)
        block = self.block_manager.get_block(node_config['block_id'])
        logs = block.get_logs(limit=limit)
        logs['node_name'] = node_config['node_name']
        logs['block_id'] = node_config['block_id']
        return logs

    def shutdown(self) -> None:
        for service_id in self._processes.ids():
            try:
                self.stop_node(service_id)
            except Exception:
                continue
