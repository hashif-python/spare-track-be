from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.auth.models import User
from app.common.dependencies import get_current_user
from app.common.responses import success_response
from app.dashboard.schemas import DashboardSummaryResponse
from app.dashboard.service import get_dashboard_summary
from app.database import get_db


router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary/")
def dashboard_summary_api(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    summary = DashboardSummaryResponse.model_validate(get_dashboard_summary(db))
    return success_response("Dashboard summary fetched successfully", summary.model_dump(mode="json"))
