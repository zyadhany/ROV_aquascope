from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from .errors import not_found
from .runtime import service_manager as manager

router = APIRouter(prefix='/api', tags=['services'])


@router.get('/services')
def list_services() -> dict[str, Any]:
    return {
        'services': manager.list_services(),
    }


@router.get('/services/{service_id}')
def get_service(service_id: str) -> dict[str, Any]:
    try:
        return manager.get_service(service_id)
    except KeyError as error:
        raise not_found(error) from error


@router.post('/services/{service_id}/start')
def start_service(service_id: str) -> dict[str, Any]:
    try:
        return manager.start_service(service_id)
    except KeyError as error:
        raise not_found(error) from error


@router.post('/services/{service_id}/stop')
def stop_service(service_id: str) -> dict[str, Any]:
    try:
        return manager.stop_service(service_id)
    except KeyError as error:
        raise not_found(error) from error


@router.post('/services/{service_id}/restart')
def restart_service(service_id: str) -> dict[str, Any]:
    try:
        return manager.restart_service(service_id)
    except KeyError as error:
        raise not_found(error) from error


@router.get('/services/{service_id}/logs')
def get_service_logs(service_id: str) -> dict[str, Any]:
    try:
        return manager.get_logs(service_id)
    except KeyError as error:
        raise not_found(error) from error
