import CreateLoanForm from "../components/CreateLoanForm";
import EmptyState from "../components/EmptyState";
import LoanCard from "../components/LoanCard";
import UserSummaryCard from "../components/UserSummaryCard";

function shouldShowInConfirmationList(loan, user, isAdmin) {
  if (!loan || !user) {
    return false;
  }

  const isBorrower = loan.borrower_id === user.id;
  const isLender = loan.lender_id === user.id;
  const pendingRepaymentsCount = Number(
    loan.pending_repayments_count || 0,
  );

  if (loan.status === "draft") {
    return isAdmin || isLender;
  }

  if (loan.status === "funding_pending") {
    return isAdmin || isBorrower;
  }

  if (loan.status === "waiting_confirmation") {
    return isAdmin || isLender;
  }

  if (pendingRepaymentsCount > 0) {
    return isAdmin || isLender || isBorrower;
  }

  return false;
}

function HomePage({
  summary,
  lenders,
  loans,
  user,
  isAdmin,
  repayments,
  fundingActivationCodes,
  onInviteSent,
  onCreate,
  onLoadRepayments,
  onConfirm,
  onRegenerateActivationCode,
  onActivateLoan,
  onActivateLoanByConfirmation,
  onReject,
  onMarkPaid,
  onRepay,
  onConfirmRepayment,
  onRejectRepayment,
}) {
  const confirmationLoans = loans
    .filter((loan) =>
      shouldShowInConfirmationList(loan, user, isAdmin)
    )
    .sort((a, b) => b.id - a.id);

  return (
    <>
      <UserSummaryCard summary={summary} />

      <CreateLoanForm
        lenders={lenders}
        onCreate={onCreate}
        onInviteSent={onInviteSent}
      />

      <section className="home-confirmation-section">
        <div className="section-head">
          <h2>
            Требуется подтверждение
          </h2>
        </div>

        {confirmationLoans.length === 0 && (
          <EmptyState
            title="Подтверждений пока нет"
            text="Здесь появятся заявки и возвраты, по которым нужно действие одной из сторон."
          />
        )}

        {confirmationLoans.map((loan) => (
          <LoanCard
            key={loan.id}
            loan={loan}
            user={user}
            isAdmin={isAdmin}
            repayments={repayments[loan.id]}
            fundingActivationCode={fundingActivationCodes?.[loan.id] || ""}
            onLoadRepayments={onLoadRepayments}
            onConfirm={onConfirm}
            onRegenerateActivationCode={onRegenerateActivationCode}
            onActivateLoan={onActivateLoan}
            onActivateLoanByConfirmation={onActivateLoanByConfirmation}
            onReject={onReject}
            onMarkPaid={onMarkPaid}
            onRepay={onRepay}
            onConfirmRepayment={onConfirmRepayment}
            onRejectRepayment={onRejectRepayment}
          />
        ))}
      </section>
    </>
  );
}

export default HomePage;
