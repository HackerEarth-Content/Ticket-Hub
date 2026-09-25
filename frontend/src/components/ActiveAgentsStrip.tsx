import type { OnShiftAgent } from "../types";
import { AgentContactCard } from "./AgentContactCard";

interface Props {
  agents: OnShiftAgent[];
  loading: boolean;
}

// The channel dedicated to internal comms with the support agents --
// support-productsales.
const SUPPORT_SLACK_CHANNEL_ID = "C09E8TJ49GA";

function WarningIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="7.5" x2="12" y2="13.5" />
      <circle cx="12" cy="17" r="0.5" fill="currentColor" />
    </svg>
  );
}

/** Lives inside the same live-updates panel as the stat-tile strip, right
 * below it -- one unified "live" card instead of a second stacked box.
 * `agents` is already filtered to "on shift right now" server-side (see
 * useOnShiftNow) -- this component only renders, it doesn't decide who's
 * active, so it never needs the full roster or anyone's schedule. */
export function ActiveAgentsStrip({ agents, loading }: Props) {
  if (loading) return null;

  return (
    <div className="active-agents-row">
      <span className="active-agents-label">On shift now</span>
      {agents.length === 0 ? (
        <span className="active-agents-empty">No agent's shift covers this hour right now.</span>
      ) : (
        <div className="active-agents-list">
          {agents.map((agent) => (
            <div key={agent.id} className="active-agent-chip">
              <AgentContactCard name={agent.name} email={agent.email} phone={agent.phone}>
                <span className="active-agent-name">{agent.name}</span>
              </AgentContactCard>
            </div>
          ))}
        </div>
      )}
      <div className="active-agents-notes">
        <div className="active-agents-note">
          <WarningIcon />
          <span>Please write to support@hackerearth.com for any support-related queries.</span>
        </div>
        <div className="active-agents-note">
          <WarningIcon />
          <span>
            Please use the slack channel{" "}
            <a
              href={`https://slack.com/app_redirect?channel=${SUPPORT_SLACK_CHANNEL_ID}`}
              target="_blank"
              rel="noreferrer"
            >
              support-productsales
            </a>{" "}
            for any internal communication with the support agents.
          </span>
        </div>
      </div>
    </div>
  );
}
