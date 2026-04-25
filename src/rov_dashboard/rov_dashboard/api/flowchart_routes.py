from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from .runtime import flowchart_manager as manager

router = APIRouter(prefix='/api', tags=['flowchart'])


@router.get('/flowchart')
def get_flowchart() -> dict[str, Any]:
    return manager.get_flowchart()


@router.post('/layout')
def save_layout(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        saved_layout = manager.save_layout(payload)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=f'Failed to save layout: {error}',
        ) from error

    return {
        'message': 'Layout saved',
        'layout': saved_layout,
    }
