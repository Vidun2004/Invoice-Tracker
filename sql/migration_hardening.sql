-- Hardening: audit trail survives, admin-only delete, stage enforced in DB
-- Run AFTER schema.sql + migration_vendors.sql, in Supabase SQL Editor

-- 0. Admin helper (used by policies)
create or replace function public.is_admin()
returns boolean language sql security definer set search_path = public as $$
  select exists (select 1 from public.profiles where id = auth.uid() and role = 'admin');
$$;

-- 1. Stop cascade deletes wiping history/proofs
alter table public.audit_log drop constraint if exists audit_log_invoice_id_fkey;
alter table public.audit_log
  add constraint audit_log_invoice_id_fkey
  foreign key (invoice_id) references public.invoices(id) on delete restrict;

alter table public.finance_proofs drop constraint if exists finance_proofs_invoice_id_fkey;
alter table public.finance_proofs
  add constraint finance_proofs_invoice_id_fkey
  foreign key (invoice_id) references public.invoices(id) on delete restrict;

-- 2. RLS: audit insert-only, proofs insert-only, delete restricted to admin
drop policy if exists "auth all audit" on public.audit_log;
drop policy if exists "auth read audit" on public.audit_log;
drop policy if exists "auth insert audit" on public.audit_log;
create policy "auth read audit" on public.audit_log for select to authenticated using (true);
create policy "auth insert audit" on public.audit_log for insert to authenticated with check (true);

drop policy if exists "auth all proofs" on public.finance_proofs;
drop policy if exists "auth read proofs rows" on public.finance_proofs;
drop policy if exists "auth insert proofs rows" on public.finance_proofs;
create policy "auth read proofs rows" on public.finance_proofs for select to authenticated using (true);
create policy "auth insert proofs rows" on public.finance_proofs for insert to authenticated with check (true);

drop policy if exists "auth all invoices" on public.invoices;
drop policy if exists "auth read invoices" on public.invoices;
drop policy if exists "auth insert invoices" on public.invoices;
drop policy if exists "auth update invoices" on public.invoices;
drop policy if exists "admin delete invoices" on public.invoices;
create policy "auth read invoices" on public.invoices for select to authenticated using (true);
create policy "auth insert invoices" on public.invoices for insert to authenticated with check (true);
create policy "auth update invoices" on public.invoices for update to authenticated using (true) with check (true);
create policy "admin delete invoices" on public.invoices for delete to authenticated using (public.is_admin());

drop policy if exists "auth all vendors" on public.vendors;
drop policy if exists "auth read vendors" on public.vendors;
drop policy if exists "auth write vendors" on public.vendors;
drop policy if exists "admin delete vendors" on public.vendors;
create policy "auth read vendors" on public.vendors for select to authenticated using (true);
create policy "auth write vendors" on public.vendors for insert to authenticated with check (true);
create policy "auth update vendors" on public.vendors for update to authenticated using (true) with check (true);
create policy "admin delete vendors" on public.vendors for delete to authenticated using (public.is_admin());

drop policy if exists "auth read profiles" on public.profiles;
drop policy if exists "auth update own profile" on public.profiles;
drop policy if exists "admin update profiles" on public.profiles;
create policy "auth read profiles" on public.profiles for select to authenticated using (true);
create policy "auth update own profile" on public.profiles for update to authenticated
  using (auth.uid() = id) with check (auth.uid() = id);
create policy "admin update profiles" on public.profiles for update to authenticated
  using (public.is_admin()) with check (public.is_admin());

-- storage: remove app delete, keep read+insert
drop policy if exists "admin delete proofs" on storage.objects;

-- 3. Server-side stage machine (race-proof, both apps)
create or replace function public.enforce_stage()
returns trigger language plpgsql as $$
declare
  flow text[];
begin
  if old.current_stage = new.current_stage then
    return new;
  end if;
  if old.type <> new.type then
    raise exception 'type cannot change (was %, new %)', old.type, new.type;
  end if;
  if old.type = 'standard' then
    flow := array['Created','PR','PO','GRN','SentToFinance','Paid'];
  else
    flow := array['Created','SentToFinance','Paid'];
  end if;
  if array_position(flow, old.current_stage) is null
     or array_position(flow, new.current_stage) is null then
    raise exception 'unknown stage % -> %', old.current_stage, new.current_stage;
  end if;
  if array_position(flow, new.current_stage) = array_position(flow, old.current_stage) + 1 then
    return new;
  end if;
  raise exception 'illegal stage move % -> % for %', old.current_stage, new.current_stage, old.type;
end $$;

drop trigger if exists enforce_stage_flow on public.invoices;
create trigger enforce_stage_flow
before update of current_stage, type on public.invoices
for each row execute function public.enforce_stage();

-- 4. Soft delete (audit survives: delete sets deleted_at, rows hidden not wiped)
alter table public.invoices add column if not exists deleted_at timestamptz;
create index if not exists idx_invoices_deleted on public.invoices(deleted_at);

create or replace view public.eligible_for_finance as
select id, invoice_number, vendor_name, amount, currency, type, current_stage
from public.invoices
where deleted_at is null
  and ((type='standard' and current_stage='GRN')
    or (type='straight' and current_stage='Created'))
order by created_at desc;
