from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select
from .database import get_session
from .models import OnboardingProgress


async def start_onboarding(tenant_id: str, role: str) -> Dict[str, Any]:
    async with get_session() as session:
        stmt = select(OnboardingProgress).where(
            OnboardingProgress.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.current_phase = 1
            existing.role_selection = role
            existing.first_platform_connected = False
            existing.first_post_published = False
            existing.completed_at = None
            existing.skipped = False
            existing.updated_at = datetime.utcnow()
        else:
            progress = OnboardingProgress(
                tenant_id=tenant_id,
                current_phase=1,
                role_selection=role,
                first_platform_connected=False,
                first_post_published=False,
                skipped=False,
            )
            session.add(progress)

        await session.commit()

        return {
            "tenant_id": tenant_id,
            "current_phase": 1,
            "role": role,
            "completed": False,
            "skipped": False,
        }


async def get_onboarding_status(tenant_id: str) -> Optional[Dict[str, Any]]:
    async with get_session() as session:
        stmt = select(OnboardingProgress).where(
            OnboardingProgress.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()

        if not progress:
            return None

        return {
            "tenant_id": tenant_id,
            "current_phase": progress.current_phase,
            "role": progress.role_selection,
            "first_platform_connected": progress.first_platform_connected,
            "first_post_published": progress.first_post_published,
            "completed": progress.completed_at is not None,
            "completed_at": progress.completed_at.isoformat()
            if progress.completed_at
            else None,
            "skipped": progress.skipped,
            "created_at": progress.created_at.isoformat()
            if progress.created_at
            else None,
            "updated_at": progress.updated_at.isoformat()
            if progress.updated_at
            else None,
        }


async def complete_phase(tenant_id: str, phase: int) -> Dict[str, Any]:
    async with get_session() as session:
        stmt = select(OnboardingProgress).where(
            OnboardingProgress.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()

        if not progress:
            raise ValueError(f"No onboarding found for tenant {tenant_id}")

        if progress.skipped:
            raise ValueError("Cannot complete phase for skipped onboarding")

        if phase == 1:
            progress.current_phase = 2
        elif phase == 2:
            progress.first_platform_connected = True
            progress.current_phase = 3
        elif phase == 3:
            progress.first_post_published = True
            progress.completed_at = datetime.utcnow()
        else:
            raise ValueError(f"Invalid phase number: {phase}")

        progress.updated_at = datetime.utcnow()
        await session.commit()

        return {
            "tenant_id": tenant_id,
            "current_phase": progress.current_phase,
            "role": progress.role_selection,
            "first_platform_connected": progress.first_platform_connected,
            "first_post_published": progress.first_post_published,
            "completed": progress.completed_at is not None,
            "completed_at": progress.completed_at.isoformat()
            if progress.completed_at
            else None,
            "skipped": False,
        }


async def skip_onboarding(tenant_id: str) -> Dict[str, Any]:
    async with get_session() as session:
        stmt = select(OnboardingProgress).where(
            OnboardingProgress.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()

        if not progress:
            raise ValueError(f"No onboarding found for tenant {tenant_id}")

        progress.skipped = True
        progress.updated_at = datetime.utcnow()
        await session.commit()

        return {
            "tenant_id": tenant_id,
            "current_phase": progress.current_phase,
            "role": progress.role_selection,
            "completed": False,
            "skipped": True,
        }


async def get_onboarding_status(tenant_id: str) -> Optional[Dict[str, Any]]:
    """
    Get current onboarding status for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Dict with onboarding status or None if not started
    """
    async with get_session() as session:
        stmt = select(OnboardingProgress).where(
            OnboardingProgress.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()

        if not progress:
            return None

        return {
            "tenant_id": tenant_id,
            "current_phase": progress.current_phase,
            "role": progress.role_selection,
            "first_platform_connected": progress.first_platform_connected,
            "first_post_published": progress.first_post_published,
            "completed": progress.completed_at is not None,
            "completed_at": progress.completed_at.isoformat()
            if progress.completed_at
            else None,
            "skipped": progress.skipped,
            "created_at": progress.created_at.isoformat()
            if progress.created_at
            else None,
            "updated_at": progress.updated_at.isoformat()
            if progress.updated_at
            else None,
        }


async def complete_phase(tenant_id: str, phase: int) -> Dict[str, Any]:
    """
    Mark a phase as complete and advance to next phase.

    Args:
        tenant_id: Tenant identifier
        phase: Phase number to complete (1, 2, or 3)

    Returns:
        Dict with updated onboarding status
    """
    async with get_session() as session:
        stmt = select(OnboardingProgress).where(
            OnboardingProgress.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()

        if not progress:
            raise ValueError(f"No onboarding found for tenant {tenant_id}")

        if progress.skipped:
            raise ValueError("Cannot complete phase for skipped onboarding")

        # Update phase-specific flags
        if phase == 1:
            # Role selection complete, move to phase 2
            progress.current_phase = 2
        elif phase == 2:
            # Platform connected
            progress.first_platform_connected = True
            progress.current_phase = 3
        elif phase == 3:
            # First post published - onboarding complete
            progress.first_post_published = True
            progress.completed_at = datetime.utcnow()
        else:
            raise ValueError(f"Invalid phase number: {phase}")

        progress.updated_at = datetime.utcnow()
        await session.commit()

        return {
            "tenant_id": tenant_id,
            "current_phase": progress.current_phase,
            "role": progress.role_selection,
            "first_platform_connected": progress.first_platform_connected,
            "first_post_published": progress.first_post_published,
            "completed": progress.completed_at is not None,
            "completed_at": progress.completed_at.isoformat()
            if progress.completed_at
            else None,
            "skipped": False,
        }


async def skip_onboarding(tenant_id: str) -> Dict[str, Any]:
    """
    Mark onboarding as skipped for a tenant.

    Args:
        tenant_id: Tenant identifier

    Returns:
        Dict with updated onboarding status
    """
    async with get_session() as session:
        stmt = select(OnboardingProgress).where(
            OnboardingProgress.tenant_id == tenant_id
        )
        result = await session.execute(stmt)
        progress = result.scalar_one_or_none()

        if not progress:
            raise ValueError(f"No onboarding found for tenant {tenant_id}")

        progress.skipped = True
        progress.updated_at = datetime.utcnow()
        await session.commit()

        return {
            "tenant_id": tenant_id,
            "current_phase": progress.current_phase,
            "role": progress.role_selection,
            "completed": False,
            "skipped": True,
        }
