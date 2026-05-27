-- ═══════════════════════════════════════════
-- Calm Veritas Forum — Supabase Schema
-- Run this in: supabase.com → SQL Editor
-- ═══════════════════════════════════════════

-- 1. Profiles (auto-created on signup)
create table profiles (
  id uuid references auth.users on delete cascade primary key,
  username text not null,
  created_at timestamptz default now()
);
alter table profiles enable row level security;
create policy "Profiles are public" on profiles for select using (true);
create policy "Users update own profile" on profiles for update using (auth.uid() = id);

-- Auto-create profile on signup
create or replace function handle_new_user()
returns trigger as $$
begin
  insert into profiles (id, username)
  values (new.id, coalesce(new.raw_user_meta_data->>'username', split_part(new.email,'@',1)));
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure handle_new_user();

-- 2. Threads
create table threads (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users on delete cascade not null,
  title text not null,
  body text not null,
  category text not null default 'general',
  reply_count integer default 0,
  created_at timestamptz default now()
);
alter table threads enable row level security;
create policy "Threads are public" on threads for select using (true);
create policy "Auth users create threads" on threads for insert with check (auth.uid() = user_id);
create policy "Authors update own threads" on threads for update using (auth.uid() = user_id);

-- 3. Posts (replies)
create table posts (
  id uuid default gen_random_uuid() primary key,
  thread_id uuid references threads on delete cascade not null,
  user_id uuid references auth.users on delete cascade not null,
  body text not null,
  created_at timestamptz default now()
);
alter table posts enable row level security;
create policy "Posts are public" on posts for select using (true);
create policy "Auth users create posts" on posts for insert with check (auth.uid() = user_id);
create policy "Authors update own posts" on posts for update using (auth.uid() = user_id);

-- 4. Email subscribers
create table subscribers (
  id uuid default gen_random_uuid() primary key,
  email text not null unique,
  subscribed_at timestamptz default now()
);
alter table subscribers enable row level security;
create policy "Anyone can subscribe" on subscribers for insert with check (true);
create policy "Admins can view subscribers" on subscribers for select using (false);
