-- Enable pgcrypto extension
create extension if not exists pgcrypto;

-- Create function to execute SQL
create or replace function exec_sql(query text)
returns void as $$
begin
  execute query;
end;
$$ language plpgsql security definer;
