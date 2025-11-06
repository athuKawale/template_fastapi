import time
from typing import Awaitable, Callable

from fastapi import Request, Response
from loguru import logger


async def logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Middleware for logging HTTP requests."""
    start_time = time.time()

    response = await call_next(request)

    process_time = (time.time() - start_time) * 1000

    client_ip = request.client.host if request.client else "unknown"

    logger.bind(
        client_ip=client_ip,
        method=request.method,
        path=request.url.path,
        query_params=str(request.query_params),
        headers=dict(request.headers),
        status_code=response.status_code,
        process_time=f"{process_time:.2f}ms",
    ).info("access")

    return response
