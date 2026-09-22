import type { OnShiftAgent } from "../types";

interface Props {
  agents: OnShiftAgent[];
  loading: boolean;
}

function MailIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2.5" y="4.5" width="19" height="15" rx="2.5" />
      <path d="m3 6.5 9 6.5 9-6.5" />
    </svg>
  );
}

function SlackIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M7 13a2 2 0 1 1 2-2v2H7Z" />
      <path d="M13 7a2 2 0 1 1 2 2h-2V7Z" />
      <path d="M17 11a2 2 0 1 1-2 2v-2h2Z" />
      <path d="M11 17a2 2 0 1 1-2-2h2v2Z" />
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
              <span className="active-agent-name">{agent.name}</span>
              <a
                className="icon-btn"
                href={`https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(agent.email)}`}
                target="_blank"
                rel="noreferrer"
                title={`Email ${agent.name}`}
              >
                <MailIcon />
              </a>
              {agent.slack_id && (
                <a
                  className="icon-btn"
                  href={`https://slack.com/app_redirect?channel=${agent.slack_id}`}
                  target="_blank"
                  rel="noreferrer"
                  title={`Slack ${agent.name}`}
                >
                  <SlackIcon />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
