-- Add university column to users table
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS university TEXT;
