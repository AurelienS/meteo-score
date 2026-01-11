"""Parameters API endpoints for MétéoScore.

Provides read operations for weather parameters.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import Parameter
from core.schemas import MetaResponse, PaginatedResponse, ParameterResponse

router = APIRouter(prefix="/parameters", tags=["parameters"])


@router.get("/", response_model=PaginatedResponse[ParameterResponse])
async def get_parameters(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(default=100, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ParameterResponse]:
    """Get all weather parameters with pagination.

    Args:
        page: Page number (1-indexed).
        per_page: Number of items per page (max 100).
        db: Database session (injected).

    Returns:
        Paginated list of weather parameters.
    """
    # Limit per_page to prevent abuse
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Get total count
    count_result = await db.execute(select(func.count()).select_from(Parameter))
    total = count_result.scalar() or 0

    # Get paginated parameters
    result = await db.execute(
        select(Parameter).order_by(Parameter.id).offset(offset).limit(per_page)
    )
    parameters = result.scalars().all()

    return PaginatedResponse[ParameterResponse](
        data=[ParameterResponse.model_validate(param) for param in parameters],
        meta=MetaResponse(total=total, page=page, per_page=per_page),
    )


@router.get("/{parameter_id}", response_model=ParameterResponse)
async def get_parameter(
    parameter_id: int,
    db: AsyncSession = Depends(get_db),
) -> ParameterResponse:
    """Get a specific weather parameter by ID.

    Args:
        parameter_id: Parameter identifier.
        db: Database session (injected).

    Returns:
        Parameter details.

    Raises:
        HTTPException: If parameter not found.
    """
    result = await db.execute(select(Parameter).where(Parameter.id == parameter_id))
    parameter = result.scalar_one_or_none()

    if parameter is None:
        raise HTTPException(
            status_code=404, detail=f"Parameter {parameter_id} not found"
        )

    return ParameterResponse.model_validate(parameter)
