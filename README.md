# Gestion de la DB Supabase (SQL)

-- 1. Vide la table des inscriptions (registrations)
TRUNCATE TABLE registrations CASCADE;

-- 2. Vide la table des tâches (tasks)
TRUNCATE TABLE tasks CASCADE;

-- 3. Vide la table des chantiers/événements (events)
TRUNCATE TABLE events CASCADE;

-- 4. Ajoute un chantier/événement (events)
INSERT INTO events (title, start_date, type)
VALUES ('Chantier d''ébourgeonnage', '2026-07-10', 'Ébourgeonnage');