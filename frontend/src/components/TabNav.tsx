import type { CSSProperties } from "react";

export type DashboardTab =
  | "overview"
  | "frontline"
  | "backline"
  | "customers"
  | "events"
  | "content_oncall"
  | "frontline_metrics";

const TABS: { key: DashboardTab; label: string; sub: string; accent: string; requiresAuth?: boolean }[] = [
  { key: "overview", label: "Overview", sub: "Org-wide", accent: "var(--accent-blue)" },
  { key: "frontline", label: "Frontline", sub: "L1", accent: "var(--accent-aqua)" },
  { key: "backline", label: "Backline", sub: "L2", accent: "var(--accent-orange)" },
  { key: "customers", label: "Customers", sub: "By account", accent: "var(--accent-indigo)" },
  { key: "events", label: "Programs/Events", sub: "By event", accent: "var(--accent-yellow)" },
  { key: "content_oncall", label: "Slack Requests", sub: "Content/engg on-call", accent: "var(--accent-magenta)" },
  {
    key: "frontline_metrics",
    label: "Frontline Metric Dashboard",
    sub: "Quarterly rollup",
    accent: "var(--accent-aqua)",
    requiresAuth: true,
  },
];

interface Props {
  active: DashboardTab;
  onChange: (tab: DashboardTab) => void;
  isLoggedIn: boolean;
}

/** Top-level content switcher -- each tab keeps its own accent (matching the
 * section-heading colors already used inside it), so the active tab reads as
 * "which zone of the dashboard am I in" at a glance. Auth-gated tabs
 * (requiresAuth) are dropped from the nav entirely for signed-out visitors,
 * not just their content -- there's nothing team-internal to advertise. */
export function TabNav({ active, onChange, isLoggedIn }: Props) {
  const visibleTabs = TABS.filter((t) => !t.requiresAuth || isLoggedIn);
  return (
    <nav className="tab-nav" role="tablist" aria-label="Dashboard sections">
      {visibleTabs.map((t) => (
        <button
          key={t.key}
          role="tab"
          aria-selected={active === t.key}
          className={`tab-nav-item ${active === t.key ? "active" : ""}`}
          style={{ "--tab-accent": t.accent } as CSSProperties}
          onClick={() => onChange(t.key)}
        >
          <span className="tab-nav-label">{t.label}</span>
          <span className="tab-nav-sub">{t.sub}</span>
        </button>
      ))}
    </nav>
  );
}
