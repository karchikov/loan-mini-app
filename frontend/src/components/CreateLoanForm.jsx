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
  onCreate,
}) {
  const [borrowerId, setBorrowerId] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();

    setError("");

    const borrowerIdValue = Number(borrowerId);
    const amountValue = Number(amount);

    if (!borrowerIdValue || borrowerIdValue <= 0) {
      setError("Select borrower");
      return;
    }

    if (!amountValue || amountValue <= 0) {
      setError("Amount must be greater than 0");
      return;
    }

    try {
      setLoading(true);

      await onCreate({
        borrower_id: borrowerIdValue,
        amount: amountValue,
        description: description.trim() || null,
      });

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
      <h2>Create Loan</h2>

      <form onSubmit={handleSubmit}>
        <select
          value={borrowerId}
          onChange={(e) => setBorrowerId(e.target.value)}
          disabled={loading}
        >
          <option value="">
            Select borrower
          </option>

          {users.map((user) => (
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