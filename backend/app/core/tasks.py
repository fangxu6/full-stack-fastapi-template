from app.core.celery import celery_app


def runtime_ping(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("runtime.ping value must be a string")
    if len(value) > 64:
        raise ValueError("runtime.ping value must be 64 characters or fewer")
    return value


celery_app.task(name="runtime.ping")(runtime_ping)
