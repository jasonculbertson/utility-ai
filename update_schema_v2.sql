-- Add new columns to pge_bills table
ALTER TABLE pge_bills
  ADD COLUMN IF NOT EXISTS previous_amount NUMERIC,
  ADD COLUMN IF NOT EXISTS payments_received NUMERIC,
  ADD COLUMN IF NOT EXISTS unpaid_balance NUMERIC,
  ADD COLUMN IF NOT EXISTS electric_delivery NUMERIC,
  ADD COLUMN IF NOT EXISTS electric_generation NUMERIC,
  ADD COLUMN IF NOT EXISTS gas_charges NUMERIC,
  ADD COLUMN IF NOT EXISTS total_amount NUMERIC,
  ADD COLUMN IF NOT EXISTS due_date DATE;
