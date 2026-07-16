import type { BarItem } from "./BarList";
import { BarList } from "./BarList";

interface Props {
  title: string;
  sub: string;
  items: BarItem[];
  loading: boolean;
  emptyLabel: string;
}

/** A titled card wrapping a BarList -- used for the team-level and
 * channel-level Slack issue breakdowns. */
export function BarListCard({ title, sub, items, loading, emptyLabel }: Props) {
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">{title}</div>
          <div className="card-sub">{sub}</div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 90, width: "100%" }} />
      ) : items.length === 0 ? (
        <div className="card-sub">{emptyLabel}</div>
      ) : (
        <BarList items={items} />
      )}
    </div>
  );
}
