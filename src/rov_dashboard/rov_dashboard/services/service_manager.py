from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
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
        self._runtime_status: dict[str, str] = {}

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
            service_copy['status'] = self._status_for_service(service_copy)
            services_by_id[service_id] = service_copy
        return services_by_id

    def _status_for_service(self, service: dict[str, Any]) -> str:
        node_name = str(service.get('node_name', '')).strip()
        if node_name:
            try:
                return self.node_manager.get_status(node_name)['status']
            except KeyError:
                pass

        return self._runtime_status.get(
            str(service.get('id', '')).strip(),
            str(service.get('status', 'stopped')),
        )

    def list_services(self) -> list[dict[str, Any]]:
        return list(self._services_by_id().values())

    def get_service(self, service_id: str) -> dict[str, Any]:
        service = self._services_by_id().get(service_id)
        if service is None:
            raise KeyError(f'Service not found: {service_id}')
        return service

    def _set_status(self, service_id: str, status: str, action: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        with self._lock:
            self._runtime_status[service_id] = status
        service['status'] = status

        return {
            'success': True,
            'service': service,
            'action': action,
            'placeholder': True,
            'message': f'Placeholder {action} accepted. No process was started or stopped.',
            'last_update': self._timestamp(),
        }

    def start_service(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        node_name = str(service.get('node_name', '')).strip()
        if node_name:
            return self.node_manager.start_node(node_name)
        return self._set_status(service_id, 'running', 'start')

    def stop_service(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        node_name = str(service.get('node_name', '')).strip()
        if node_name:
            return self.node_manager.stop_node(node_name)
        return self._set_status(service_id, 'stopped', 'stop')

    def restart_service(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        node_name = str(service.get('node_name', '')).strip()
        if node_name:
            stop_result = self.node_manager.stop_node(node_name)
            if not stop_result.get('success', False):
                return stop_result
            return self.node_manager.start_node(node_name)
        return self._set_status(service_id, 'running', 'restart')

    def get_logs(self, service_id: str) -> dict[str, Any]:
        service = self.get_service(service_id)
        logs_config = service.get('logs', {})
        if not isinstance(logs_config, dict):
            logs_config = {}
        source = str(logs_config.get('source', service_id)).strip()
        logs = self.ros_interface.get_logs(source)
        logs['service_id'] = service_id
        return logs
