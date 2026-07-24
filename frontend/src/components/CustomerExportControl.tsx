import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Period } from "../types";

interface Props {
  period: Period;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Customers tab's download control -- a single button revealing a dropdown
 * with two options, same trigger/menu pattern as Header's account menu, so
 * the two-way choice doesn't cost permanent toolbar width (an always-visible
 * mode select + company select broke the section header's layout).
 * "Tickets per customer" is the existing all-customer counts export;
 * "Tickets by customer" drills into a company picker before downloading.
 * Both share the tab's (open, no-login) gating -- see api/dashboard_routes.py. */
export function CustomerExportControl({ period }: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [byCustomer, setByCustomer] = useState(false);
  const [customerNames, setCustomerNames] = useState<string[]>([]);
  const [loadingNames, setLoadingNames] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState("");
  const [exporting, setExporting] = useState(false);

  const menuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!menuOpen) return;
    function onClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
        setByCustomer(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [menuOpen]);

  function openByCustomer() {
    setByCustomer(true);
    if (customerNames.length > 0) return;
    setLoadingNames(true);
    api
      .customerNames()
      .then((r) => setCustomerNames(r.customer_names))
      .finally(() => setLoadingNames(false));
  }

  async function downloadCounts() {
    setExporting(true);
    try {
      const blob = await api.exportCustomerCounts(period);
      downloadBlob(blob, `customer-issues-${period.replace(/:/g, "_")}.xlsx`);
      setMenuOpen(false);
    } finally {
      setExporting(false);
    }
  }

  async function downloadByCustomer() {
    if (!selectedCustomer) return;
    setExporting(true);
    try {
      const blob = await api.exportCustomerTickets(period, selectedCustomer);
      const safeName = selectedCustomer.replace(/[^a-z0-9]+/gi, "_");
      downloadBlob(blob, `customer-tickets-${safeName}-${period.replace(/:/g, "_")}.xlsx`);
      setMenuOpen(false);
      setByCustomer(false);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="auth-menu-wrap" ref={menuRef}>
      <button
        className="section-action"
        onClick={() => setMenuOpen((o) => !o)}
        aria-expanded={menuOpen}
      >
        {exporting ? "⏳ Exporting…" : "⬇️ Download Excel"}
      </button>
      {menuOpen && (
        <div className="auth-menu">
          {!byCustomer ? (
            <>
              <button className="auth-menu-item" disabled={exporting} onClick={downloadCounts}>
                Ticket count per customer
              </button>
              <button className="auth-menu-item" disabled={exporting} onClick={openByCustomer}>
                Tickets by customer
              </button>
            </>
          ) : (
            <>
              <div className="auth-menu-name">Tickets by customer</div>
              <select
                className="select"
                value={selectedCustomer}
                onChange={(e) => setSelectedCustomer(e.target.value)}
                disabled={exporting || loadingNames}
                style={{ margin: "0 8px 6px", width: "calc(100% - 16px)" }}
              >
                <option value="">{loadingNames ? "Loading companies…" : "Select a company"}</option>
                {customerNames.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
              <button
                className="auth-menu-item"
                disabled={exporting || !selectedCustomer}
                onClick={downloadByCustomer}
              >
                {exporting ? "⏳ Exporting…" : "⬇️ Download"}
              </button>
              <button className="auth-menu-item" disabled={exporting} onClick={() => setByCustomer(false)}>
                ← Back
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
