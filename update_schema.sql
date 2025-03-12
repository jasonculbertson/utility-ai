-- Drop existing table
drop table if exists pge_bills;

-- Create enhanced table for PG&E bills
create table pge_bills (
    id bigint primary key generated always as identity,
    -- Basic Info
    account_number varchar,
    service_address text,
    billing_period_start date,
    billing_period_end date,
    billing_days integer,
    
    -- Usage Data
    total_kwh decimal(10,2),
    peak_kwh decimal(10,2),
    off_peak_kwh decimal(10,2),
    tier1_kwh decimal(10,2),
    tier2_kwh decimal(10,2),
    tier3_kwh decimal(10,2),
    
    -- Rate Plan Info
    rate_plan varchar(50),
    peak_rate decimal(10,4),
    off_peak_rate decimal(10,4),
    tier1_rate decimal(10,4),
    tier2_rate decimal(10,4),
    tier3_rate decimal(10,4),
    
    -- Charges and Adjustments
    base_electric_charges decimal(10,2),
    generation_credits decimal(10,2),
    dcare_discount decimal(10,2),
    taxes_and_surcharges decimal(10,2),
    minimum_charges decimal(10,2),
    total_amount decimal(10,2),
    
    -- Storage and Processing
    storage_path text,
    processed_at timestamp with time zone,
    created_at timestamp with time zone default now()
);
