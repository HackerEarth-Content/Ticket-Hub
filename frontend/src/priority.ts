// Severity order, most severe first -- descending so "Urgent" always leads.
export const PRIORITY_ORDER = ["URGENT", "HIGH", "MEDIUM", "LOW"];

// Support's P-level equivalent for each derived priority, shown alongside
// the bucket name since that's the scale the team actually pages on.
export const P_LABEL: Record<string, string> = {
  URGENT: "P0",
  HIGH: "P1",
  MEDIUM: "P2",
  LOW: "P3/P4",
};

export function priorityDisplay(p: string): string {
  return P_LABEL[p] ? `${p} (${P_LABEL[p]})` : p;
}
