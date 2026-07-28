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

// Shared neutral fill for anything past the categorical ramp and for the
// pinned-tail buckets below -- these aren't meant to compete for identity
// color, just to still render as a bar with its own count and label.
const NEUTRAL_COLOR = "var(--ink-3)";

// Not real support modules -- junk/no-signal buckets from HubSpot's native
// dropdown (see dashboard/utils.py's _MODULE_NOT_SET_LABEL). Always sorted
// to the bottom of the list, below every real module.
const PINNED_TAIL = ["Not Actionable", "Spam", "No Information Received", "Duplicate", "Not set"];

interface Props {
  distribution: ModuleDistribution | null;
  moduleTickets: ModuleTickets | null;
  loading: boolean;
}

export function ModuleDistributionCard({ distribution, moduleTickets, loading }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const items = buildItems(distribution);
  const group = expanded ? moduleTickets?.tickets_by_module[expanded] : null;

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Volume by module</div>
          <div className="card-sub">
            All modules this period
            {moduleTickets ? " — click a module for its tickets" : ""}
          </div>
        </div>
      </div>
      {loading ? (
        <div className="skeleton" style={{ height: 180, width: "100%" }} />
      ) : (
        <>
          <div style={{ maxHeight: 280, overflowY: "auto", paddingRight: 4 }}>
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
          </div>
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
  const entries = Object.entries(distribution.ticket_count_by_module);
  const real = entries.filter(([label]) => !PINNED_TAIL.includes(label)).sort((a, b) => b[1] - a[1]);
  const pinned = entries.filter(([label]) => PINNED_TAIL.includes(label)).sort((a, b) => b[1] - a[1]);

  const realItems = real.map(([label, value], i) => ({
    label,
    value,
    // Past the fixed ramp, no generated hue -- share the neutral fill instead.
    color: i < CATEGORICAL_SLOTS.length ? CATEGORICAL_SLOTS[i] : NEUTRAL_COLOR,
  }));
  const pinnedItems = pinned.map(([label, value]) => ({
    label,
    value,
    color: NEUTRAL_COLOR,
  }));
  return [...realItems, ...pinnedItems];
}
