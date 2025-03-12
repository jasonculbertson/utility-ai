-- Enable RLS
alter table pge_bills enable row level security;

-- Create policy to allow all operations
create policy "Enable all operations for authenticated users"
on pge_bills
for all
using (true)
with check (true);
