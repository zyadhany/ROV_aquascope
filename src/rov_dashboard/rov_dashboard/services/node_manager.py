from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import os
import shlex
import signal
import subprocess
import threading
from typing import Any

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
        self._lock = threading.RLock()
        self._processes: dict[str, subprocess.Popen[Any]] = {}

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _normalize_node_ref(self, node_name: str) -> str:
        clean_name = str(node_name).strip()
        if not clean_name:
            raise ValueError('Node name cannot be empty.')
        return clean_name.lstrip('/')

    def _node_entries(self) -> dict[str, dict[str, Any]]:
        entries: dict[str, dict[str, Any]] = {}
        for block in self.block_manager.list_node_blocks():
            block_config = block.to_dict()

            block_id = str(block_config.get('id', '')).strip()
            node_name = str(block_config.get('ros_node', block_id)).strip()
            package = str(block_config.get('package', '')).strip()
            executable = str(block_config.get('executable', '')).strip()
            if not executable:
                executable = node_name.lstrip('/')
            aliases = block_config.get('aliases', [])

            if not block_id or not node_name:
                continue

            if not isinstance(aliases, list):
                aliases = []

            block_copy = deepcopy(block_config)
            block_copy['id'] = block_id
            block_copy['block_id'] = block_id
            block_copy['node_name'] = node_name
            block_copy['package'] = package
            block_copy['executable'] = executable
            block_copy['aliases'] = [str(alias).strip() for alias in aliases]
            block_copy['start_command'] = self._start_command(block_copy)
            entries[block_id.lstrip('/')] = block_copy

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

    def _find_node_config(self, node_name: str) -> dict[str, Any]:
        normalized = self._normalize_node_ref(node_name)
        for entry in self._node_entries().values():
            if entry['id'].lstrip('/') == normalized:
                return entry

            if entry['id'].rstrip('/').split('/')[-1] == normalized:
                return entry

            if entry.get('block_id', '').lstrip('/') == normalized:
                return entry

            if entry.get('block_id', '').rstrip('/').split('/')[-1] == normalized:
                return entry

            if str(entry.get('node_name', '')).lstrip('/') == normalized:
                return entry

            aliases = [alias.lstrip('/') for alias in entry.get('aliases', [])]
            if normalized in aliases:
                return entry

        raise KeyError(f'Node not found: {node_name}')

    def _tracked_process(self, service_id: str) -> subprocess.Popen[Any] | None:
        with self._lock:
            process = self._processes.get(service_id)

        if process is None:
            return None

        if process.poll() is None:
            return process

        with self._lock:
            current_process = self._processes.get(service_id)
            if current_process is process:
                self._processes.pop(service_id, None)

        return None

    def _graph_running(self, node_name: str) -> bool:
        node_info = self.ros_interface.get_node_info(node_name)
        return node_info.get('status') == 'active'

    def _status_payload(self, node_config: dict[str, Any]) -> dict[str, Any]:
        tracked_process = self._tracked_process(node_config['id'])
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
        status = self._status_payload(node_config)

        if status['tracked']:
            return {
                **status,
                'success': True,
                'message': 'Node is already running under dashboard control.',
            }

        if status['ros_graph_running']:
            return {
                **status,
                'success': False,
                'message': (
                    'Node appears to already be running outside dashboard control.'
                ),
            }

        command = shlex.split(str(node_config.get('start_command', '')).strip())
        if not command:
            return {
                **status,
                'success': False,
                'message': 'No start command configured for this node.',
            }

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=os.environ.copy(),
            )
        except Exception as exc:
            return {
                **status,
                'success': False,
                'message': f'Failed to start node: {exc}',
            }

        with self._lock:
            self._processes[node_config['id']] = process

        updated_status = self._status_payload(node_config)
        return {
            **updated_status,
            'success': True,
            'message': 'Node started.',
        }

    def stop_node(self, node_name: str) -> dict[str, Any]:
        node_config = self._find_node_config(node_name)
        process = self._tracked_process(node_config['id'])

        if process is None:
            status = self._status_payload(node_config)
            return {
                **status,
                'success': True,
                'message': 'Node is not running under dashboard control.',
            }

        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
        except ProcessLookupError:
            pass
        finally:
            with self._lock:
                self._processes.pop(node_config['id'], None)

        status = self._status_payload(node_config)
        return {
            **status,
            'success': True,
            'message': 'Node stopped.',
        }

    def get_logs(self, node_name: str, limit: int | None = None) -> dict[str, Any]:
        node_config = self._find_node_config(node_name)
        block = self.block_manager.get_block(node_config['block_id'])
        logs = block.get_logs(limit=limit)
        logs['node_name'] = node_config['node_name']
        logs['block_id'] = node_config['block_id']
        return logs

    def shutdown(self) -> None:
        with self._lock:
            service_ids = list(self._processes.keys())

        for service_id in service_ids:
            try:
                self.stop_node(service_id)
            except Exception:
                continue
