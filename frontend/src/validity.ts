// HubSpot's ticket_validity stores "Valid"/"Invalid", not the "Valid Issue"/
// "Invalid Issue" labels shown in HubSpot's UI -- the other three options'
// stored values match their labels exactly.
export const VALIDITY_ORDER = ["Valid", "Invalid", "Service Request", "Data Request", "Feature Request"];

const VALIDITY_LABEL: Record<string, string> = {
  Valid: "Valid Issue",
  Invalid: "Invalid Issue",
};

export function validityDisplay(v: string): string {
  return VALIDITY_LABEL[v] ?? v;
}
