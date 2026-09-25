// HubSpot's ticket_validity stores "Valid"/"Invalid", not the "Valid Issue"/
// "Invalid Issue" labels shown in HubSpot's UI -- the other three options'
// stored values match their labels exactly.
export const VALIDITY_ORDER = ["Valid", "Invalid", "Service Request", "Data Request", "Feature Request"];

// Sentinel for a null/missing ticket_validity -- distinct from any real
// HubSpot value, used as both the filter's option value and the display
// label for individual rows.
export const VALIDITY_NOT_SET = "not_set";

const VALIDITY_LABEL: Record<string, string> = {
  Valid: "Valid Issue",
  Invalid: "Invalid Issue",
  [VALIDITY_NOT_SET]: "Not yet categorized",
};

export function validityDisplay(v: string | null): string {
  if (v == null) return VALIDITY_LABEL[VALIDITY_NOT_SET];
  return VALIDITY_LABEL[v] ?? v;
}
