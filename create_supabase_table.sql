-- Create table for PG&E bills
create table pge_bills (
    id bigint primary key generated always as identity,
    account_number varchar,
    statement_date date,
    total_amount decimal(10,2),
    due_date date,
    service_address text,
    electric_charges decimal(10,2),
    gas_charges decimal(10,2),
    total_usage_kwh decimal(10,2),
    total_usage_therms decimal(10,2),
    storage_path text,
    processed_at timestamp with time zone,
    created_at timestamp with time zone default now()
);
