-- Invoice Tracker Schema - Phase 0
-- Run in Supabase SQL Editor

-- 1. Profiles (extends auth.users)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  role text not null default 'user' check (role in ('admin','user')),
  created_at timestamptz default now()
);

-- auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, display_name)
  values (new.id, new.email, split_part(new.email,'@',1))
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users for each row execute function public.handle_new_user();

-- 2. Invoices
create table if not exists public.invoices (
  id uuid primary key default gen_random_uuid(),
  invoice_number text unique not null,
  vendor_name text not null,
  amount numeric(14,2) not null check (amount >= 0),
  currency text not null default 'LKR',
  invoice_date date not null,
  due_date date,
  type text not null check (type in ('standard','straight')),
  current_stage text not null default 'Created'
    check (current_stage in ('Created','PR','PO','GRN','SentToFinance','Paid')),
  pr_number text,
  po_number text,
  grn_number text,
  notes text,
  created_by uuid references public.profiles(id),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- updated_at trigger
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end $$;

drop trigger if exists set_invoices_updated on public.invoices;
create trigger set_invoices_updated
before update on public.invoices for each row execute function public.set_updated_at();

-- 3. Finance proofs (photo metadata)
create table if not exists public.finance_proofs (
  id uuid primary key default gen_random_uuid(),
  invoice_id uuid not null references public.invoices(id) on delete cascade,
  photo_path text not null,
  captured_at timestamptz not null default now(),
  uploaded_by uuid references public.profiles(id),
  device_info text,
  created_at timestamptz default now()
);
create index if not exists idx_proofs_invoice on public.finance_proofs(invoice_id);

-- 4. Audit log
create table if not exists public.audit_log (
  id uuid primary key default gen_random_uuid(),
  invoice_id uuid not null references public.invoices(id) on delete cascade,
  from_stage text,
  to_stage text,
  action text not null,
  note text,
  source text not null default 'desktop' check (source in ('desktop','web')),
  actor uuid references public.profiles(id),
  created_at timestamptz default now()
);
create index if not exists idx_audit_invoice on public.audit_log(invoice_id);
create index if not exists idx_audit_created on public.audit_log(created_at desc);

-- 5. Eligible-for-finance view (used by web dropdown)
create or replace view public.eligible_for_finance as
select id, invoice_number, vendor_name, amount, currency, type, current_stage
from public.invoices
where (type='standard' and current_stage='GRN')
   or (type='straight' and current_stage='Created')
order by created_at desc;

-- 6. Storage bucket for photos
insert into storage.buckets (id, name, public)
values ('finance-proofs','finance-proofs', false)
on conflict (id) do nothing;

-- 7. RLS
alter table public.profiles enable row level security;
alter table public.invoices enable row level security;
alter table public.finance_proofs enable row level security;
alter table public.audit_log enable row level security;

drop policy if exists "auth read profiles" on public.profiles;
create policy "auth read profiles" on public.profiles for select to authenticated using (true);

drop policy if exists "auth all invoices" on public.invoices;
create policy "auth all invoices" on public.invoices for all to authenticated using (true) with check (true);

drop policy if exists "auth all proofs" on public.finance_proofs;
create policy "auth all proofs" on public.finance_proofs for all to authenticated using (true) with check (true);

drop policy if exists "auth all audit" on public.audit_log;
create policy "auth all audit" on public.audit_log for all to authenticated using (true) with check (true);

-- storage policies (private bucket, authenticated only)
drop policy if exists "auth read proofs" on storage.objects;
create policy "auth read proofs" on storage.objects for select to authenticated using (bucket_id='finance-proofs');

drop policy if exists "auth insert proofs" on storage.objects;
create policy "auth insert proofs" on storage.objects for insert to authenticated with check (bucket_id='finance-proofs');

drop policy if exists "admin delete proofs" on storage.objects;
create policy "admin delete proofs" on storage.objects for delete to authenticated using (bucket_id='finance-proofs');
