from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import threading
from typing import Any

from ..core.config_loader import load_services_config
from ..core.ros_interface import RosInterface


class ServiceManager:
    def __init__(self, ros_interface: RosInterface | None = None) -> None:
        self.ros_interface = ros_interface or RosInterface()
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
            service_copy['status'] = self._runtime_status.get(
                service_id,
                str(service_copy.get('status', 'stopped')),
            )
            services_by_id[service_id] = service_copy
        return services_by_id

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
        return self._set_status(service_id, 'running', 'start')

    def stop_service(self, service_id: str) -> dict[str, Any]:
        return self._set_status(service_id, 'stopped', 'stop')

    def restart_service(self, service_id: str) -> dict[str, Any]:
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
