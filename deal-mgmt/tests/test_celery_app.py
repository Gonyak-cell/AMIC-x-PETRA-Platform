from app.tasks.celery_app import CELERY_TASK_MODULES, celery_app


def test_celery_registers_explicit_task_modules() -> None:
    update_kwargs = celery_app.conf.update.call_args.kwargs

    assert update_kwargs["imports"] == CELERY_TASK_MODULES
    assert "app.tasks.extraction_tasks" in CELERY_TASK_MODULES
    assert "app.tasks.attachment_tasks" in CELERY_TASK_MODULES
