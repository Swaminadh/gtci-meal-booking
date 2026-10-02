-- Run this complete file in Supabase Dashboard > SQL Editor.
-- The browser uses only the publishable key. Direct table access remains blocked.
create table if not exists public.employees (
  email text primary key check (email = lower(email)),
  full_name text not null,
  role text not null default 'user' check (role in ('user', 'admin')),
  active boolean not null default true,
  updated_at timestamptz not null default now()
);

create table if not exists public.meal_bookings (
  email text not null references public.employees(email) on delete cascade,
  meal_date date not null,
  status text not null check (status in ('booked', 'declined')),
  updated_at timestamptz not null default now(),
  primary key (email, meal_date)
);

create index if not exists meal_bookings_date_booked_idx on public.meal_bookings (meal_date) where status = 'booked';
alter table public.employees enable row level security;
alter table public.meal_bookings enable row level security;
revoke all on table public.employees, public.meal_bookings from anon, authenticated;

-- RPC functions are deliberately the only browser-facing database operations.
-- This is an email allow-list, not proof that a person owns an email address.
create or replace function public.check_employee(p_email text)
returns table(email text, full_name text, role text)
language sql stable security definer set search_path = public
as $$
  select e.email, e.full_name, e.role
  from public.employees e
  where e.email = lower(trim(p_email)) and e.active;
$$;

create or replace function public.get_bookings(p_email text)
returns table(meal_date date, status text)
language sql stable security definer set search_path = public
as $$
  select b.meal_date, b.status
  from public.meal_bookings b
  where b.email = lower(trim(p_email))
    and exists (select 1 from public.employees e where e.email = lower(trim(p_email)) and e.active)
  order by b.meal_date;
$$;

create or replace function public.save_bookings(p_email text, p_bookings jsonb)
returns void
language plpgsql security definer set search_path = public
as $$
declare
  normalized_email text := lower(trim(p_email));
  booking jsonb;
  booking_date date;
  booking_status text;
begin
  if not exists (select 1 from public.employees where email = normalized_email and active) then raise exception 'Access unavailable.'; end if;
  if jsonb_typeof(p_bookings) <> 'array' or jsonb_array_length(p_bookings) not between 1 and 5 then raise exception 'Invalid booking request.'; end if;
  for booking in select value from jsonb_array_elements(p_bookings) loop
    booking_date := (booking ->> 'meal_date')::date;
    booking_status := booking ->> 'status';
    if booking_date < current_date or booking_date > current_date + 60 then raise exception 'Bookings must be for the next 60 days.'; end if;
    if booking_status = 'clear' then
      delete from public.meal_bookings where email = normalized_email and meal_date = booking_date;
    elsif booking_status in ('booked', 'declined') then
      insert into public.meal_bookings (email, meal_date, status) values (normalized_email, booking_date, booking_status)
      on conflict (email, meal_date) do update set status = excluded.status, updated_at = now();
    else raise exception 'Invalid meal choice.';
    end if;
  end loop;
end;
$$;

create or replace function public.get_report(p_email text, p_start_date date, p_end_date date)
returns table(meal_date date, email text, full_name text)
language plpgsql stable security definer set search_path = public
as $$
#variable_conflict use_column
begin
  if p_start_date > p_end_date then raise exception 'Choose a valid date range.'; end if;
  if not exists (select 1 from public.employees e where e.email = lower(trim(p_email)) and e.active and e.role = 'admin') then raise exception 'Admin access required.'; end if;
  return query select b.meal_date, b.email, e.full_name from public.meal_bookings b join public.employees e on e.email = b.email
    where b.status = 'booked' and b.meal_date between p_start_date and p_end_date order by b.meal_date, e.full_name;
end;
$$;

revoke all on function public.check_employee(text), public.get_bookings(text), public.save_bookings(text, jsonb), public.get_report(text, date, date) from public;
grant execute on function public.check_employee(text), public.get_bookings(text), public.save_bookings(text, jsonb), public.get_report(text, date, date) to anon;
