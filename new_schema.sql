-- Add new columns to pge_bills table
ALTER TABLE pge_bills
  ADD COLUMN IF NOT EXISTS source_file_id TEXT,
  ADD COLUMN IF NOT EXISTS source_filename TEXT,
  ADD COLUMN IF NOT EXISTS storage_path TEXT,
  ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS account_number TEXT,
  ADD COLUMN IF NOT EXISTS service_address TEXT,
  ADD COLUMN IF NOT EXISTS billing_period TEXT,
  ADD COLUMN IF NOT EXISTS billing_days INTEGER,
  ADD COLUMN IF NOT EXISTS total_kwh NUMERIC,
  ADD COLUMN IF NOT EXISTS total_amount NUMERIC;
