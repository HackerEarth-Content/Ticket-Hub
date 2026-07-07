import type { CustomerStatusBreakdown } from "../types";
import { StackedBreakdownCard } from "./StackedBreakdownCard";

interface Props {
  data: CustomerStatusBreakdown | null;
  loading: boolean;
}

export function CustomerStatusCard({ data, loading }: Props) {
  return (
    <StackedBreakdownCard
      title="Status by customer"
      sub="Where each top account's tickets stand this period"
      customers={data?.customers ?? []}
      loading={loading || !data}
      countsKey="status_counts"
      drilldownKey="stage_counts"
      drilldownLabel="stage"
    />
  );
}
