drop table if exists admissions_chat cascade;

create table admissions_chat (
    id uuid default gen_random_uuid() primary key,
    phone_number text unique,
    full_chat jsonb,
    last_emotion text,
    lead_score int default 0,
    lead_type text default 'Cold',
    created_at timestamp default now()
);

alter table admissions_chat enable row level security;

create policy "Allow public insert"
on admissions_chat
for insert
to anon
with check (true);

create policy "Allow public update"
on admissions_chat
for update
to anon
using (true)
with check (true);

create policy "Allow public select"
on admissions_chat
for select
to anon
using (true);
