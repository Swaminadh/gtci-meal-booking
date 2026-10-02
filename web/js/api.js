import { SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY } from "./config.js";

async function rpc(functionName, body) {
  const response = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${functionName}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "apikey": SUPABASE_PUBLISHABLE_KEY, "Authorization": `Bearer ${SUPABASE_PUBLISHABLE_KEY}` },
    body: JSON.stringify(body)
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.message || "Request failed. Please try again.");
  return data;
}
export async function checkEmployee(email) {
  const rows = await rpc("check_employee", { p_email: email });
  if (!rows?.length) throw new Error("Access unavailable.");
  return rows[0];
}
export async function getBookings(email) { return { bookings: await rpc("get_bookings", { p_email: email }) }; }
export async function saveBookings(email, bookings) { return rpc("save_bookings", { p_email: email, p_bookings: bookings }); }
export async function getReport(email, startDate, endDate) {
  const rows = await rpc("get_report", { p_email: email, p_start_date: startDate, p_end_date: endDate });
  return { rows, total: rows.length };
}
