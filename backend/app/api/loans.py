from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.loan import (
    LoanCreate,
    LoanInterestLedgerResponse,
    LoanResponse,
    RepaymentCreate,
    RepaymentResponse,
)
from app.services.loan_service import (
    confirm_loan,
    confirm_repayment,
    create_loan,
    create_repayment,
    get_interest_ledger_history,
    get_loan_by_id,
    get_repayment_history,
    get_user_loans,
    mark_loan_as_paid,
    reject_loan,
    reject_repayment,
)

router = APIRouter(
    prefix="/loans",
    tags=["loans"],
)


@router.post(
    "",
    response_model=LoanResponse,
)
def create_new_loan(
    loan_data: LoanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_loan(
        db=db,
        loan_data=loan_data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[LoanResponse],
)
def get_loans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_loans(
        db=db,
        current_user=current_user,
    )


@router.get(
    "/{loan_id}",
    response_model=LoanResponse,
)
def get_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loan = get_loan_by_id(
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
def confirm_existing_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return confirm_loan(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )


@router.post(
    "/{loan_id}/reject",
    response_model=LoanResponse,
)
def reject_existing_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return reject_loan(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )


@router.post(
    "/{loan_id}/mark-paid",
    response_model=LoanResponse,
)
def mark_paid_existing_loan(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return mark_loan_as_paid(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )


@router.post(
    "/{loan_id}/repay",
    response_model=LoanResponse,
)
def repay_loan(
    loan_id: int,
    repayment_data: RepaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_repayment(
        db=db,
        loan_id=loan_id,
        repayment_data=repayment_data,
        current_user=current_user,
    )


@router.post(
    "/{loan_id}/repayments/{repayment_id}/confirm",
    response_model=LoanResponse,
)
def confirm_existing_repayment(
    loan_id: int,
    repayment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return confirm_repayment(
        db=db,
        loan_id=loan_id,
        repayment_id=repayment_id,
        current_user=current_user,
    )


@router.post(
    "/{loan_id}/repayments/{repayment_id}/reject",
    response_model=LoanResponse,
)
def reject_existing_repayment(
    loan_id: int,
    repayment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return reject_repayment(
        db=db,
        loan_id=loan_id,
        repayment_id=repayment_id,
        current_user=current_user,
    )


@router.get(
    "/{loan_id}/repayments",
    response_model=list[RepaymentResponse],
)
def get_loan_repayments(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_repayment_history(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )


@router.get(
    "/{loan_id}/interest-ledger",
    response_model=list[LoanInterestLedgerResponse],
)
def get_loan_interest_ledger(
    loan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_interest_ledger_history(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
    )