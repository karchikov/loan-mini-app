export function formatMoney(value, currency = "") {
  if (value === null || value === undefined) {
    return currency ? `0.00 ${currency}` : "0.00";
  }

  const formattedValue = Number(value).toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return currency ? `${formattedValue} ${currency}` : formattedValue;
}

export function formatDate(value) {
  if (!value) {
    return "-";
  }

  return new Date(value).toLocaleString("ru-RU");
}