-- Run with the project administrator after applying Alembic migrations.
-- Documents are served through the backend; browser anon/authenticated roles have no bucket access.
INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES ('medical-reports', 'medical-reports', false, 15728640)
ON CONFLICT (id) DO UPDATE SET public=false, file_size_limit=15728640;
-- Never expose SUPABASE_SERVICE_ROLE_KEY to NEXT_PUBLIC_* variables.
-- Create a dedicated login role using a secret manager, with NOSUPERUSER NOBYPASSRLS.
-- The role's password is deliberately not included in source control.
-- Example grants after creating medicare_app:
-- GRANT USAGE ON SCHEMA public TO medicare_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO medicare_app;
-- The backend sets app.user_id transaction-locally after verifying authentication.
-- Do not grant these tables to anon or authenticated Supabase browser roles.
