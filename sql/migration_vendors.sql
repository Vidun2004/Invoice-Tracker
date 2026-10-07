-- Vendors table - run once in Supabase SQL Editor
create table if not exists public.vendors (
  id uuid primary key default gen_random_uuid(),
  name text unique not null,
  contact text,
  notes text,
  created_by uuid references public.profiles(id),
  created_at timestamptz default now()
);
create index if not exists idx_vendors_name on public.vendors(name);

alter table public.vendors enable row level security;
drop policy if exists "auth all vendors" on public.vendors;
create policy "auth all vendors" on public.vendors for all to authenticated using (true) with check (true);

-- backfill from existing invoices (ignore duplicates)
insert into public.vendors (name)
select distinct vendor_name from public.invoices where vendor_name is not null and vendor_name <> ''
on conflict (name) do nothing;
