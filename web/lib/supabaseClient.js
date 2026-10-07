import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

// Shared stage machine (keep in sync with desktop/utils/stages.py)
export const STANDARD_FLOW = ["Created", "PR", "PO", "GRN", "SentToFinance", "Paid"];
export const STRAIGHT_FLOW = ["Created", "SentToFinance", "Paid"];
export function nextStage(type, current) {
  const flow = type === "standard" ? STANDARD_FLOW : STRAIGHT_FLOW;
  const i = flow.indexOf(current);
  return i >= 0 && i + 1 < flow.length ? flow[i + 1] : null;
}
