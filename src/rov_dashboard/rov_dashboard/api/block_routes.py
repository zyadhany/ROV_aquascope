from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .runtime import flowchart_manager as manager

router = APIRouter(prefix='/api', tags=['blocks'])


def _not_found(error: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(error).strip("'"))


def _bad_request(error: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(error))


@router.get('/block/{block_id:path}/state')
def get_block_state(block_id: str) -> dict[str, Any]:
    try:
        return manager.get_block_state(block_id)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _bad_request(error) from error


@router.get('/block/{block_id:path}/data')
def get_block_data(block_id: str) -> dict[str, Any]:
    try:
        return manager.get_block_data(block_id)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _bad_request(error) from error


@router.post('/block/{block_id:path}/command')
def send_block_command(
    block_id: str,
    command: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    try:
        return manager.send_command(block_id, command)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _bad_request(error) from error


@router.get('/block/{block_id:path}/logs')
def get_block_logs(block_id: str) -> dict[str, Any]:
    try:
        return manager.get_block_logs(block_id)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _bad_request(error) from error


@router.post('/topic/publish')
def publish_topic(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    topic = str(payload.get('topic', '')).strip()
    message_type = str(payload.get('message_type', '')).strip()

    if not topic:
        raise HTTPException(status_code=400, detail='Missing topic.')
    if not message_type:
        raise HTTPException(status_code=400, detail='Missing message_type.')
    if 'value' not in payload:
        raise HTTPException(status_code=400, detail='Missing value.')
    
    try:
        return manager.ros_interface.publish_command(
            topic,
            message_type,
            payload.get('value'),
        )
    except ValueError as error:
        raise _bad_request(error) from error


@router.get('/block/{block_id:path}')
def get_block(block_id: str) -> dict[str, Any]:
    try:
        return manager.get_block(block_id)
    except KeyError as error:
        raise _not_found(error) from error
    except ValueError as error:
        raise _bad_request(error) from error
