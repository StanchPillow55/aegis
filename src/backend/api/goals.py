from fastapi import APIRouter, HTTPException, Header
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from src.backend.models.goals import Goal, GoalStatus, GoalCheckIn, CompletionConfirmedBy
from src.backend.intelligence.goal_tracker import (
    get_all_goals,
    get_goal,
    save_goal,
    get_pending_check_ins,
    delete_pending_check_in
)

router = APIRouter(prefix="/api/goals", tags=["goals"])

@router.get("", response_model=List[Goal])
def list_goals(
    status: Optional[GoalStatus] = None,
    x_user_id: str = Header(default="default_user")
):
    return get_all_goals(x_user_id, status)

@router.post("", response_model=Goal)
def create_goal(
    goal: Goal,
    x_user_id: str = Header(default="default_user")
):
    goal.id = str(uuid.uuid4())
    goal.created_at = datetime.now(timezone.utc)
    if goal.status is None:
        goal.status = GoalStatus.active
    save_goal(goal, x_user_id)
    return goal

@router.post("/{goal_id}/complete")
def complete_goal_manually(
    goal_id: str,
    x_user_id: str = Header(default="default_user")
):
    g = get_goal(goal_id, x_user_id)
    if not g:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    g.status = GoalStatus.completed
    g.completed_at = datetime.now(timezone.utc)
    g.completion_confirmed_by = CompletionConfirmedBy.user
    g.progress_pct = 100.0
    save_goal(g, x_user_id)
    return g

@router.get("/pending-confirmations", response_model=List[GoalCheckIn])
def get_pending_confirmations(
    x_user_id: str = Header(default="default_user")
):
    return get_pending_check_ins(x_user_id)

@router.post("/{goal_id}/confirm-completion")
def confirm_ai_completion(
    goal_id: str,
    x_user_id: str = Header(default="default_user")
):
    g = get_goal(goal_id, x_user_id)
    if not g:
        raise HTTPException(status_code=404, detail="Goal not found")
        
    g.status = GoalStatus.completed
    g.completed_at = datetime.now(timezone.utc)
    g.completion_confirmed_by = CompletionConfirmedBy.ai_suggested
    g.progress_pct = 100.0
    save_goal(g, x_user_id)
    
    # Remove from pending check-ins
    delete_pending_check_in(goal_id)
    return g

@router.post("/{goal_id}/reject-completion")
def reject_ai_completion(
    goal_id: str,
    x_user_id: str = Header(default="default_user")
):
    delete_pending_check_in(goal_id)
    return {"status": "success"}
