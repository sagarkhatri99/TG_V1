TG_V1 Application Reset - Backup Manifest
==========================================
Created: 2025-12-24 18:43:52
Location: c:\dev\TG_V1\backups\reset_20251224_184351

Files:
- tg_tools_full.sql: Full database backup
- users_table.csv: Users table (-1 users)
- users_table.sql: Users table as INSERT statements

To Restore Full Database:
docker exec -i tg_v1-db-1 psql -U user -d tg_tools < tg_tools_full.sql

To Restore Users Only:
docker exec -i tg_v1-db-1 psql -U user -d tg_tools < users_table.sql
