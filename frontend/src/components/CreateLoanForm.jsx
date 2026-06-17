import { useEffect, useMemo, useRef, useState } from "react";

import { getMyInviteLink } from "../api/users";
import { runTelegramInviteFlow } from "../utils/telegramInvite";

const AVAILABLE_CURRENCIES = [
  "RUB",
  "USD",
  "USDT",
  "USDC",
];

function formatUserName(user) {
  const nameParts = [
    user.first_name,
    user.last_name,
  ].filter(Boolean);

  const fullName = nameParts.join(" ");

  if (user.username) {
    return `${fullName || "Пользователь"} (@${user.username})`;
  }

  return fullName || `Пользователь #${user.id}`;
}

function normalizeSearchValue(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}

function CreateLoanForm({
  lenders = [],
  onCreate,
  onInviteSent,
}) {
  const dropdownRef = useRef(null);

  const [lenderId, setLenderId] = useState("");
  const [amount, setAmount] = useState("");
  const [annualInterestRate, setAnnualInterestRate] = useState("");
  const [currency, setCurrency] = useState("RUB");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");

  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [lenderSearch, setLenderSearch] = useState("");
  const [inviteModalOpen, setInviteModalOpen] = useState(false);

  const [loading, setLoading] = useState(false);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [error, setError] = useState("");
  const [infoMessage, setInfoMessage] = useState("");

  const hasAvailableLenders = lenders.length > 0;

  const selectedLender = lenders.find(
    (user) => String(user.id) === String(lenderId),
  );

  const selectedLenderText = selectedLender
    ? formatUserName(selectedLender)
    : "Выберите кредитора";

  const filteredLenders = useMemo(() => {
    const searchValue = normalizeSearchValue(lenderSearch);

    if (!searchValue) {
      return lenders;
    }

    return lenders.filter((user) => {
      const userText = normalizeSearchValue(
        [
          user.first_name,
          user.last_name,
          user.username,
          formatUserName(user),
        ].join(" "),
      );

      return userText.includes(searchValue);
    });
  }, [lenders, lenderSearch]);

  useEffect(() => {
    function handleDocumentClick(event) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target)
      ) {
        setDropdownOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleDocumentClick,
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleDocumentClick,
      );
    };
  }, []);

  async function handleInviteNewLender() {
    try {
      setInviteLoading(true);
      setInviteModalOpen(false);
      setDropdownOpen(false);
      setError("");
      setInfoMessage("");

      await runTelegramInviteFlow(getMyInviteLink);

      if (onInviteSent) {
        await onInviteSent();
      }

      setInfoMessage(
        "Приглашение подготовлено. После входа пользователя список кредиторов обновится автоматически при возврате в приложение.",
      );
    } catch (currentError) {
      console.error(currentError);

      setError(
        "Не удалось создать ссылку приглашения",
      );
    } finally {
      setInviteLoading(false);
    }
  }

  function handleDropdownToggle() {
    if (loading || inviteLoading) {
      return;
    }

    setDropdownOpen((currentValue) => !currentValue);
  }

  function handleLenderSelect(selectedUserId) {
    setError("");
    setInfoMessage("");
    setLenderId(String(selectedUserId));
    setDropdownOpen(false);
    setLenderSearch("");
  }

  function handleInviteClick() {
    setDropdownOpen(false);
    setInviteModalOpen(true);
  }

  function handleInviteCancel() {
    if (inviteLoading) {
      return;
    }

    setInviteModalOpen(false);
  }

  async function handleSubmit(e) {
    e.preventDefault();

    setError("");
    setInfoMessage("");

    const lenderIdValue = Number(lenderId);
    const amountValue = Number(amount);
    const annualInterestRateValue = Number(annualInterestRate);

    if (!selectedLender) {
      setError(
        "Выберите кредитора из списка доступных пользователей",
      );
      return;
    }

    if (!amountValue || amountValue <= 0) {
      setError(
        "Сумма должна быть больше 0",
      );
      return;
    }

    if (
      annualInterestRate === "" ||
      Number.isNaN(annualInterestRateValue) ||
      annualInterestRateValue < 0 ||
      annualInterestRateValue > 1000
    ) {
      setError(
        "Процентная ставка должна быть от 0 до 1000",
      );
      return;
    }

    if (!AVAILABLE_CURRENCIES.includes(currency)) {
      setError(
        "Выберите корректную валюту займа",
      );
      return;
    }

    try {
      setLoading(true);

      const payload = {
        lender_id: lenderIdValue,
        amount: amountValue,
        annual_interest_rate: annualInterestRateValue,
        currency,
        description: description.trim() || null,
        due_date: dueDate ? `${dueDate}T00:00:00` : null,
      };

      await onCreate(payload);

      setLenderId("");
      setAmount("");
      setAnnualInterestRate("");
      setCurrency("RUB");
      setDescription("");
      setDueDate("");
      setLenderSearch("");
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Не удалось запросить займ",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card create-loan-card">
      <div className="form-header">
        <h2>
          Запросить займ
        </h2>

        <p>
          Выберите кредитора из вашей Telegram-сети, укажите сумму, валюту и описание заявки.
        </p>
      </div>

      {!hasAvailableLenders && (
        <div className="form-error">
          <p>
            <strong>
              У вас пока нет доступных кредиторов.
            </strong>
          </p>

          <p>
            Пригласите человека в приложение. После входа он появится в этом списке, и вы сможете запросить у него займ.
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <label className="form-field">
          <span>Кредитор</span>

          <div
            className="custom-dropdown"
            ref={dropdownRef}
          >
            <button
              type="button"
              className={`custom-dropdown-toggle ${
                dropdownOpen ? "open" : ""
              }`}
              onClick={handleDropdownToggle}
              disabled={loading || inviteLoading}
            >
              <span
                className={
                  selectedLender
                    ? "custom-dropdown-value"
                    : "custom-dropdown-placeholder"
                }
              >
                {selectedLenderText}
              </span>

              <span className="custom-dropdown-arrow">
                ▾
              </span>
            </button>

            {dropdownOpen && (
              <div className="custom-dropdown-menu">
                <div className="custom-dropdown-search-box">
                  <input
                    type="text"
                    value={lenderSearch}
                    onChange={(e) => setLenderSearch(e.target.value)}
                    placeholder="Поиск кредитора"
                    className="custom-dropdown-search"
                    autoFocus
                  />
                </div>

                <button
                  type="button"
                  className="custom-dropdown-option invite-option pinned"
                  onClick={handleInviteClick}
                  disabled={loading || inviteLoading}
                >
                  {inviteLoading
                    ? "Создаём ссылку..."
                    : "👤 Пригласить нового кредитора"}
                </button>

                <div className="custom-dropdown-divider" />

                <div className="custom-dropdown-scroll">
                  {hasAvailableLenders && filteredLenders.length > 0 ? (
                    filteredLenders.map((user) => (
                      <button
                        type="button"
                        key={user.id}
                        className={`custom-dropdown-option ${
                          String(user.id) === String(lenderId)
                            ? "selected"
                            : ""
                        }`}
                        onClick={() => handleLenderSelect(user.id)}
                      >
                        {formatUserName(user)}
                      </button>
                    ))
                  ) : (
                    <div className="custom-dropdown-empty">
                      Кредитор не найден
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </label>

        <label className="form-field">
          <span>Сумма займа</span>

          <input
            type="number"
            placeholder="Например: 5000"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            disabled={loading || inviteLoading || !hasAvailableLenders}
          />
        </label>

        <label className="form-field">
          <span>Процентная ставка, % годовых</span>

          <input
            type="number"
            min="0"
            max="1000"
            step="0.01"
            placeholder="Например: 12.5"
            value={annualInterestRate}
            onChange={(e) => setAnnualInterestRate(e.target.value)}
            disabled={loading || inviteLoading || !hasAvailableLenders}
          />
        </label>

        <label className="form-field">
          <span>Валюта</span>

          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            disabled={loading || inviteLoading || !hasAvailableLenders}
          >
            {AVAILABLE_CURRENCIES.map((currencyValue) => (
              <option
                key={currencyValue}
                value={currencyValue}
              >
                {currencyValue}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field">
          <span>Срок возврата</span>

          <input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            disabled={loading || inviteLoading || !hasAvailableLenders}
          />
        </label>

        <label className="form-field">
          <span>Описание</span>

          <input
            type="text"
            placeholder="Например: до пятницы"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={loading || inviteLoading || !hasAvailableLenders}
          />
        </label>

        {infoMessage && (
          <p className="form-success">
            {infoMessage}
          </p>
        )}

        {error && (
          <p className="form-error">
            {error}
          </p>
        )}

        <button
          type="submit"
          className="full-width create-loan-button"
          disabled={loading || inviteLoading || !hasAvailableLenders}
        >
          {loading ? "Отправка..." : "Запросить займ"}
        </button>
      </form>

      {inviteModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <h3>
              Отправить приглашение?
            </h3>

            <p>
              Telegram откроет окно отправки сообщения. После этого нужно вручную нажать кнопку отправки в Telegram.
            </p>

            <div className="modal-actions">
              <button
                type="button"
                onClick={handleInviteNewLender}
                disabled={inviteLoading}
              >
                {inviteLoading
                  ? "Создаём ссылку..."
                  : "Отправить приглашение"}
              </button>

              <button
                type="button"
                className="secondary-button"
                onClick={handleInviteCancel}
                disabled={inviteLoading}
              >
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CreateLoanForm;