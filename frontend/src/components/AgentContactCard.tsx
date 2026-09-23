import type { ReactNode } from "react";

interface Props {
  name: string;
  email: string;
  phone?: string | null;
  placement?: "top" | "bottom";
  children: ReactNode;
}

function MailIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="2.5" y="4.5" width="19" height="15" rx="2.5" />
      <path d="m3 6.5 9 6.5 9-6.5" />
    </svg>
  );
}

function PhoneIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6.5 3.5h3l1.5 4-2 1.5a11 11 0 0 0 5.5 5.5l1.5-2 4 1.5v3a2 2 0 0 1-2.2 2A17 17 0 0 1 4.5 5.7a2 2 0 0 1 2-2.2Z" />
    </svg>
  );
}

/** A small hover card of an agent's contact details, anchored to whatever
 * trigger it wraps (their name). Pure CSS show/hide (:hover/:focus-within in
 * App.css) so it works the same everywhere it's used, without each caller
 * re-implementing tooltip positioning. */
export function AgentContactCard({ name, email, phone, placement = "top", children }: Props) {
  return (
    <span className="agent-contact" tabIndex={0}>
      {children}
      <span className={`agent-contact-card agent-contact-card-${placement}`} role="tooltip">
        <span className="agent-contact-name">{name}</span>
        <span className="agent-contact-row">
          <MailIcon />
          {email}
        </span>
        {phone && (
          <span className="agent-contact-row">
            <PhoneIcon />
            {phone}
          </span>
        )}
      </span>
    </span>
  );
}
