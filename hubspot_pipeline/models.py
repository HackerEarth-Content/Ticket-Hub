"""Ticket data model for the dashboard extraction pipeline."""

from __future__ import annotations

import html
import re
from typing import Any

from pydantic import BaseModel

from hubspot_pipeline.category_map import resolve_module, split_categories
from hubspot_pipeline.customer_map import resolve_customer_name
from hubspot_pipeline.priority import derive_priority
from hubspot_pipeline.resolution_map import is_actionable, resolve_resolution_bucket
from hubspot_pipeline.stage_timing import STAGE_TIMING_STAGES, resolve_backline_path
from hubspot_pipeline.status_map import resolve_status

# hs_time_to_first_response_sla_status / hs_time_to_close_sla_status enum codes
_SLA_STATUS_LABELS = {
    "0": "Active SLA",
    "1": "Overdue",
    "2": "Due Soon",
    "3": "Completed on time",
    "4": "Completed late",
}

_MS_PER_HOUR = 3_600_000


def _ms_to_hours(raw: str | None) -> float | None:
    """time_to_close / time_to_first_agent_reply / hs_time_to_first_rep_assignment
    are raw millisecond durations (verified against live ticket samples,
    2026-07-04) -- convert to hours for consistency with every other duration
    in this model."""
    if raw is None or raw == "":
        return None
    return round(float(raw) / _MS_PER_HOUR, 2)


def _to_bool(raw: str | None) -> bool | None:
    """fcr is a booleancheckbox property, serialized as the strings 'true'/'false'."""
    if raw is None or raw == "":
        return None
    return raw == "true"


def _sla_met(raw: str | None) -> bool | None:
    """sla_percentage is misleadingly named -- live samples only ever show
    '0', '1', or blank, i.e. it's an SLA-met flag, not a percentage."""
    if raw is None or raw == "":
        return None
    return raw == "1"


def _unescape(value: str | None) -> str | None:
    """HubSpot ticket properties sometimes arrive already HTML-entity-encoded
    (e.g. "Tom &amp; Jerry&#39;s") from whatever created the ticket -- HubSpot
    stores and returns the string as-is, it doesn't decode on read. Undo that
    once here, at ingestion, so every downstream reader (export, dashboard,
    frontend) sees the real character."""
    return html.unescape(value) if value else value


_REPORTED_BY_RE = re.compile(r"^Reported By:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def _extract_reported_by(content: str | None) -> str | None:
    """Slack-sourced tickets embed "Reported By: <name>" as the first line
    of their description (verified live 2026-07-07, 14/15 tickets) -- far
    more reliable than the associated-contact rollup, which is blank for
    those same 14/15."""
    if not content:
        return None
    match = _REPORTED_BY_RE.search(content)
    if not match:
        return None
    return match.group(1).strip() or None


_WORKFLOW_RE = re.compile(r"^Workflow:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def _extract_workflow(content: str | None) -> str | None:
    """Newer Slack-sourced tickets embed a "Workflow: <type>" line before
    "Reported By:" (e.g. "Content Request - Assessments 1.0", "engg oncall")
    -- verified live 2026-07-09. Older Slack tickets predate this field and
    have no such line; None here means "not tagged", not "no workflow"."""
    if not content:
        return None
    match = _WORKFLOW_RE.search(content)
    if not match:
        return None
    return match.group(1).strip() or None


_CHANNEL_RE = re.compile(r"^Channel:\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def _extract_channel(content: str | None) -> str | None:
    """Slack-sourced tickets may embed a "Channel: <name>" line alongside
    "Workflow:"/"Reported By:" (e.g. "engg-assessment", "#content-programs").
    Normalized to a bare lowercase name. None means "not tagged".
    ponytail: unverified against live content (DB down 2026-07-16) -- if live
    tickets carry no Channel line, everything lands in the Unknown bucket and
    this regex needs adjusting to whatever the real line looks like."""
    if not content:
        return None
    match = _CHANNEL_RE.search(content)
    if not match:
        return None
    value = match.group(1).strip().lstrip("#").lower()
    return value or None


class DashboardTicket(BaseModel):
    """A HubSpot ticket normalized for dashboard KPIs/charts."""

    ticket_id: str
    subject: str
    pipeline_id: str
    pipeline_label: str
    stage_id: str
    stage_label: str
    canonical_status: str

    categories: list[str]
    primary_category: str | None
    module: str
    hubspot_module: (
        str | None
    )  # HubSpot's own "module" dropdown -- see client.py's comment
    sub_category: str | None
    customer_name: str | None
    # event_name is a single-select dropdown with an "others" catch-all
    # option -- left as the raw value here (including the literal "others"),
    # so every ticket picking it groups into one dropdown entry instead of
    # fragmenting across other_event_name's inconsistent free text. The real
    # per-ticket text still lives in other_event_name, for the export report.
    event_name: str | None
    other_event_name: str | None

    priority: str | None  # real hs_ticket_priority, None if blank
    derived_priority: str
    priority_inferred: bool

    owner_id: str | None
    owner_name: str | None
    owner_assigned_at: str | None  # hubspot_owner_assigneddate, ISO string
    source_type: str | None
    record_source: (
        str | None
    )  # hs_object_source -- e.g. CRM_UI/CONVERSATIONS/IMPORT/BOT
    reporter_contact_name: (
        str | None
    )  # parsed from ticket content, see _extract_reported_by
    slack_workflow: str | None  # parsed from ticket content, see _extract_workflow
    slack_channel: str | None  # parsed from ticket content, see _extract_channel

    created_at: str | None  # createdate, ISO string
    closed_at: str | None  # closed_date, ISO string
    last_modified_at: str | None  # hs_lastmodifieddate, ISO string

    sla_first_response_status: str | None
    sla_close_status: str | None
    sla_met: bool | None

    final_resolution: str | None
    resolution_bucket: str
    actionable: bool
    fcr: bool | None
    backline_engineer: str | None
    backline_path: str | None
    jira_link: str | None

    time_to_close_hours: float | None
    time_to_first_agent_reply_hours: float | None
    time_to_first_rep_assignment_hours: float | None

    # stage_key -> {entered_at, exited_at, cumulative_hours}, for the 4
    # backline escalation stages (see stage_timing.STAGE_TIMING_STAGES).
    stage_timings: dict[str, dict[str, Any]]

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        pipelines: dict[str, dict],
        owners: dict[str, str] | None = None,
    ) -> "DashboardTicket":
        props = raw.get("properties", {})
        pipeline_id = props.get("hs_pipeline") or ""
        stage_id = props.get("hs_pipeline_stage") or ""
        pipeline = pipelines.get(pipeline_id, {})
        stage_label = pipeline.get("stages", {}).get(stage_id, stage_id or "—")
        owner_id = props.get("hubspot_owner_id") or None

        categories = split_categories(props.get("hs_ticket_category"))
        subject = _unescape(props.get("subject")) or ""
        raw_priority = props.get("hs_ticket_priority") or None
        derived, inferred = derive_priority(
            raw_priority, subject, categories, stage_label
        )

        final_resolution = props.get("final_resolution") or None
        source_type = props.get("source_type") or None
        record_source = props.get("hs_object_source") or None

        stage_timings = {
            stage_key: {
                "entered_at": props.get(f"hs_v2_date_entered_{stage['stage_id']}")
                or None,
                "exited_at": props.get(f"hs_v2_date_exited_{stage['stage_id']}")
                or None,
                "cumulative_hours": _ms_to_hours(
                    props.get(f"hs_v2_cumulative_time_in_{stage['stage_id']}")
                ),
            }
            for stage_key, stage in STAGE_TIMING_STAGES.items()
        }

        return cls(
            ticket_id=raw.get("id", ""),
            subject=subject,
            pipeline_id=pipeline_id,
            pipeline_label=pipeline.get("label", pipeline_id or "—"),
            stage_id=stage_id,
            stage_label=stage_label,
            canonical_status=resolve_status(pipeline_id, stage_id),
            categories=categories,
            primary_category=categories[0] if categories else None,
            module=resolve_module(categories),
            hubspot_module=props.get("module") or None,
            sub_category=props.get("sub_category") or None,
            customer_name=_unescape(resolve_customer_name(props)),
            event_name=props.get("event_name") or None,
            other_event_name=_unescape(props.get("other_event_name")) or None,
            priority=raw_priority,
            derived_priority=derived,
            priority_inferred=inferred,
            owner_id=owner_id,
            owner_name=(owners or {}).get(owner_id) if owner_id else None,
            owner_assigned_at=props.get("hubspot_owner_assigneddate"),
            source_type=source_type,
            record_source=record_source,
            # Slack-only: the "Reported By:" line is a convention of the
            # Slack ticket-creation flow, not a general description format --
            # extracting it from other sources' descriptions would be noise,
            # not signal.
            reporter_contact_name=(
                _unescape(_extract_reported_by(props.get("content")))
                if source_type == "Slack"
                else None
            ),
            slack_workflow=(
                _extract_workflow(props.get("content"))
                if source_type == "Slack"
                else None
            ),
            slack_channel=(
                _extract_channel(props.get("content"))
                if source_type == "Slack"
                else None
            ),
            created_at=props.get("createdate"),
            closed_at=props.get("closed_date"),
            last_modified_at=props.get("hs_lastmodifieddate"),
            sla_first_response_status=_SLA_STATUS_LABELS.get(
                props.get("hs_time_to_first_response_sla_status") or ""
            ),
            sla_close_status=_SLA_STATUS_LABELS.get(
                props.get("hs_time_to_close_sla_status") or ""
            ),
            sla_met=_sla_met(props.get("sla_percentage")),
            final_resolution=final_resolution,
            resolution_bucket=resolve_resolution_bucket(final_resolution),
            actionable=is_actionable(final_resolution),
            fcr=_to_bool(props.get("fcr")),
            backline_engineer=props.get("backline_engineer") or None,
            backline_path=resolve_backline_path(stage_timings),
            jira_link=props.get("jira_link") or None,
            time_to_close_hours=_ms_to_hours(props.get("time_to_close")),
            time_to_first_agent_reply_hours=_ms_to_hours(
                props.get("time_to_first_agent_reply")
            ),
            time_to_first_rep_assignment_hours=_ms_to_hours(
                props.get("hs_time_to_first_rep_assignment")
            ),
            stage_timings=stage_timings,
        )


class CsatSubmission(BaseModel):
    """An email CSAT survey response (HubSpot Feedback Submissions, survey
    "Customer Satisfaction Survey - Support") normalized for storage.

    ticket_id/owner_id/owner_name are filled in by pipeline._match_ticket,
    not by HubSpot -- the object only associates to the contact who
    responded, never to a ticket."""

    submission_id: str
    rating: int  # 0=Detractor, 1=Passive, 2=Promoter -- confirmed via hs_response_group
    submitted_at: str
    contact_id: str | None
    ticket_id: str | None
    owner_id: str | None
    owner_name: str | None

    @classmethod
    def from_raw(
        cls,
        raw: dict[str, Any],
        contact_id: str | None,
        ticket_id: str | None,
        owner_id: str | None,
        owner_name: str | None,
    ) -> "CsatSubmission":
        props = raw.get("properties", {})
        return cls(
            submission_id=raw["id"],
            rating=int(props["hs_value"]),
            submitted_at=props["hs_submission_timestamp"],
            contact_id=contact_id,
            ticket_id=ticket_id,
            owner_id=owner_id,
            owner_name=owner_name,
        )
