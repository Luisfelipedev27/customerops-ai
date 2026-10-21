import { Layers } from "lucide-react";
export const money = (n) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n || 0);
export const date = (s) =>
  new Date(s).toLocaleString("en-US", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
const riskLabel = {
  high: "High risk",
  medium: "Needs attention",
  low: "Healthy",
};
const statusLabel = {
  pending: "Awaiting approval",
  executed: "Executed",
  rejected: "Rejected",
  ready: "Indexed",
  failed: "Failed",
  open: "Open",
  resolved: "Resolved",
  in_progress: "In progress",
  completed: "Completed",
};
export function Badge({ value }) {
  return (
    <span className={"badge " + value}>
      <i />
      {riskLabel[value] || statusLabel[value] || value}
    </span>
  );
}
export function Empty({ text }) {
  return (
    <div className="empty">
      <Layers size={28} />
      <p>{text}</p>
    </div>
  );
}
