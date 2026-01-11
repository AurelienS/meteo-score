"""Sites API endpoints for MétéoScore.

Provides read operations for weather observation sites.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models import Site
from core.schemas import MetaResponse, PaginatedResponse, SiteResponse

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("/", response_model=PaginatedResponse[SiteResponse])
async def get_sites(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(default=100, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[SiteResponse]:
    """Get all sites with pagination.

    Args:
        page: Page number (1-indexed).
        per_page: Number of items per page (max 100).
        db: Database session (injected).

    Returns:
        Paginated list of sites.
    """
    # Limit per_page to prevent abuse
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Get total count
    count_result = await db.execute(select(func.count()).select_from(Site))
    total = count_result.scalar() or 0

    # Get paginated sites
    result = await db.execute(
        select(Site).order_by(Site.id).offset(offset).limit(per_page)
    )
    sites = result.scalars().all()

    return PaginatedResponse[SiteResponse](
        data=[SiteResponse.model_validate(site) for site in sites],
        meta=MetaResponse(total=total, page=page, per_page=per_page),
    )


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
) -> SiteResponse:
    """Get a specific site by ID.

    Args:
        site_id: Site identifier.
        db: Database session (injected).

    Returns:
        Site details.

    Raises:
        HTTPException: If site not found.
    """
    result = await db.execute(select(Site).where(Site.id == site_id))
    site = result.scalar_one_or_none()

    if site is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")

    return SiteResponse.model_validate(site)
