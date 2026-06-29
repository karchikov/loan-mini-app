from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.loan import (
    LoanActivationRequest,
    LoanCreate,
    LoanFundingActivationCodeResponse,
    LoanInterestLedgerResponse,
    LoanResponse,
    RepaymentCreate,
    RepaymentResponse,
)
from app.services.loan_service import (
    activate_loan,
    confirm_loan,
    confirm_repayment,
    create_loan,
    create_repayment,
    get_interest_ledger_history,
    get_loan_by_id,
    get_repayment_history,
    get_user_loans,
    mark_loan_as_paid,
    regenerate_funding_activation_code,
    reject_loan,
    reject_repayment,
)

router = APIRouter(
    prefix="/loans",
    tags=["loans"],
)


def get_request_ip_address(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        first_ip_address = forwarded_for.split(",")[0].strip()

        if first_ip_address:
            return first_ip_address

    real_ip_address = request.headers.get("x-real-ip")

    if real_ip_address:
        return real_ip_address.strip()

    if request.client:
        return request.client.host

    return None


def get_request_user_agent(request: Request) -> str | None:
    user_agent = request.headers.get("user-agent")

    if user_agent:
        return user_agent

    return None


@router.post(
    "",
    response_model=LoanResponse,
)
def create_new_loan(
    loan_data: LoanCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_loan(
        db=db,
        loan_data=loan_data,
        current_user=current_user,
        ip_address=get_request_ip_address(request),
        user_agent=get_request_user_agent(request),
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
    response_model=LoanFundingActivationCodeResponse,
)
def confirm_existing_loan(
    loan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = confirm_loan(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
        ip_address=get_request_ip_address(request),
        user_agent=get_request_user_agent(request),
    )

    return {
        "loan": result.loan,
        "activation_code": result.activation_code,
    }


@router.post(
    "/{loan_id}/activation-code/regenerate",
    response_model=LoanFundingActivationCodeResponse,
)
def regenerate_existing_loan_activation_code(
    loan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = regenerate_funding_activation_code(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
        ip_address=get_request_ip_address(request),
        user_agent=get_request_user_agent(request),
    )

    return {
        "loan": result.loan,
        "activation_code": result.activation_code,
    }


@router.post(
    "/{loan_id}/activate",
    response_model=LoanResponse,
)
def activate_existing_loan(
    loan_id: int,
    activation_data: LoanActivationRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return activate_loan(
        db=db,
        loan_id=loan_id,
        activation_code=activation_data.activation_code,
        current_user=current_user,
        ip_address=get_request_ip_address(request),
        user_agent=get_request_user_agent(request),
    )


@router.post(
    "/{loan_id}/reject",
    response_model=LoanResponse,
)
def reject_existing_loan(
    loan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return reject_loan(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
        ip_address=get_request_ip_address(request),
        user_agent=get_request_user_agent(request),
    )


@router.post(
    "/{loan_id}/mark-paid",
    response_model=LoanResponse,
)
def mark_paid_existing_loan(
    loan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return mark_loan_as_paid(
        db=db,
        loan_id=loan_id,
        current_user=current_user,
        ip_address=get_request_ip_address(request),
        user_agent=get_request_user_agent(request),
    )


@router.post(
    "/{loan_id}/repay",
    response_model=LoanResponse,
)
def repay_loan(
    loan_id: int,
    repayment_data: RepaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_repayment(
        db=db,
        loan_id=loan_id,
        repayment_data=repayment_data,
        current_user=current_user,
        ip_address=get_request_ip_address(request),
        user_agent=get_request_user_agent(request),
    )


@router.post(
    "/{loan_id}/repayments/{repayment_id}/confirm",
    response_model=LoanResponse,
)
def confirm_existing_repayment(
    loan_id: int,
    repayment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return confirm_repayment(
        db=db,
        loan_id=loan_id,
        repayment_id=repayment_id,
        current_user=current_user,
        ip_address=get_request_ip_address(request),
        user_agent=get_request_user_agent(request),
    )


@router.post(
    "/{loan_id}/repayments/{repayment_id}/reject",
    response_model=LoanResponse,
)
def reject_existing_repayment(
    loan_id: int,
    repayment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return reject_repayment(
        db=db,
        loan_id=loan_id,
        repayment_id=repayment_id,
        current_user=current_user,
        ip_address=get_request_ip_address(request),
        user_agent=get_request_user_agent(request),
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