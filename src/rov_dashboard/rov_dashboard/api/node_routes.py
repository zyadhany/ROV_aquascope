from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from .errors import bad_request, not_found
from .runtime import node_manager as manager

router = APIRouter(prefix='/api', tags=['nodes'])


@router.get('/nodes')
def list_nodes() -> dict[str, Any]:
    return {
        'nodes': manager.list_nodes(),
    }


@router.get('/nodes/{node_name:path}/status')
def get_node_status(node_name: str) -> dict[str, Any]:
    try:
        return manager.get_status(node_name)
    except KeyError as error:
        raise not_found(error) from error
    except ValueError as error:
        raise bad_request(error) from error


@router.post('/nodes/{node_name:path}/start')
def start_node(node_name: str) -> dict[str, Any]:
    try:
        return manager.start_node(node_name)
    except KeyError as error:
        raise not_found(error) from error
    except ValueError as error:
        raise bad_request(error) from error


@router.post('/nodes/{node_name:path}/stop')
def stop_node(node_name: str) -> dict[str, Any]:
    try:
        return manager.stop_node(node_name)
    except KeyError as error:
        raise not_found(error) from error
    except ValueError as error:
        raise bad_request(error) from error


@router.get('/nodes/{node_name:path}/logs')
def get_node_logs(
    node_name: str,
    limit: int | None = Query(default=None, ge=1, le=1000),
) -> dict[str, Any]:
    try:
        return manager.get_logs(node_name, limit=limit)
    except KeyError as error:
        raise not_found(error) from error
    except ValueError as error:
        raise bad_request(error) from error
