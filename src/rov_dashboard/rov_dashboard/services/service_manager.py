from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import os
import shlex
import signal
import subprocess
import threading
from typing import Any

from .node_manager import NodeManager
from ..core.config_loader import load_services_config
from ..core.ros_interface import RosInterface


class ServiceManager:
    def __init__(
        self,
        ros_interface: RosInterface | None = None,
        node_manager: NodeManager | None = None,
    ) -> None:
        self.ros_interface = ros_interface or RosInterface()
        self.node_manager = node_manager or NodeManager(self.ros_interface)
        self._lock = threading.Lock()
        self._processes: dict[str, subprocess.Popen[Any]] = {}

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _services_by_id(self) -> dict[str, dict[str, Any]]:
        services_by_id: dict[str, dict[str, Any]] = {}
        for service in load_services_config().get('services', []):
            if not isinstance(service, dict):
                continue
            service_id = str(service.get('id', '')).strip()
            if not service_id:
                continue
            service_copy = deepcopy(service)
            service_copy.update(self._runtime_info_for_service(service_copy))
            services_by_id[service_id] = service_copy
        return services_by_id

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

    def _runtime_info_for_service(self, service: dict[str, Any]) -> dict[str, Any]:
        service_id = str(service.get('id', '')).strip()
        node_name = str(service.get('node_name', '')).strip()
        start_command = str(service.get('start_command', '')).strip()
        stop_method = str(service.get('stop_method', '')).strip()

        if node_name:
            try:
                node_status = self.node_manager.get_status(node_name)
                return {
                    'status': node_status['status'],
                    'running': node_status['running'],
                    'tracked': node_status['tracked'],
                    'ros_graph_running': node_status['ros_graph_running'],
                    'controllable': bool(start_command),
                    'control_mode': 'ros_node',
                    'last_update': self._timestamp(),
                }
            except KeyError:
                return {
                    'status': 'misconfigured',
                    'running': False,
                    'tracked': False,
                    'ros_graph_running': False,
                    'controllable': False,
                    'control_mode': 'ros_node',
                    'message': f'Configured node was not found: {node_name}',
                    'last_update': self._timestamp(),
                }

        tracked_process = self._tracked_process(service_id)
        tracked_running = tracked_process is not None
        controllable = bool(start_command) and stop_method != 'manual'

        return {
            'status': 'running' if tracked_running else str(service.get('status', 'stopped')),
            'running': tracked_running or str(service.get('status', '')) == 'running',
            'tracked': tracked_running,
            'ros_graph_running': False,
            'controllable': controllable,
            'control_mode': 'process' if controllable else 'manual',
            'last_update': self._timestamp(),
        }

    def list_services(self) -> list[dict[str, Any]]:
        return list(self._services_by_id().values())

    def get_service(self, service_id: str) -> dict[str, Any]:
        service = self._services_by_id().get(service_id)
        if service is None:
            raise KeyError(f'Service not found: {service_id}')
        return service

    def _manual_service_response(self, service_id: str, action: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        return {
            'success': False,
            'service': service,
            'action': action,
            'message': 'Service is configured for manual control.',
            'last_update': self._timestamp(),
        }

    def start_service(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        node_name = str(service.get('node_name', '')).strip()
        if node_name:
            return self.node_manager.start_node(node_name)

        if not service.get('controllable', False):
            return self._manual_service_response(service_id, 'start')

        if self._tracked_process(service_id) is not None:
            return {
                'success': True,
                'service': self.get_service(service_id),
                'action': 'start',
                'message': 'Service is already running under dashboard control.',
                'last_update': self._timestamp(),
            }

        command = shlex.split(str(service.get('start_command', '')).strip())
        if not command:
            return {
                'success': False,
                'service': service,
                'action': 'start',
                'message': 'No start command configured for this service.',
                'last_update': self._timestamp(),
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
                'success': False,
                'service': service,
                'action': 'start',
                'message': f'Failed to start service: {exc}',
                'last_update': self._timestamp(),
            }

        with self._lock:
            self._processes[service_id] = process

        return {
            'success': True,
            'service': self.get_service(service_id),
            'action': 'start',
            'message': 'Service started.',
            'last_update': self._timestamp(),
        }

    def stop_service(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        node_name = str(service.get('node_name', '')).strip()
        if node_name:
            return self.node_manager.stop_node(node_name)

        if not service.get('controllable', False):
            return self._manual_service_response(service_id, 'stop')

        process = self._tracked_process(service_id)
        if process is None:
            return {
                'success': True,
                'service': self.get_service(service_id),
                'action': 'stop',
                'message': 'Service is not running under dashboard control.',
                'last_update': self._timestamp(),
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
                self._processes.pop(service_id, None)

        return {
            'success': True,
            'service': self.get_service(service_id),
            'action': 'stop',
            'message': 'Service stopped.',
            'last_update': self._timestamp(),
        }

    def restart_service(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        node_name = str(service.get('node_name', '')).strip()
        if node_name:
            stop_result = self.node_manager.stop_node(node_name)
            if not stop_result.get('success', False):
                return stop_result
            return self.node_manager.start_node(node_name)

        stop_result = self.stop_service(service_id)
        if not stop_result.get('success', False):
            return stop_result

        start_result = self.start_service(service_id)
        start_result['action'] = 'restart'
        return start_result

    def get_logs(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        logs_config = service.get('logs', {})
        if not isinstance(logs_config, dict):
            logs_config = {}
        source = str(logs_config.get('source', service_id)).strip()
        logs = self.ros_interface.get_logs(source)
        logs['service_id'] = service_id
        return logs
