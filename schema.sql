-- Run in Supabase SQL Editor. Keep RLS enabled; users can only access their own rows.
create extension if not exists pgcrypto;
create table if not exists public.user_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  email text,
  created_at timestamptz not null default now()
);
create table if not exists public.cashflow_scenarios (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null default 'My scenario',
  currency text not null default 'USD',
  opening_balance numeric not null default 0 check (opening_balance >= 0),
  safety_buffer numeric not null default 0 check (safety_buffer >= 0),
  invoices jsonb not null default '[]'::jsonb,
  expenses jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.user_profiles enable row level security;
alter table public.cashflow_scenarios enable row level security;
create policy "profile owner can read own profile" on public.user_profiles for select using (auth.uid() = id);
create policy "profile owner can insert own profile" on public.user_profiles for insert with check (auth.uid() = id);
create policy "profile owner can update own profile" on public.user_profiles for update using (auth.uid() = id) with check (auth.uid() = id);
create policy "scenario owner can read own scenarios" on public.cashflow_scenarios for select using (auth.uid() = user_id);
create policy "scenario owner can insert own scenarios" on public.cashflow_scenarios for insert with check (auth.uid() = user_id);
create policy "scenario owner can update own scenarios" on public.cashflow_scenarios for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "scenario owner can delete own scenarios" on public.cashflow_scenarios for delete using (auth.uid() = user_id);
