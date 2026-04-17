from datasette import Forbidden
from datasette_plugin_router import Router
from functools import wraps

router = Router(title="datasette-comments", version="0.2.0")

PERMISSION_ACCESS_NAME = "datasette-comments-access"
PERMISSION_READONLY_NAME = "datasette-comments-readonly"


def check_permission(write=False):
    """Decorator for router handlers to enforce permission checks."""

    def decorator(func):
        @wraps(func)
        async def wrapper(**kwargs):
            datasette = kwargs.get("datasette")
            request = kwargs.get("request")
            if write:
                result = await datasette.allowed(
                    action=PERMISSION_ACCESS_NAME, actor=request.actor
                )
            else:
                result = await datasette.allowed(
                    action=PERMISSION_ACCESS_NAME, actor=request.actor
                ) or await datasette.allowed(
                    action=PERMISSION_READONLY_NAME, actor=request.actor
                )
            if not result:
                raise Forbidden("Permission denied for datasette-comments")
            return await func(**kwargs)

        # Preserve the original function's signature for the router's introspection
        import inspect

        wrapper.__signature__ = inspect.signature(func)
        wrapper.__annotations__ = func.__annotations__

        return wrapper

    return decorator
