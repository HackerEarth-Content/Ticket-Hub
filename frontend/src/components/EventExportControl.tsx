import { useEffect, useRef, useState } from "react";
import { api } from "../api";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Download control for "issue report for an event" -- same trigger/menu
 * pattern as CustomerExportControl, but single-mode: event_name is a
 * controlled HubSpot dropdown (see hubspot_pipeline.models._resolve_event_name),
 * not free text with aliasing problems, so no fuzzy-list mode is needed here. */
export function EventExportControl() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [eventNames, setEventNames] = useState<string[]>([]);
  const [loadingNames, setLoadingNames] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState("");
  const [exporting, setExporting] = useState(false);

  const menuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!menuOpen) return;
    function onClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [menuOpen]);

  function toggleMenu() {
    setMenuOpen((o) => !o);
    if (eventNames.length > 0) return;
    setLoadingNames(true);
    api
      .eventNames()
      .then((r) => setEventNames(r.event_names))
      .finally(() => setLoadingNames(false));
  }

  async function downloadByEvent() {
    if (!selectedEvent) return;
    setExporting(true);
    try {
      const blob = await api.exportEventTickets(selectedEvent);
      const safeName = selectedEvent.replace(/[^a-z0-9]+/gi, "_");
      downloadBlob(blob, `event-tickets-${safeName}.xlsx`);
      setMenuOpen(false);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="auth-menu-wrap" ref={menuRef}>
      <button className="section-action" onClick={toggleMenu} aria-expanded={menuOpen}>
        {exporting ? "⏳ Exporting…" : "⬇️ Issues by event"}
      </button>
      {menuOpen && (
        <div className="auth-menu">
          <div className="auth-menu-name">Tickets by event</div>
          <select
            className="select"
            value={selectedEvent}
            onChange={(e) => setSelectedEvent(e.target.value)}
            disabled={exporting || loadingNames}
            style={{ margin: "0 8px 6px", width: "calc(100% - 16px)" }}
          >
            <option value="">{loadingNames ? "Loading events…" : "Select an event"}</option>
            {eventNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <button
            className="auth-menu-item"
            disabled={exporting || !selectedEvent}
            onClick={downloadByEvent}
          >
            {exporting ? "⏳ Exporting…" : "⬇️ Download"}
          </button>
        </div>
      )}
    </div>
  );
}
