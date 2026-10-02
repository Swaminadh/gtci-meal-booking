import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const corsHeaders = { "Access-Control-Allow-Origin": "https://YOUR-GITHUB-USER.github.io", "Access-Control-Allow-Headers": "authorization, content-type" };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { ...corsHeaders, "Content-Type": "application/json" } });
const emailOf = (value: unknown) => typeof value === "string" ? value.trim().toLowerCase() : "";
const isAllowedBookingDate = (value: unknown) => {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const today = new Date().toISOString().slice(0, 10);
  const lastAllowed = new Date(Date.now() + 60 * 86_400_000).toISOString().slice(0, 10);
  return value >= today && value <= lastAllowed;
};

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (request.method !== "POST") return json({ error: "Method not allowed" }, 405);
  try {
    const input = await request.json();
    const email = emailOf(input.email);
    if (!/^\S+@\S+\.\S+$/.test(email)) return json({ error: "Enter a valid office email." }, 400);
    const secretKey = Deno.env.get("SUPABASE_SECRET_KEY") ?? Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
    if (!secretKey) throw new Error("Supabase server key is not configured.");
    const db = createClient(Deno.env.get("SUPABASE_URL")!, secretKey);
    const { data: employee } = await db.from("employees").select("email, full_name, role").eq("email", email).eq("active", true).maybeSingle();
    if (!employee) return json({ error: "Access unavailable." }, 403);
    if (input.action === "check_employee") return json(employee);
    if (input.action === "get_bookings") {
      const { data, error } = await db.from("meal_bookings").select("meal_date, status").eq("email", email).gte("meal_date", new Date().toISOString().slice(0, 10)).order("meal_date");
      if (error) throw error; return json({ bookings:data });
    }
    if (input.action === "save_bookings") {
      const bookings = Array.isArray(input.bookings) ? input.bookings : [];
      if (!bookings.length || bookings.length > 5 || bookings.some((x) => !isAllowedBookingDate(x.meal_date))) return json({ error:"Bookings must be for a date in the next 60 days." }, 400);
      for (const booking of bookings) {
        if (booking.status === "clear") await db.from("meal_bookings").delete().eq("email", email).eq("meal_date", booking.meal_date);
        else if (["booked", "declined"].includes(booking.status)) await db.from("meal_bookings").upsert({ email, meal_date:booking.meal_date, status:booking.status }, { onConflict:"email,meal_date" });
        else return json({ error:"Invalid meal choice." }, 400);
      }
      return json({ ok:true });
    }
    if (input.action === "get_report") {
      if (employee.role !== "admin") return json({ error:"Admin access required." }, 403);
      const start = input.startDate, end = input.endDate;
      if (!/^\d{4}-\d{2}-\d{2}$/.test(start || "") || !/^\d{4}-\d{2}-\d{2}$/.test(end || "") || start > end) return json({ error:"Choose a valid date range." }, 400);
      const { data, error } = await db.from("meal_bookings").select("meal_date, email, employees!inner(full_name)").eq("status", "booked").gte("meal_date", start).lte("meal_date", end).order("meal_date");
      if (error) throw error;
      return json({ total:data.length, rows:data.map((r:any) => ({ meal_date:r.meal_date, email:r.email, full_name:r.employees.full_name })) });
    }
    return json({ error:"Unknown action." }, 400);
  } catch (error) { console.error(error); return json({ error:"Service unavailable." }, 500); }
});
