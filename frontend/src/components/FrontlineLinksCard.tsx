import { useEffect, useState } from "react";
import { api } from "../api";
import type { DashboardLink } from "../types";

/** A standalone card (not a tucked-away menu) so pinned links are as visible
 * as any other frontline metric -- add/edit happens inline in the same card
 * instead of a popover, since the list is short and this is meant to be
 * glanced at, not dug for. */
const _COLLAPSED_COUNT = 3;

export function FrontlineLinksCard() {
  const [links, setLinks] = useState<DashboardLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<number | "new" | null>(null);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(false);

  function refresh() {
    setLoading(true);
    api
      .dashboardLinks()
      .then(setLinks)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    refresh();
  }, []);

  function startEdit(link: DashboardLink) {
    setEditingId(link.id);
    setName(link.name);
    setUrl(link.url);
  }

  function startAdd() {
    setEditingId("new");
    setName("");
    setUrl("");
  }

  async function save() {
    if (!name.trim() || !url.trim()) return;
    setSaving(true);
    try {
      if (editingId === "new") {
        await api.addDashboardLink(name.trim(), url.trim());
      } else if (editingId !== null) {
        await api.updateDashboardLink(editingId, name.trim(), url.trim());
      }
      setEditingId(null);
      refresh();
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: number) {
    setSaving(true);
    try {
      await api.deleteDashboardLink(id);
      refresh();
    } finally {
      setSaving(false);
    }
  }

  const form = (
    <div className="fl-form">
      <input
        className="select"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Name"
        disabled={saving}
        autoFocus
      />
      <input
        className="select"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="https://…"
        disabled={saving}
      />
      <button className="table-toggle" disabled={saving || !name.trim() || !url.trim()} onClick={save}>
        Save
      </button>
      <button className="table-toggle" disabled={saving} onClick={() => setEditingId(null)}>
        Cancel
      </button>
    </div>
  );

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <div className="card-title">Quick Links</div>
          <div className="card-sub">Shortcuts your team pinned to this dashboard</div>
        </div>
        {editingId !== "new" && (
          <button className="table-toggle" onClick={startAdd}>
            + Add link
          </button>
        )}
      </div>

      {editingId === "new" && form}

      {loading ? (
        <div className="skeleton" style={{ height: 60, width: "100%" }} />
      ) : links.length === 0 && editingId !== "new" ? (
        <div className="card-sub">No links yet - add one above.</div>
      ) : (
        <>
          <div className="fl-list" style={expanded ? { maxHeight: 360, overflowY: "auto" } : undefined}>
            {(expanded ? links : links.slice(0, _COLLAPSED_COUNT)).map((link) =>
              editingId === link.id ? (
                <div key={link.id}>{form}</div>
              ) : (
                <div key={link.id} className="fl-row">
                  <a href={link.url} target="_blank" rel="noreferrer" className="fl-link">
                    {link.name}
                  </a>
                  <span className="fl-actions">
                    <button className="icon-btn" onClick={() => startEdit(link)} title="Edit" disabled={saving}>
                      ✏️
                    </button>
                    <button className="icon-btn" onClick={() => remove(link.id)} title="Delete" disabled={saving}>
                      🗑️
                    </button>
                  </span>
                </div>
              ),
            )}
          </div>
          {links.length > _COLLAPSED_COUNT && (
            <button
              className="table-toggle"
              style={{ marginTop: 8 }}
              onClick={() => setExpanded((v) => !v)}
            >
              {expanded ? "Show less" : `Show more (${links.length - _COLLAPSED_COUNT})`}
            </button>
          )}
        </>
      )}
    </div>
  );
}
