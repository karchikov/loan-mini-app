import { useState } from "react";

function formatUserName(user) {
  const nameParts = [
    user.first_name,
    user.last_name,
  ].filter(Boolean);

  const fullName = nameParts.join(" ");

  if (user.username) {
    return `${fullName || "User"} (@${user.username})`;
  }

  return fullName || `User #${user.id}`;
}

function CreateLoanForm({
  users,
  currentUser,
  isAdmin,
  onCreate,
}) {
  const [lenderId, setLenderId] = useState("");
  const [borrowerId, setBorrowerId] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedLenderId = lenderId
    ? Number(lenderId)
    : currentUser.id;

  const borrowerOptions = users.filter((user) => {
    return user.id !== selectedLenderId;
  });

  const lenderOptions = users.filter((user) => {
    if (borrowerId) {
      return user.id !== Number(borrowerId);
    }

    return true;
  });

  async function handleSubmit(e) {
    e.preventDefault();

    setError("");

    const borrowerIdValue = Number(borrowerId);
    const lenderIdValue = lenderId ? Number(lenderId) : null;
    const amountValue = Number(amount);

    if (!borrowerIdValue || borrowerIdValue <= 0) {
      setError("Select borrower");
      return;
    }

    if (isAdmin && lenderIdValue === borrowerIdValue) {
      setError("Lender and borrower must be different");
      return;
    }

    if (!isAdmin && borrowerIdValue === currentUser.id) {
      setError("You cannot create a loan to yourself");
      return;
    }

    if (!amountValue || amountValue <= 0) {
      setError("Amount must be greater than 0");
      return;
    }

    try {
      setLoading(true);

      const payload = {
        borrower_id: borrowerIdValue,
        amount: amountValue,
        description: description.trim() || null,
      };

      if (isAdmin && lenderIdValue) {
        payload.lender_id = lenderIdValue;
      }

      await onCreate(payload);

      setLenderId("");
      setBorrowerId("");
      setAmount("");
      setDescription("");
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Failed to create loan"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card create-loan-card">
      <h2>
        {isAdmin ? "Create Loan as Admin" : "Create Loan"}
      </h2>

      <form onSubmit={handleSubmit}>
        {isAdmin && (
          <select
            value={lenderId}
            onChange={(e) => setLenderId(e.target.value)}
            disabled={loading}
          >
            <option value="">
              Я сам / текущий админ
            </option>

            {lenderOptions.map((user) => (
              <option
                key={user.id}
                value={user.id}
              >
                {formatUserName(user)}
              </option>
            ))}
          </select>
        )}

        <select
          value={borrowerId}
          onChange={(e) => setBorrowerId(e.target.value)}
          disabled={loading}
        >
          <option value="">
            Select borrower
          </option>

          {borrowerOptions.map((user) => (
            <option
              key={user.id}
              value={user.id}
            >
              {formatUserName(user)}
            </option>
          ))}
        </select>

        <input
          type="number"
          placeholder="Amount"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          disabled={loading}
        />

        <input
          type="text"
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={loading}
        />

        {error && <p className="form-error">{error}</p>}

        <button
          type="submit"
          className="full-width"
          disabled={loading}
        >
          {loading ? "Creating..." : "Create Loan"}
        </button>
      </form>
    </div>
  );
}

export default CreateLoanForm;