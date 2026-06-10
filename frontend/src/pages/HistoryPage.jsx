import UserHistoryCard from "../components/UserHistoryCard";

function HistoryPage({
  history,
}) {
  return (
    <div>
      <UserHistoryCard history={history} />
    </div>
  );
}

export default HistoryPage;