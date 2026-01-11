"""Weather Models API endpoints for MétéoScore.

Provides read operations for weather forecast models.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import Model
from core.schemas import MetaResponse, ModelResponse, PaginatedResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/", response_model=PaginatedResponse[ModelResponse])
async def get_models(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(default=100, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ModelResponse]:
    """Get all weather forecast models with pagination.

    Args:
        page: Page number (1-indexed).
        per_page: Number of items per page (max 100).
        db: Database session (injected).

    Returns:
        Paginated list of weather models.
    """
    # Limit per_page to prevent abuse
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Get total count
    count_result = await db.execute(select(func.count()).select_from(Model))
    total = count_result.scalar() or 0

    # Get paginated models
    result = await db.execute(
        select(Model).order_by(Model.id).offset(offset).limit(per_page)
    )
    models = result.scalars().all()

    return PaginatedResponse[ModelResponse](
        data=[ModelResponse.model_validate(model) for model in models],
        meta=MetaResponse(total=total, page=page, per_page=per_page),
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: int,
    db: AsyncSession = Depends(get_db),
) -> ModelResponse:
    """Get a specific weather model by ID.

    Args:
        model_id: Model identifier.
        db: Database session (injected).

    Returns:
        Model details.

    Raises:
        HTTPException: If model not found.
    """
    result = await db.execute(select(Model).where(Model.id == model_id))
    model = result.scalar_one_or_none()

    if model is None:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    return ModelResponse.model_validate(model)
