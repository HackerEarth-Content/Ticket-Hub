# Handoff: IT Helpdesk Dashboard (HubSpot + Python + React)

## Project goal
Build a dashboard to monitor an IT/support helpdesk running on **HubSpot Tickets**. Needs:
- Live "today" status (open, new, resolved, breaching-soon counts)
- Overall KPIs + ticket-specific KPIs tied to SLA
- Summaries for previous day / week / month, plus current-day live view
- Visual distribution of tickets by module/category (bar, pie charts)

**Proposed stack:** Python for HubSpot API extraction → Postgres for storage → FastAPI backend (computes KPIs, cached in Redis) → React frontend (Recharts) polling every few minutes. See architecture diagram already generated earlier in this chat (title: `helpdesk_dashboard_architecture`) — not reproduced here, regenerate if needed.

## Real HubSpot data profile (from a 500-ticket sample pull)

### Pipelines (4 total, NOT unified)
- **Support Pipeline** (id=0) — 497/500 of sample (~99% of volume). 19 stages including multiple team-routing "Pending on X" states (BE/AE, Support, Engineering, Content, Programs, Finance) and separate bug-review stages.
- **GT Support Pipeline** (id=913510303) — 5 stages, minimal volume.
- **Customer Success** (id=38932318) — 5 stages, minimal volume.
- **Marketing Support** (id=23707277) — 4 stages, no volume in sample.

**Critical issue:** stage IDs are NOT shared across pipelines (e.g. "New" = `54370401` in Support but `1388840362` in GT Support). Any status chart requires a **canonical status mapping table** (config, not hardcoded) collapsing each pipeline's stages into: New, Open, Pending, Closing, Resolved. This mapping needs to be built out per-pipeline (Support Pipeline's mapping was drafted in this conversation).

### Data quality findings
- **Priority (`hs_ticket_priority`)**: 78% blank (389/500). Only MEDIUM/HIGH/LOW/URGENT populated on the rest. → Needs derivation (see below).
- **Category (`hs_ticket_category`)**: 25.6% blank (128/500), stored as **semicolon-joined multi-select free text** (e.g. `"Test Access;Proctoring B2C;Result enquiry"`). Must be split on `;` before counting or pie chart will show ~70 tiny slices. Long tail of one-off combos — bucket top 10-12 into named slices, rest into "Other."
- **`hs_resolution`**: 100% blank in sample. **Drop from MVP.**
- **`hs_ticket_type`**: 100% blank in sample. **Drop from MVP.**
- **No SLA/timestamp properties** (first-response time, time-to-close, SLA due date) appeared in the property list pulled so far — **unconfirmed whether this is a missing-from-extraction issue or HubSpot's native SLA/Service Hub feature is simply not enabled on this portal.** This is the single most important open question — see "Open questions" below.
- Sample was pulled by recency (~97% Closed/Solved) — a "live open tickets" view needs an explicitly filtered query (stage not in closed/solved set), not a general recency pull, or the live dashboard will look empty.

### Properties currently pulled
`createdate`, `hs_lastmodifieddate`, `hs_object_id`, `hs_pipeline`, `hs_pipeline_stage`, `hs_resolution`, `hs_ticket_category`, `hs_ticket_priority`, `subject`

### Properties to ADD to extraction
- `closedate` — required for MTTR/resolution-time calculations
- `hubspot_owner_id` — required for any agent-level KPI
- HubSpot native SLA calculated properties, IF the portal has SLA/Service Hub enabled (e.g. `hs_time_to_first_agent_reply_wait_time_calculated`, breach flags) — **needs verification**
- CSAT property, IF post-resolution survey feature is enabled on this portal — **needs verification**
- Ticket source/channel property — existence not yet confirmed in this portal, needs checking

## Derived priority (to fill the 78% gap)
Proposed rule-based inference layer (to be built in Python ETL, kept as a **separate `derived_priority` field** — never overwrite the real `hs_ticket_priority`, and tag inferred rows with `inferred: true`):

Rule order (first match wins):
1. Keyword in subject line (`URGENT`, `CRITICAL`, `DOWN`, `[P1]`) → HIGH/URGENT
2. Category-based default (platform is a testing/hiring product, so live/time-boxed categories skew higher):
   - HIGH: Test Loading Issues, Unable to Login, Login issues, Webcam, Audio/Video Issue, IDE/Compiler, Proctoring B2C
   - MEDIUM: Submission Related, Test Access, Dashboard Issues, Result enquiry, Team Management
   - LOW: Sales Enquiry, Contest Info, Registration Related, Spam, Not Actionable, No Action Required
3. Stage-based signal: tickets in "Bugs pending on Backline/AE" or "Bugs pending on QA/Platform" → at least MEDIUM
4. Fallback: MEDIUM, `inferred: true`

This is a stopgap — the real fix is making priority a required field in HubSpot ticket creation (workflow validation), flagged as a parallel workstream to whoever owns HubSpot config.

## KPI feasibility (latest requested list: Uptime, MTTR, First Response Time, SLA Breach Rate, CSAT, Error Rates)

| KPI | Feasible from HubSpot tickets? | Dependency |
|---|---|---|
| Service Availability (Uptime %) | **No — wrong data source.** Ticket volume is a noisy proxy for infra uptime | Needs external monitoring feed (Pingdom, Datadog, StatusPage) — separate pipeline, out of scope for this dashboard unless explicitly extended |
| MTTR by severity (P1 vs P3 etc.) | **Yes**, once `closedate` is pulled and priority is populated (real or derived) | `closedate - createdate` grouped by priority |
| First Response Time | **Conditional** | Depends on whether native HubSpot SLA/Service Hub is enabled on this portal — check Settings → Objects → Tickets → SLA |
| SLA Breach Rate | **Conditional**, same dependency | If SLA enabled, pull HubSpot's calculated breach properties directly. If not, must define an SLA matrix against derived priority + created date and compute breach manually — heavier lift given priority is only 22% real today |
| CSAT | **Conditional** | Requires HubSpot's post-resolution survey feature (Service Hub) to be enabled; no way to back-derive from ticket metadata if it's off |
| Error Rates | **No — wrong data source.** This is a DevOps/app-stability metric, not a helpdesk metric | Closest ticket-side proxy: % tickets tagged Bug/Loading Issue/Compiler-related (volume signal only, not true error rate). Real error rates need Sentry/Datadog/log aggregator, separate pipeline |

**Net scope call to make:** Uptime and Error Rates likely don't belong in this dashboard as first-class KPIs — they need a different data source entirely. Recommend either dropping them or explicitly scoping this as a future two-source dashboard (HubSpot + a monitoring API).

## Open questions blocking next steps (need answers from whoever owns the HubSpot portal)
1. **Is HubSpot's native SLA/Service Hub feature enabled?** (Settings → Objects → Tickets → SLA) — determines whether First Response Time / SLA Breach Rate come free as calculated properties or need to be built from scratch.
2. **Is the post-resolution CSAT survey enabled?** — determines whether CSAT is pullable at all right now.
3. **Does a ticket source/channel property exist** in this portal's custom properties?
4. **Confirm/refine the category → module grouping** drafted in this conversation (Assessment/Testing, Proctoring, Interviews, Account/Access, Contests/Events, Sales, Content/Platform) with the support team before hardcoding it.
5. **Confirm the canonical status mapping** for GT Support, Customer Success, and Marketing Support pipelines (only Support Pipeline's mapping was drafted so far).

## Revised KPI/dashboard scope given all findings
**Build now:** live open/pending/new counts (via explicitly filtered non-closed query), daily/weekly/monthly volume trend, category distribution (post `;`-split normalization), pipeline/stage distribution (via canonical mapping), MTTR by derived priority (once `closedate` added), data-quality KPIs (% priority unset, % category blank, % tickets stuck >48h in a "Pending on X" stage — useful bottleneck signal by team).

**Build once portal settings are confirmed:** First Response Time, SLA Breach Rate, CSAT, agent-level KPIs (once `hubspot_owner_id` is pulled).

**Do not build in this dashboard:** Uptime %, Error Rates (wrong data source — flag as separate monitoring integration if wanted later). Anything based on `hs_resolution` or `hs_ticket_type` (100% empty currently).

## Next concrete steps (pick up here)
1. Get answers to the 5 open questions above.
2. Build the Python `derived_priority` rule engine.
3. Build the canonical status-mapping config (JSON/dict) for all 4 pipelines.
4. Update HubSpot extraction script to pull `closedate`, `hubspot_owner_id`, and SLA/CSAT properties if confirmed available.
5. Draft Postgres schema (`tickets_raw`, `daily_snapshot` tables) — not yet built in this conversation, was offered as a next step.
