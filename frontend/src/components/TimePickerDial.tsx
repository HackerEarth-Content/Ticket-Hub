import { useEffect, useRef, useState } from "react";

const DIAL_SIZE = 232;
const CENTER = DIAL_SIZE / 2;
const NUMBER_RADIUS = 92;

function parseValue(value: string | null): { hour12: number; minute: number; period: "AM" | "PM" } {
  if (!value) return { hour12: 9, minute: 0, period: "AM" };
  const [h, m] = value.split(":").map(Number);
  const period: "AM" | "PM" = h >= 12 ? "PM" : "AM";
  const hour12 = h % 12 || 12;
  return { hour12, minute: m, period };
}

function toValue(hour12: number, minute: number, period: "AM" | "PM"): string {
  const h24 = period === "AM" ? (hour12 === 12 ? 0 : hour12) : hour12 === 12 ? 12 : hour12 + 12;
  return `${String(h24).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function pointToSteps(clientX: number, clientY: number, rect: DOMRect, steps: number): number {
  const dx = clientX - (rect.left + rect.width / 2);
  const dy = clientY - (rect.top + rect.height / 2);
  const deg = (Math.atan2(dx, -dy) * 180) / Math.PI;
  const norm = ((deg % 360) + 360) % 360;
  return Math.round(norm / (360 / steps)) % steps;
}

function posForStep(step: number, steps: number, radius: number): { x: number; y: number } {
  const rad = (step * (360 / steps) * Math.PI) / 180;
  return { x: CENTER + radius * Math.sin(rad), y: CENTER - radius * Math.cos(rad) };
}

interface Props {
  value: string | null; // "HH:MM" 24h, or null
  onChange: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

/** A Material-style clock-dial time picker: pick the hour on a 12-position
 * dial, then the minute on a 60-position one, either by clicking a number or
 * dragging the hand -- a real clock face instead of a native <input
 * type="time">'s inline spinner. */
export function TimePickerDial({ value, onChange, disabled, placeholder = "Set time" }: Props) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"hour" | "minute">("hour");
  const [draft, setDraft] = useState(() => parseValue(value));
  const dialRef = useRef<HTMLDivElement>(null);
  const draggingRef = useRef(false);

  useEffect(() => {
    if (open) setDraft(parseValue(value));
    setMode("hour");
  }, [open, value]);

  function applyFromPointer(clientX: number, clientY: number) {
    const rect = dialRef.current?.getBoundingClientRect();
    if (!rect) return;
    if (mode === "hour") {
      const step = pointToSteps(clientX, clientY, rect, 12);
      setDraft((d) => ({ ...d, hour12: step === 0 ? 12 : step }));
    } else {
      const step = pointToSteps(clientX, clientY, rect, 60);
      setDraft((d) => ({ ...d, minute: step }));
    }
  }

  function onPointerDown(e: React.PointerEvent) {
    (e.target as Element).setPointerCapture(e.pointerId);
    draggingRef.current = true;
    applyFromPointer(e.clientX, e.clientY);
  }
  function onPointerMove(e: React.PointerEvent) {
    if (!draggingRef.current) return;
    applyFromPointer(e.clientX, e.clientY);
  }
  function onPointerUp() {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    if (mode === "hour") setMode("minute");
  }

  function confirm() {
    onChange(toValue(draft.hour12, draft.minute, draft.period));
    setOpen(false);
  }

  const displayValue = value ? (() => {
    const { hour12, minute, period } = parseValue(value);
    return `${hour12}:${String(minute).padStart(2, "0")} ${period}`;
  })() : null;

  const handStep = mode === "hour" ? (draft.hour12 % 12) : draft.minute;
  const handSteps = mode === "hour" ? 12 : 60;
  const handEnd = posForStep(handStep, handSteps, NUMBER_RADIUS);

  return (
    <>
      <button
        type="button"
        className="time-picker-trigger"
        onClick={() => setOpen(true)}
        disabled={disabled}
      >
        {displayValue ?? placeholder}
      </button>

      {open && (
        <div className="time-picker-backdrop" onClick={() => setOpen(false)}>
          <div className="time-picker-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="time-picker-display">
              <button
                type="button"
                className={`time-picker-display-part ${mode === "hour" ? "active" : ""}`}
                onClick={() => setMode("hour")}
              >
                {String(draft.hour12).padStart(2, "0")}
              </button>
              <span className="time-picker-colon">:</span>
              <button
                type="button"
                className={`time-picker-display-part ${mode === "minute" ? "active" : ""}`}
                onClick={() => setMode("minute")}
              >
                {String(draft.minute).padStart(2, "0")}
              </button>
              <div className="time-picker-period">
                <button
                  type="button"
                  className={draft.period === "AM" ? "active" : ""}
                  onClick={() => setDraft((d) => ({ ...d, period: "AM" }))}
                >
                  AM
                </button>
                <button
                  type="button"
                  className={draft.period === "PM" ? "active" : ""}
                  onClick={() => setDraft((d) => ({ ...d, period: "PM" }))}
                >
                  PM
                </button>
              </div>
            </div>

            <div
              className="time-picker-dial"
              ref={dialRef}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
            >
              <svg width={DIAL_SIZE} height={DIAL_SIZE}>
                <circle cx={CENTER} cy={CENTER} r={CENTER} className="time-picker-face" />
                <line
                  x1={CENTER}
                  y1={CENTER}
                  x2={handEnd.x}
                  y2={handEnd.y}
                  className="time-picker-hand"
                />
                <circle cx={CENTER} cy={CENTER} r={3} className="time-picker-hub" />
                <circle cx={handEnd.x} cy={handEnd.y} r={16} className="time-picker-knob" />
              </svg>
              {(mode === "hour" ? [12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11] : [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]).map(
                (n, i) => {
                  const pos = posForStep(i, 12, NUMBER_RADIUS);
                  const selected = mode === "hour" ? draft.hour12 === n || (n === 12 && draft.hour12 === 12) : draft.minute === n;
                  return (
                    <span
                      key={n}
                      className={`time-picker-number ${selected ? "selected" : ""}`}
                      style={{ left: pos.x, top: pos.y }}
                    >
                      {mode === "minute" ? String(n).padStart(2, "0") : n}
                    </span>
                  );
                },
              )}
            </div>

            <div className="time-picker-actions">
              <button type="button" className="table-toggle" onClick={() => setOpen(false)}>
                Cancel
              </button>
              <button type="button" className="table-toggle time-picker-ok" onClick={confirm}>
                OK
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
