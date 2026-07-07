import type { CSSProperties } from "react";

export type DashboardTab = "overview" | "frontline" | "backline" | "customers";

const TABS: { key: DashboardTab; label: string; sub: string; accent: string }[] = [
  { key: "overview", label: "Overview", sub: "Org-wide", accent: "var(--accent-blue)" },
  { key: "frontline", label: "Frontline", sub: "Support desk", accent: "var(--accent-aqua)" },
  { key: "backline", label: "Backline", sub: "Engineering escalations", accent: "var(--accent-orange)" },
  { key: "customers", label: "Customers", sub: "By account", accent: "var(--accent-indigo)" },
];

interface Props {
  active: DashboardTab;
  onChange: (tab: DashboardTab) => void;
}

/** Top-level content switcher -- each tab keeps its own accent (matching the
 * section-heading colors already used inside it), so the active tab reads as
 * "which zone of the dashboard am I in" at a glance. */
export function TabNav({ active, onChange }: Props) {
  return (
    <nav className="tab-nav" role="tablist" aria-label="Dashboard sections">
      {TABS.map((t) => (
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
