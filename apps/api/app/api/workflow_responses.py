from typing import NoReturn

from fastapi import HTTPException, status

from app.services.workflow_errors import WorkflowConflictError, WorkflowNotFoundError


def raise_workflow_http_error(error: Exception) -> NoReturn:
    if isinstance(error, WorkflowNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, WorkflowConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    raise error
