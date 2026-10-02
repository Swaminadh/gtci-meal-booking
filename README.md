# Book Your Meal

A plain HTML, CSS, and JavaScript meal-booking interface backed by Supabase Postgres, built to be fast and dependency-free for 150 engineers. The previous Streamlit implementation is kept for reference in [`legacy_streamlit/`](legacy_streamlit/) — it is not deployed.

## Project layout

- `web/` — the active static frontend (HTML/CSS/JS), deployed to GitHub Pages
- `supabase/schema.sql` — tables, row-level security, and the RPC functions the browser calls
- `supabase/functions/meal-api/` — an unused draft Edge Function from an earlier design; the frontend calls the RPC functions in `schema.sql` directly, not this function
- `database/` — the employee roster workbook/CSVs used to seed and sync the `employees` table
- `scripts/import_employees.py` — syncs `database/employee_db.xlsx` to Supabase (used by `.github/workflows/sync-employees.yml`)
- `legacy_streamlit/` — the retired Streamlit app, kept as a backup only

## First deployment

1. Run `supabase/schema.sql` in Supabase Dashboard → SQL Editor.
2. Save `database/employee_db.xlsx` as CSV. In Supabase Table Editor, import it into `employees`: map `name` to `full_name`, set all emails to lower case, and assign the relevant employee the `admin` role.
3. `web/js/config.js` contains the public project URL and publishable key. Never add a secret key to the website.
4. The included `.github/workflows/deploy-pages.yml` publishes `web/` on every push to `main`. In the repository's **Settings → Pages**, select **GitHub Actions** as the source.

## Automatic employee roster sync

The included `.github/workflows/sync-employees.yml` runs every time `database/employee_db.xlsx` is changed on `main`. In the GitHub repository, add these Actions secrets under **Settings → Secrets and variables → Actions**:

- `SUPABASE_URL` — your project URL
- `SUPABASE_SECRET_KEY` — a Supabase secret key

It updates existing employees, adds new employees, and marks employees removed from the workbook as inactive. It does not delete employees or their booking history.

## Privacy and limitations

The roster is only in Supabase and is not published by GitHub Pages. Browser users cannot read database tables directly; they can call only the scoped PostgreSQL RPC functions.

This first version uses an email allow-list, not authentication: a person who enters an allowed email can act as that employee, including an admin email. It is intended only for the explicitly accepted low-risk, trusted-internal scenario. Add magic-link or organisation sign-in before using personal email addresses or treating reports as confidential.
