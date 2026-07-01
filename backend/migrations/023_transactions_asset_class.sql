ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS asset_class TEXT;
