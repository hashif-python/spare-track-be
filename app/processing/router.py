from celery.result import AsyncResult
from fastapi import APIRouter, Depends
from app.auth.models import User
from app.celery_app import celery
from app.common.dependencies import get_current_user
from app.common.responses import success_response


router = APIRouter(prefix="/api/tasks", tags=["Tasks"])


@router.get("/{task_id}/")
def get_task_status_api(task_id: str, current_user: User = Depends(get_current_user)):
    task_result = AsyncResult(task_id, app=celery)
    data = {
        "task_id": task_id,
        "status": task_result.status,
        "ready": task_result.ready(),
        "successful": task_result.successful() if task_result.ready() else False,
        "result": task_result.result if task_result.ready() else None,
    }
    return success_response("Task status fetched successfully", data)
