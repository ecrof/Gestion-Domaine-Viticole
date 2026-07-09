# Gestion de l'app
- https://github.com/
- https://share.streamlit.io/
- https://supabase.com/

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




TRUNCATE TABLE registrations CASCADE;
TRUNCATE TABLE tasks CASCADE;
TRUNCATE TABLE events CASCADE;

INSERT INTO events (title, start_date, type)
VALUES 
    ('Vendanges Solaris - Week-end 1 - 9am jusqu''au soir', '2026-09-05', 'Vendanges'),
    ('Vendanges Solaris - Week-end 2 - 9am jusqu''au soir', '2026-09-12', 'Vendanges'),
    ('Vendanges Solaris - Week-end 3 - 9am jusqu''au soir', '2026-09-19', 'Vendanges'),
    ('Vendanges Riesling - Week-end 1 - 9am jusqu''au soir', '2026-09-26', 'Vendanges'),
    ('Vendanges Riesling - Week-end 2 - 9am jusqu''au soir', '2026-10-03', 'Vendanges'),
    ('Vendanges Riesling - Week-end 3 - 9am jusqu''au soir', '2026-10-10', 'Vendanges');


-- Ajoute les nouvelles colonnes nécessaires de manière sécurisée si elles n'existent pas
ALTER TABLE registrations ADD COLUMN IF NOT EXISTS meal_lunch boolean DEFAULT false;
ALTER TABLE registrations ADD COLUMN IF NOT EXISTS meal_dinner boolean DEFAULT false;
ALTER TABLE registrations ADD COLUMN IF NOT EXISTS comment text;

ALTER TABLE tasks RENAME COLUMN priority TO completed_by;
