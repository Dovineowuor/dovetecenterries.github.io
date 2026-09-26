-- -- PostgreSQL setup script for Zoobee-Cart project

-- -- Create database if it doesn't exist
-- DO
-- $$
-- BEGIN
--     IF NOT EXISTS (
--         SELECT FROM pg_database WHERE datname = 'dovetecenterprises'
--     ) THEN
--         CREATE DATABASE dovetecenterprises
--         WITH ENCODING 'UTF8'
--         LC_COLLATE = 'en_US.UTF-8'
--         LC_CTYPE = 'en_US.UTF-8'
--         TEMPLATE template0;
--     END IF;
-- END
-- $$;

-- -- Drop user if exists before recreating
-- DO
-- $$
-- BEGIN
--     IF EXISTS (
--         SELECT FROM pg_roles WHERE rolname = 'dovetecadmin'
--     ) THEN
--         REVOKE ALL PRIVILEGES ON DATABASE dovetecenterprises FROM dovetecadmin;
--         DROP ROLE dovetecadmin;
--     END IF;
-- END
-- $$;

-- -- Create user and grant privileges
-- CREATE ROLE dovetecadmin WITH LOGIN PASSWORD 'Ge20u2ahe7eme9#';
-- GRANT ALL PRIVILEGES ON DATABASE dovetecenterprises TO dovetecadmin;

-- -- Verify database creation
-- SELECT 'Database created: ' || datname AS "Database Info"
-- FROM pg_database
-- WHERE datname = 'dovetecenterprises';

-- -- Verify user creation
-- SELECT 'User created: ' || rolname AS "User Info"
-- FROM pg_roles
-- WHERE rolname = 'dovetecadmin';
