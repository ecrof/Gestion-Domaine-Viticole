# Gestion de la DB Supabase (SQL)

-- 1. Vide la table des inscriptions (registrations)
TRUNCATE TABLE registrations CASCADE;

-- 2. Vide la table des tâches (tasks)
TRUNCATE TABLE tasks CASCADE;

-- 3. Vide la table des chantiers/événements (events)
TRUNCATE TABLE events CASCADE;