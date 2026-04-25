from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from .runtime import node_manager as manager

router = APIRouter(prefix='/api', tags=['nodes'])


def _not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error).strip("'"))


def _bad_request(error: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(error))


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
        raise _not_found(error) from error
    except ValueError as error:
        raise _bad_request(error) from error


@router.post('/nodes/{node_name:path}/start')
def start_node(node_name: str) -> dict[str, Any]:
    try:
        return manager.start_node(node_name)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _bad_request(error) from error


@router.post('/nodes/{node_name:path}/stop')
def stop_node(node_name: str) -> dict[str, Any]:
    try:
        return manager.stop_node(node_name)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _bad_request(error) from error
