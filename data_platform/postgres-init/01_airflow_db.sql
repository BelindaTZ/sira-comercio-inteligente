-- Feature 010 — base de metadata de Airflow, separada de la base operativa `sira`.
-- Postgres ejecuta este script SÓLO al inicializar un volumen nuevo. En un volumen
-- ya existente hay que crearla a mano una vez:
--   docker compose exec postgres createdb -U sira airflow
SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'airflow')\gexec
