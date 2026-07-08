# Product

## Register

product

## Users

Support/ops team members, team leads, and managers at HackerEarth who monitor
HubSpot support tickets day-to-day. They check this during work hours, often
under time pressure (an active incident, an SLA about to breach, a daily
stand-up), and need to go from "what's the state of things" to "which ticket
needs attention" in seconds. Some views (org-wide KPIs, CSAT, customer
health) are open to anyone; per-agent and escalation detail is gated behind
sign-in for the team itself.

## Product Purpose

Give HackerEarth's support organization a single live view of ticket volume,
SLA compliance, CSAT, agent workload, backline escalations, customer health,
and Slack-reported content/on-call requests — replacing manual HubSpot
report-building with a dashboard that auto-syncs every 5 minutes and answers
"how are we doing right now" without anyone touching HubSpot directly.

## Brand Personality

Sharp, modern, confident — but data-first, not decorative. The team trusts
this dashboard to be accurate before they trust it to be pretty; polish
should read as precision (tight alignment, considered color, fast scanning),
not as flourish. No flashy chrome competing with the numbers.

## Anti-references

- Generic Bootstrap-style admin templates (boxy, dated, low information
  density).
- Decorative gradients, glassmorphism, or gradient text — this is an ops
  tool, not a marketing page.
- Any chart or card that hides uncertainty for the sake of looking clean —
  this dashboard already has a convention of surfacing data-quality caveats
  (e.g. "N responses couldn't be matched to a ticket") rather than papering
  over them; visual polish should not undo that honesty.

## Design Principles

- **One glance, one answer.** Every card or table answers a single question
  clearly; detail lives one click away (drill-downs), not crammed into the
  summary view.
- **Fixed, consistent color identity.** Categorical color order is assigned
  once and never cycles or gets reassigned by value (already established
  across module/source/reporter charts) — the reader learns the palette once.
- **Fast to scan under pressure.** Numbers and status lead; labels and
  chrome recede. A support lead should get "today's state" in seconds.
- **Honest about gaps.** Data-quality caveats (unmatched CSAT, inferred
  priority, fallback reporter names) stay visible, not hidden for cleanliness.
- **Sign-in changes scope, not trust.** Signed-out users get the full
  org-wide picture; sign-in unlocks per-agent/escalation detail, not a
  "better" version of the same data.

## Accessibility & Inclusion

WCAG AA contrast minimum throughout. Categorical charts use a fixed,
colorblind-safe hue order (already validated for this app) with a legend
always present for 2+ series — color is never the only way to distinguish
categories. No accessibility requirements beyond standard good practice.
