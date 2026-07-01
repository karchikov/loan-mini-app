import UserHistoryCard from "../components/UserHistoryCard";

function HistoryPage({
  title = "Последние события",
  emptyText = "Событий пока нет",
  history,
}) {
  return (
    <div>
      <UserHistoryCard
        title={title}
        emptyText={emptyText}
        history={history}
      />
    </div>
  );
}

export default HistoryPage;
