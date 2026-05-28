from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.loan import (
    LoanCreate,
    LoanResponse,
    RepaymentCreate,
    RepaymentResponse,
)
from app.services.loan_service import (
    confirm_loan,
    create_loan,
    create_repayment,
    get_loan_by_id,
    get_repayment_history,
    get_user_loans,
    mark_loan_as_paid,
    reject_loan,
)

router = APIRouter(
    prefix="/loans",
    tags=["loans"],
)


@router.post(
    "",
    response_model=LoanResponse,
)
async def create_new_loan(
    loan_data: LoanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_loan(
        db=db,
        loan_data=loan_data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[LoanResponse],
)
async def get_loans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_user_loans(
        db=db,
        current_user=current_user,
    )


@router.get(
    "/{loan_id}",
    response_model=LoanResponse,
)
async def get_loan(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loan = await get_loan_by_id(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )

    if loan is None:
        raise HTTPException(
            status_code=404,
            detail="Loan not found",
        )

    return loan


@router.post(
    "/{loan_id}/confirm",
    response_model=LoanResponse,
)
async def confirm_existing_loan(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await confirm_loan(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )


@router.post(
    "/{loan_id}/reject",
    response_model=LoanResponse,
)
async def reject_existing_loan(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await reject_loan(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )


@router.post(
    "/{loan_id}/mark-paid",
    response_model=LoanResponse,
)
async def mark_paid_existing_loan(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await mark_loan_as_paid(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )


@router.post(
    "/{loan_id}/repay",
    response_model=LoanResponse,
)
async def repay_loan(
    loan_id: int,
    repayment_data: RepaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_repayment(
        db=db,
        loan_id=loan_id,
        repayment_data=repayment_data,
        current_user=current_user,
    )


@router.get(
    "/{loan_id}/repayments",
    response_model=list[RepaymentResponse],
)
async def get_loan_repayments(
    loan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_repayment_history(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )