import type { CustomerDetails } from "../types";
import { StackedBreakdownCard } from "./StackedBreakdownCard";

interface Props {
  data: CustomerDetails | null;
  loading: boolean;
}

/** Who actually resolves each account's tickets -- frontline support,
 * backline engineering, automation, etc (resolution_bucket). Priority mix
 * rides along as the drilldown since it's the other "what kind of tickets
 * does this account raise" signal, same shape as status/stage above. */
export function CustomerResolverCard({ data, loading }: Props) {
  return (
    <StackedBreakdownCard
      title="Who's resolving it"
      sub="Resolution ownership per top account this period"
      customers={data?.customers ?? []}
      loading={loading || !data}
      countsKey="resolution_bucket_counts"
      drilldownKey="priority_counts"
      drilldownLabel="priority"
    />
  );
}
