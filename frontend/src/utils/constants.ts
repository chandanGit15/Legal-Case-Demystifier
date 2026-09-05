/** Legal issue categories for the New Case flow (fixed by product spec). */
/** The application is India-only: the country is fixed and never editable. */
export const JURISDICTION_COUNTRY = "India";

export const INDIAN_STATES = [
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
];

export const INDIAN_UNION_TERRITORIES = [
  "Andaman and Nicobar Islands",
  "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi",
  "Jammu and Kashmir",
  "Ladakh",
  "Lakshadweep",
  "Puducherry",
];

export const CASE_CATEGORIES = [
  "Employment",
  "Consumer",
  "Contract",
  "Property",
  "Family",
  "Criminal",
  "Civil",
  "Financial",
  "Tenant/Landlord",
  "Business",
  "Intellectual Property",
  "Other",
] as const;

export type CaseCategory = (typeof CASE_CATEGORIES)[number];

export const LANGUAGES: [string, string][] = [
  ["en", "English"],
  ["es", "Español"],
  ["fr", "Français"],
  ["de", "Deutsch"],
  ["hi", "हिन्दी"],
  ["zh", "中文"],
  ["ar", "العربية"],
  ["pt", "Português"],
];

export const CASE_STATUS_META: Record<string, { label: string; tone: string }> = {
  draft: { label: "Draft", tone: "draft" },
  analysis_in_progress: { label: "Analysis in progress", tone: "analysis_in_progress" },
  analysis_complete: { label: "Analysis complete", tone: "analysis_complete" },
  action_required: { label: "Action required", tone: "action_required" },
  resolved: { label: "Resolved", tone: "resolved" },
  archived: { label: "Archived", tone: "archived" },
};

export const CASE_STATUS_OPTIONS = Object.entries(CASE_STATUS_META).map(([value, meta]) => ({
  value,
  label: meta.label,
}));

export function caseStatusMeta(status: string | undefined | null): { label: string; tone: string } {
  return CASE_STATUS_META[status ?? ""] ?? { label: status || "draft", tone: status || "draft" };
}