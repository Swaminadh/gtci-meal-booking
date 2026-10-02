import { checkEmployee, getBookings, saveBookings, getReport } from "./api.js";

const $ = (id) => document.getElementById(id);
const state = { user: null, bookings: [] };
// toISOString() converts to UTC first, which shifts local midnight back a day in positive-offset timezones (e.g. IST) - format from local date parts instead.
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const today = new Date();

function message(id, text, error = false) { const el = $(id); el.textContent = text; el.className = `message${error ? " error" : ""}`; }
function formatDate(value) { return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { weekday:"short", day:"numeric", month:"short", year:"numeric" }); }
function showView() {
  document.body.classList.toggle("login-bg", !state.user);
  $("login-view").hidden = Boolean(state.user); $("employee-view").hidden = !state.user || state.user.role === "admin";
  $("admin-view").hidden = !state.user || state.user.role !== "admin"; $("logout-button").hidden = !state.user;
  if (!state.user) return;
  if (state.user.role === "admin") $("admin-email").textContent = state.user.email;
  else { $("employee-name").textContent = `Hello, ${state.user.full_name} 👋`; $("employee-email").textContent = state.user.email; }
}
function renderBookings() {
  const rows = state.bookings.filter(x => x.meal_date >= iso(today)).sort((a,b) => a.meal_date.localeCompare(b.meal_date));
  $("upcoming-bookings").innerHTML = rows.length ? rows.map(x => `<tr><td>${formatDate(x.meal_date)}</td><td>${x.status === "booked" ? "✅ Yes" : "🚫 No"}</td></tr>`).join("") : "<tr><td colspan=\"2\">🍽️ No future bookings yet.</td></tr>";
}
function bookingFor(date) { return state.bookings.find(x => x.meal_date === date); }
async function refreshBookings() { state.bookings = (await getBookings(state.user.email)).bookings; renderBookings(); renderWeek(); }
async function save(items) { await saveBookings(state.user.email, items); await refreshBookings(); message("booking-message", "✅ Your booking has been saved."); }
function monday(date) { const d = new Date(`${date}T00:00:00`); const day = d.getDay() || 7; d.setDate(d.getDate() - day + 1); return d; }
function renderWeek() {
  const start = monday($("week-start").value || iso(today)); $("week-start").value = iso(start);
  $("week-days").innerHTML = Array.from({ length:5 }, (_, i) => { const date = iso(addDays(start, i)); const booking = bookingFor(date); return `<div class="week-day"><label>${formatDate(date)}</label><select data-date="${date}"><option value="">No choice</option><option value="booked" ${booking?.status === "booked" ? "selected" : ""}>Meal</option><option value="declined" ${booking?.status === "declined" ? "selected" : ""}>No meal</option></select></div>`; }).join("");
}
function setMode(mode) { document.querySelectorAll("[data-mode]").forEach(x => x.classList.toggle("active", x.dataset.mode === mode)); $("day-picker").hidden = mode !== "day"; $("day-actions").hidden = mode !== "day"; $("week-picker").hidden = mode !== "week"; $("week-actions").hidden = mode !== "week"; if (mode === "week") renderWeek(); }
function csvEscape(value) { return `"${String(value ?? "").replaceAll('"', '""')}"`; }
function datesBetween(start, end) { const dates = []; for (let d = new Date(`${start}T00:00:00`), last = new Date(`${end}T00:00:00`); d <= last; d = addDays(d, 1)) dates.push(iso(d)); return dates; }
function shortDate(value) { return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, { month:"short", day:"numeric" }); }
function renderReport(rows, startDate, endDate) {
  const dates = datesBetween(startDate, endDate);
  const people = new Map();
  for (const r of rows) {
    if (!people.has(r.email)) people.set(r.email, { full_name:r.full_name, email:r.email, booked:new Set() });
    people.get(r.email).booked.add(r.meal_date);
  }
  const sorted = [...people.values()].sort((a, b) => a.full_name.localeCompare(b.full_name));
  $("report-head").innerHTML = `<tr><th>Name</th><th>Email</th>${dates.map(d => `<th>${shortDate(d)}</th>`).join("")}</tr>`;
  $("report-rows").innerHTML = sorted.length
    ? sorted.map(p => `<tr><td>${p.full_name}</td><td>${p.email}</td>${dates.map(d => `<td>${p.booked.has(d) ? "Yes" : "No"}</td>`).join("")}</tr>`).join("")
    : `<tr><td colspan="${2 + dates.length}">No meals booked for this period.</td></tr>`;
}
function downloadReport() { const head = [...$("report-head").querySelectorAll("th")].map(th => th.textContent); const rows = [...$("report-rows").querySelectorAll("tr")].map(r => [...r.children].map(c => c.textContent)); if (!rows.length) return; const content = [head, ...rows].map(r => r.map(csvEscape).join(",")).join("\n"); const a = Object.assign(document.createElement("a"), { href:URL.createObjectURL(new Blob([content], { type:"text/csv" })), download:"meal-report.csv" }); a.click(); URL.revokeObjectURL(a.href); }

$("login-form").addEventListener("submit", async (event) => { event.preventDefault(); const email = $("email").value.trim().toLowerCase(); message("login-message", "Checking access..."); try { state.user = await checkEmployee(email); localStorage.setItem("meal-user", JSON.stringify(state.user)); showView(); if (state.user.role === "admin") $("load-report").click(); else await refreshBookings(); } catch (e) { message("login-message", e.message, true); } });
$("logout-button").onclick = () => { localStorage.removeItem("meal-user"); state.user = null; showView(); };
document.querySelectorAll("[data-mode]").forEach(x => x.onclick = () => setMode(x.dataset.mode));
$("meal-date").value = iso(addDays(today, 1)); $("meal-date").min = iso(today); $("meal-date").max = iso(addDays(today, 60)); $("week-start").value = iso(monday(today)); $("week-start").min = iso(today); $("week-start").max = iso(addDays(today, 60));
$("week-start").onchange = renderWeek;
$("day-actions").onclick = async (event) => { const choice = event.target.dataset.choice; if (!choice) return; try { await save([{ meal_date: $("meal-date").value, status: choice }]); } catch (e) { message("booking-message", e.message, true); } };
$("save-week").onclick = async () => { const items = [...$("week-days").querySelectorAll("select")].map(x => ({ meal_date:x.dataset.date, status:x.value || "clear" })); try { await save(items); } catch (e) { message("booking-message", e.message, true); } };
$("report-start").value = iso(today); $("report-end").value = iso(today);
$("load-report").onclick = async () => { try { const start = $("report-start").value, end = $("report-end").value; const data = await getReport(state.user.email, start, end); $("report-total").textContent = `Total meals booked: ${data.total}`; renderReport(data.rows, start, end); message("report-message", data.rows.length ? "" : "No meals booked for this period."); } catch (e) { message("report-message", e.message, true); } };
$("download-report").onclick = downloadReport;
try { state.user = JSON.parse(localStorage.getItem("meal-user")); if (state.user) { showView(); state.user.role === "admin" ? $("load-report").click() : refreshBookings(); } } catch { localStorage.removeItem("meal-user"); }
