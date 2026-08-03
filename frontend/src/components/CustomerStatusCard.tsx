import type { CustomerStatusBreakdown } from "../types";
import { StackedBreakdownCard } from "./StackedBreakdownCard";

interface Props {
  data: CustomerStatusBreakdown | null;
  loading: boolean;
  showAll: boolean;
}

export function CustomerStatusCard({ data, loading, showAll }: Props) {
  return (
    <StackedBreakdownCard
      title="Status by customer"
      sub={
        showAll
          ? "Where every identified account's tickets stand this period"
          : "Where each top account's tickets stand this period"
      }
      customers={(showAll ? data?.all_customers : data?.customers) ?? []}
      loading={loading || !data}
      countsKey="status_counts"
      drilldownKey="stage_counts"
      drilldownLabel="stage"
    />
  );
}
