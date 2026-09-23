import { useState } from "react";
import type { DragEvent } from "react";
import { api } from "../api";
import type { AgentShift, FrontlineAgent } from "../types";
import { DAY_LABELS } from "../agentShifts";
import { TimePickerDial } from "./TimePickerDial";

type DayType = "working" | "week_off" | "holiday";

function emptyWeek(): AgentShift[] {
  return Array.from({ length: 7 }, (_, day_of_week) => ({
    day_of_week,
    is_week_off: true,
    is_holiday: false,
    start_time: null,
    end_time: null,
  }));
}

function dayType(shift: AgentShift): DayType {
  if (shift.is_holiday) return "holiday";
  if (shift.is_week_off) return "week_off";
  return "working";
}

function formatTime(hhmm: string): string {
  const [h, m] = hhmm.split(":").map(Number);
  const period = h >= 12 ? "PM" : "AM";
  const hour12 = h % 12 || 12;
  return `${hour12}:${String(m).padStart(2, "0")} ${period}`;
}

function ShiftCell({ shift }: { shift: AgentShift | undefined }) {
  if (!shift || shift.is_holiday) return <span className="holiday-pill">Holiday</span>;
  if (shift.is_week_off || !shift.start_time || !shift.end_time) {
    return <span className="weekoff-pill">Week off</span>;
  }
  return (
    <span className="shift-pill">
      {formatTime(shift.start_time)} – {formatTime(shift.end_time)}
    </span>
  );
}

interface Props {
  agents: FrontlineAgent[];
  loading: boolean;
  onChanged: () => void;
}

export function FrontlineAgentsCard({ agents, loading, onChanged }: Props) {
  const [addingAgent, setAddingAgent] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [slackId, setSlackId] = useState("");
  const [saving, setSaving] = useState(false);

  const [editingAgentId, setEditingAgentId] = useState<number | null>(null);
  const [draftShifts, setDraftShifts] = useState<AgentShift[]>([]);

  const [editingInfoId, setEditingInfoId] = useState<number | null>(null);
  const [infoName, setInfoName] = useState("");
  const [infoEmail, setInfoEmail] = useState("");
  const [infoSlackId, setInfoSlackId] = useState("");

  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [dragOverId, setDragOverId] = useState<number | null>(null);
  const [pendingSwap, setPendingSwap] = useState<{ a: FrontlineAgent; b: FrontlineAgent } | null>(null);
  const [swapping, setSwapping] = useState(false);

  const anyEditing = editingAgentId !== null || editingInfoId !== null;
  const canDrag = !anyEditing && !saving && !pendingSwap;

  async function addAgent() {
    if (!name.trim() || !email.trim()) return;
    setSaving(true);
    try {
      const created = await api.addFrontlineAgent(name.trim(), email.trim(), slackId.trim());
      setAddingAgent(false);
      setName("");
      setEmail("");
      setSlackId("");
      onChanged();
      startEditShifts(created.id, created.shifts);
    } finally {
      setSaving(false);
    }
  }

  async function removeAgent(id: number) {
    if (!window.confirm("Remove this agent and their shifts?")) return;
    setSaving(true);
    try {
      await api.deleteFrontlineAgent(id);
      onChanged();
    } finally {
      setSaving(false);
    }
  }

  function startEditShifts(id: number, shifts: AgentShift[]) {
    setEditingAgentId(id);
    setDraftShifts(shifts.length ? shifts.map((s) => ({ ...s })) : emptyWeek());
  }

  function updateDraftDay(day: number, patch: Partial<AgentShift>) {
    setDraftShifts((prev) => prev.map((s) => (s.day_of_week === day ? { ...s, ...patch } : s)));
  }

  function setDraftDayType(day: number, type: DayType) {
    if (type === "working") {
      updateDraftDay(day, { is_week_off: false, is_holiday: false });
    } else {
      updateDraftDay(day, {
        is_week_off: type === "week_off",
        is_holiday: type === "holiday",
        start_time: null,
        end_time: null,
      });
    }
  }

  function startEditInfo(agent: FrontlineAgent) {
    setEditingInfoId(agent.id);
    setInfoName(agent.name);
    setInfoEmail(agent.email);
    setInfoSlackId(agent.slack_id ?? "");
  }

  async function saveInfo() {
    if (editingInfoId === null || !infoName.trim() || !infoEmail.trim()) return;
    setSaving(true);
    try {
      await api.updateFrontlineAgent(editingInfoId, infoName.trim(), infoEmail.trim(), infoSlackId.trim());
      setEditingInfoId(null);
      onChanged();
    } finally {
      setSaving(false);
    }
  }

  async function saveShifts() {
    if (editingAgentId === null) return;
    setSaving(true);
    try {
      await api.setFrontlineAgentShifts(editingAgentId, draftShifts);
      setEditingAgentId(null);
      onChanged();
    } finally {
      setSaving(false);
    }
  }

  function handleDragStart(agent: FrontlineAgent) {
    if (!canDrag) return;
    setDraggingId(agent.id);
  }

  function handleDragOver(e: DragEvent, agent: FrontlineAgent) {
    if (draggingId !== null && draggingId !== agent.id) e.preventDefault();
  }

  function handleDragEnter(agent: FrontlineAgent) {
    if (draggingId !== null && draggingId !== agent.id) setDragOverId(agent.id);
  }

  function handleDragLeave(agent: FrontlineAgent) {
    setDragOverId((id) => (id === agent.id ? null : id));
  }

  function handleDrop(e: DragEvent, targetAgent: FrontlineAgent) {
    e.preventDefault();
    setDragOverId(null);
    const draggedAgent = agents.find((a) => a.id === draggingId);
    setDraggingId(null);
    if (!draggedAgent || draggedAgent.id === targetAgent.id) return;
    setPendingSwap({ a: draggedAgent, b: targetAgent });
  }

  async function confirmSwap() {
    if (!pendingSwap) return;
    setSwapping(true);
    try {
      await api.swapFrontlineAgentShifts(pendingSwap.a.id, pendingSwap.b.id);
      setPendingSwap(null);
      onChanged();
    } finally {
      setSwapping(false);
    }
  }

  return (
    <div className="card card-lg">
      <div className="card-head">
        <div>
          <div className="card-title">Shift roster</div>
          <div className="card-sub">
            Source of truth for who's on shift -- the "On shift now" strip above is derived from this table.
          </div>
        </div>
        {!addingAgent && (
          <button className="table-toggle table-toggle-lg" onClick={() => setAddingAgent(true)} disabled={saving}>
            + Add agent
          </button>
        )}
      </div>

      {addingAgent && (
        <div className="fl-form" style={{ marginBottom: 12 }}>
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
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            disabled={saving}
          />
          <input
            className="select"
            value={slackId}
            onChange={(e) => setSlackId(e.target.value)}
            placeholder="Slack member ID (optional)"
            disabled={saving}
          />
          <button className="table-toggle" disabled={saving || !name.trim() || !email.trim()} onClick={addAgent}>
            Save
          </button>
          <button className="table-toggle" disabled={saving} onClick={() => setAddingAgent(false)}>
            Cancel
          </button>
        </div>
      )}

      {loading ? (
        <div className="skeleton" style={{ height: 220, width: "100%" }} />
      ) : agents.length === 0 ? (
        <div className="card-sub">No agents yet -- add one above.</div>
      ) : (
        <div className="shift-table-wrap">
          <table className="shift-table">
            <thead>
              <tr>
                <th>Day</th>
                {agents.map((agent) => (
                  <th
                    key={agent.id}
                    className={[
                      draggingId === agent.id ? "dragging" : "",
                      draggingId !== null && draggingId !== agent.id ? "drop-target" : "",
                      dragOverId === agent.id ? "drop-target-hover" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    onDragOver={(e) => handleDragOver(e, agent)}
                    onDragEnter={() => handleDragEnter(agent)}
                    onDragLeave={() => handleDragLeave(agent)}
                    onDrop={(e) => handleDrop(e, agent)}
                  >
                    {editingInfoId === agent.id ? (
                      <div className="agent-info-edit">
                        <input
                          className="select"
                          value={infoName}
                          onChange={(e) => setInfoName(e.target.value)}
                          placeholder="Name"
                          disabled={saving}
                        />
                        <input
                          className="select"
                          value={infoEmail}
                          onChange={(e) => setInfoEmail(e.target.value)}
                          placeholder="Email"
                          disabled={saving}
                        />
                        <input
                          className="select"
                          value={infoSlackId}
                          onChange={(e) => setInfoSlackId(e.target.value)}
                          placeholder="Slack member ID"
                          disabled={saving}
                        />
                        <span className="fl-actions">
                          <button
                            className="icon-btn"
                            onClick={saveInfo}
                            disabled={saving || !infoName.trim() || !infoEmail.trim()}
                            title="Save"
                          >
                            ✅
                          </button>
                          <button
                            className="icon-btn"
                            onClick={() => setEditingInfoId(null)}
                            disabled={saving}
                            title="Cancel"
                          >
                            ✖️
                          </button>
                        </span>
                      </div>
                    ) : (
                      <div className="agent-col-head">
                        <span
                          className={`agent-name ${canDrag ? "agent-name-draggable" : ""}`}
                          draggable={canDrag}
                          onDragStart={() => handleDragStart(agent)}
                          onDragEnd={() => setDraggingId(null)}
                          title={canDrag ? "Drag onto another agent to swap their shifts" : agent.name}
                        >
                          {agent.name}
                        </span>
                        {editingAgentId === agent.id ? (
                          <span className="fl-actions">
                            <button className="icon-btn" onClick={saveShifts} disabled={saving} title="Save">
                              ✅
                            </button>
                            <button
                              className="icon-btn"
                              onClick={() => setEditingAgentId(null)}
                              disabled={saving}
                              title="Cancel"
                            >
                              ✖️
                            </button>
                          </span>
                        ) : (
                          <span className="fl-actions">
                            <button
                              className="icon-btn"
                              onClick={() => startEditShifts(agent.id, agent.shifts)}
                              disabled={saving || anyEditing}
                              title="Edit shifts"
                            >
                              ✏️
                            </button>
                            <button
                              className="icon-btn"
                              onClick={() => startEditInfo(agent)}
                              disabled={saving || anyEditing}
                              title="Edit agent info"
                            >
                              🪪
                            </button>
                            <button
                              className="icon-btn"
                              onClick={() => removeAgent(agent.id)}
                              disabled={saving || anyEditing}
                              title="Remove agent"
                            >
                              🗑️
                            </button>
                          </span>
                        )}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {DAY_LABELS.map((label, day) => (
                <tr key={day}>
                  <td className="name-cell">{label}</td>
                  {agents.map((agent) => {
                    if (editingAgentId !== agent.id) {
                      const shift = agent.shifts.find((s) => s.day_of_week === day);
                      return (
                        <td key={agent.id}>
                          <ShiftCell shift={shift} />
                        </td>
                      );
                    }
                    const draft = draftShifts.find((s) => s.day_of_week === day)!;
                    const type = dayType(draft);
                    return (
                      <td key={agent.id}>
                        <div className="shift-cell-edit">
                          <select
                            className="select shift-day-type"
                            value={type}
                            onChange={(e) => setDraftDayType(day, e.target.value as DayType)}
                          >
                            <option value="working">Working</option>
                            <option value="week_off">Week off</option>
                            <option value="holiday">Holiday</option>
                          </select>
                          {type === "working" && (
                            <div className="shift-cell-edit-times">
                              <TimePickerDial
                                value={draft.start_time}
                                onChange={(v) => updateDraftDay(day, { start_time: v })}
                                placeholder="Start"
                              />
                              <span className="shift-cell-edit-sep">–</span>
                              <TimePickerDial
                                value={draft.end_time}
                                onChange={(v) => updateDraftDay(day, { end_time: v })}
                                placeholder="End"
                              />
                            </div>
                          )}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pendingSwap && (
        <div className="modal-backdrop" onClick={() => !swapping && setPendingSwap(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">Swap shifts?</div>
            <div className="modal-body">
              <strong>{pendingSwap.a.name}</strong> and <strong>{pendingSwap.b.name}</strong> will swap
              their entire weekly schedules (including week-offs and holidays). You can undo this by
              dragging them onto each other again.
            </div>
            <div className="modal-actions">
              <button className="table-toggle" onClick={() => setPendingSwap(null)} disabled={swapping}>
                Cancel
              </button>
              <button className="table-toggle time-picker-ok" onClick={confirmSwap} disabled={swapping}>
                {swapping ? "Swapping…" : "Swap"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
