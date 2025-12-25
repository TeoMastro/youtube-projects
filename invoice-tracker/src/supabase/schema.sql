-- Invoices table
create table invoices (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users not null,
  company_name text not null,
  amount numeric not null,
  currency text default 'USD',
  date date not null,
  category text,
  image_url text,
  processed_at timestamp with time zone default timezone('utc'::text, now()),
  created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Enable Row Level Security
alter table invoices enable row level security;

-- Policy: Users can only see their own invoices
create policy "Users can view own invoices"
  on invoices for select
  using (auth.uid() = user_id);

-- Policy: Users can insert their own invoices
create policy "Users can insert own invoices"
  on invoices for insert
  with check (auth.uid() = user_id);

-- Policy: Users can update their own invoices
create policy "Users can update own invoices"
  on invoices for update
  using (auth.uid() = user_id);

-- Policy: Users can delete their own invoices
create policy "Users can delete own invoices"
  on invoices for delete
  using (auth.uid() = user_id);

-- Storage Setup
-- Create the bucket (public so we can use getPublicUrl)
insert into storage.buckets (id, name, public)
values ('invoices', 'invoices', true)
on conflict (id) do nothing;

-- Policy: Authenticated users can upload files to 'invoices' bucket
-- (Enforcing that files are stored in a folder named after their user ID)
create policy "Authenticated users can upload invoices"
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'invoices' and
  (storage.foldername(name))[1] = auth.uid()::text
);

-- Policy: Users can view their own files (and since it's public, technically anyone with link, but let's add RLS for listing)
create policy "Users can view own invoices"
on storage.objects for select
to authenticated
using (
  bucket_id = 'invoices' and
  (storage.foldername(name))[1] = auth.uid()::text
);
