"""Ticket data model for the dashboard extraction pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from hubspot_pipeline.category_map import resolve_module, split_categories
from hubspot_pipeline.priority import derive_priority
from hubspot_pipeline.status_map import resolve_status

# hs_time_to_first_response_sla_status / hs_time_to_close_sla_status enum codes
_SLA_STATUS_LABELS = {
    "0": "Active SLA",
    "1": "Overdue",
    "2": "Due Soon",
    "3": "Completed on time",
    "4": "Completed late",
}


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

    priority: str | None          # real hs_ticket_priority, None if blank
    derived_priority: str
    priority_inferred: bool

    owner_id: str | None
    owner_name: str | None
    source_type: str | None

    created_at: str | None        # createdate, ISO string
    closed_at: str | None         # closed_date, ISO string
    last_modified_at: str | None  # hs_lastmodifieddate, ISO string

    sla_first_response_status: str | None
    sla_close_status: str | None
    csat_rating: str | None

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
        subject = props.get("subject") or ""
        raw_priority = props.get("hs_ticket_priority") or None
        derived, inferred = derive_priority(raw_priority, subject, categories, stage_label)

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
            priority=raw_priority,
            derived_priority=derived,
            priority_inferred=inferred,
            owner_id=owner_id,
            owner_name=(owners or {}).get(owner_id) if owner_id else None,
            source_type=props.get("source_type") or None,
            created_at=props.get("createdate"),
            closed_at=props.get("closed_date"),
            last_modified_at=props.get("hs_lastmodifieddate"),
            sla_first_response_status=_SLA_STATUS_LABELS.get(
                props.get("hs_time_to_first_response_sla_status") or ""
            ),
            sla_close_status=_SLA_STATUS_LABELS.get(
                props.get("hs_time_to_close_sla_status") or ""
            ),
            csat_rating=props.get("hs_last_csat_rating") or None,
        )
