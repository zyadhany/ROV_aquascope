from __future__ import annotations

import importlib.util
from typing import Any

from .core.config_loader import get_package_paths


def _missing_runtime_dependencies() -> list[str]:
    missing_dependencies = []

    if importlib.util.find_spec('fastapi') is None:
        missing_dependencies.append('python3-fastapi')

    if importlib.util.find_spec('uvicorn') is None:
        missing_dependencies.append('python3-uvicorn')

    return missing_dependencies


def create_app() -> Any:
    missing_dependencies = _missing_runtime_dependencies()
    if missing_dependencies:
        raise RuntimeError(
            'Missing dashboard backend dependencies: '
            f'{", ".join(missing_dependencies)}. Install them before '
            'running the dashboard backend.'
        )

    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    from .api.block_routes import router as block_router
    from .api.flowchart_routes import router as flowchart_router
    from .api.runtime import ros_interface
    from .api.service_routes import router as service_router

    package_paths = get_package_paths()
    app = FastAPI(title='ROV Dashboard')
    app.include_router(flowchart_router)
    app.include_router(block_router)
    app.include_router(service_router)

    @app.on_event('shutdown')
    def shutdown_ros_interface() -> None:
        ros_interface.shutdown()

    if package_paths.web_directory.exists():
        app.mount(
            '/',
            StaticFiles(directory=package_paths.web_directory, html=True),
            name='web',
        )

    return app


def main() -> None:
    missing_dependencies = _missing_runtime_dependencies()
    if missing_dependencies:
        raise RuntimeError(
            'Missing dashboard backend dependencies: '
            f'{", ".join(missing_dependencies)}. Install them before '
            'running the dashboard backend.'
        )

    import uvicorn

    uvicorn.run(create_app(), host='0.0.0.0', port=8000)


if __name__ == '__main__':
    main()
