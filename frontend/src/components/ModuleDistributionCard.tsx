import { useState } from "react";
import type { ModuleDistribution, ModuleTickets } from "../types";
import { hubspotTicketUrl } from "../format";
import { BarList } from "./BarList";

// Fixed categorical order -- validated for CVD-safe adjacency (see color report).
// Never cycled, never reassigned by value.
const CATEGORICAL_SLOTS = [
  "var(--accent-blue)",
  "var(--accent-aqua)",
  "var(--accent-yellow)",
  "var(--accent-green)",
  "var(--accent-indigo)",
  "var(--accent-red)",
  "var(--accent-magenta)",
  "var(--accent-orange)",
];
const MAX_SLOTS = 8;

interface Props {
  distribution: ModuleDistribution | null;
  moduleTickets: ModuleTickets | null;
  loading: boolean;
}

export function ModuleDistributionCard({ distribution, moduleTickets, loading }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const items = buildItems(distribution);
  // "Other" is a frontend-only fold of the tail modules -- there's no single
  // real module behind it, so it isn't clickable.
  const group = expanded ? moduleTickets?.tickets_by_module[expanded] : null;

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Volume by module</div>
          <div className="card-sub">
            {items.length > MAX_SLOTS - 1
              ? `Top ${MAX_SLOTS - 1}, tail folded into Other`
              : "All modules this period"}
            {moduleTickets ? " — click a module for its tickets" : ""}
          </div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 180, width: "100%" }} />
      ) : (
        <>
          <BarList
            items={items}
            activeLabel={expanded}
            onItemClick={
              moduleTickets
                ? (label) =>
                    moduleTickets.tickets_by_module[label] &&
                    setExpanded(expanded === label ? null : label)
                : undefined
            }
          />
          {group && (
            <div className="tbl-wrap" style={{ marginTop: 12 }}>
              <table>
                <thead>
                  <tr>
                    <th>Ticket</th>
                    <th>Status</th>
                    <th>Owner</th>
                  </tr>
                </thead>
                <tbody>
                  {group.tickets.map((t) => (
                    <tr key={t.ticket_id}>
                      <td className="name-cell" title={t.subject}>
                        <a href={hubspotTicketUrl(t.ticket_id)} target="_blank" rel="noopener noreferrer">
                          {t.subject || t.ticket_id}
                        </a>
                        <div className="card-sub">#{t.ticket_id}</div>
                      </td>
                      <td>{t.canonical_status}</td>
                      <td>{t.owner_name ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {group.truncated && (
                <div className="card-sub" style={{ marginTop: 6 }}>
                  Showing first {group.tickets.length} of {group.count}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function buildItems(distribution: ModuleDistribution | null) {
  if (!distribution) return [];
  const entries = Object.entries(distribution.ticket_count_by_module).sort(
    (a, b) => b[1] - a[1]
  );

  if (entries.length <= MAX_SLOTS) {
    return entries.map(([label, value], i) => ({
      label,
      value,
      color: CATEGORICAL_SLOTS[i],
    }));
  }

  // Series-count ladder: past 8, fold the tail into "Other" rather than
  // generating a 9th hue (indistinguishable under CVD anyway).
  const head = entries.slice(0, MAX_SLOTS - 1);
  const tail = entries.slice(MAX_SLOTS - 1);
  const otherExisting = tail.find(([label]) => label === "Other");
  const otherTotal = tail.reduce((sum, [, v]) => sum + v, 0);

  const items = head.map(([label, value], i) => ({
    label,
    value,
    color: CATEGORICAL_SLOTS[i],
  }));
  items.push({
    label: otherExisting ? "Other" : "Other (combined)",
    value: otherTotal,
    color: CATEGORICAL_SLOTS[MAX_SLOTS - 1],
  });
  return items;
}
