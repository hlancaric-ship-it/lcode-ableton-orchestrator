-- Hlavni tabulka zanrovych smeru
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,          -- napr. "Peak-Time Techno", "Minimal Deep House"
    description TEXT
);

-- Podrobne zanrove archetypy (napr. "Sub-Bass Heavy", "Industrial Lead", "Atmospheric Pad")
CREATE TABLE IF NOT EXISTS genre_archetypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genre_id INTEGER REFERENCES genres(id) ON DELETE SET NULL,
    name TEXT NOT NULL UNIQUE,          -- napr. "Driving Peak-Time Kick & Bass", matchovano jako fraze v textu
    description TEXT,                   -- zvukovy popis chovani
    target_plugin TEXT NOT NULL DEFAULT 'Serum 2'
);

-- Detailni databazova matice pro knoflíky a parametry
CREATE TABLE IF NOT EXISTS archetype_knob_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    archetype_id INTEGER NOT NULL REFERENCES genre_archetypes(id) ON DELETE CASCADE,
    parameter_name TEXT NOT NULL,       -- funkce ze semantic_profiles.py, napr. "wt_pos", "filter_cutoff"
                                         -- NE primo Ableton parametr -- to, co je zrovna namapovane
                                         -- v Live, se meni za behu (viz LCodeArchetypeManager.apply_to_live)
    target_value REAL NOT NULL CHECK (target_value >= 0.0 AND target_value <= 1.0),
    acoustic_role TEXT                  -- semanticky popis, napr. "Ostry rezavy stredy", "Hluboky sub"
);

-- Note pattern pro archetyp -- relativne k root note pri pouziti
CREATE TABLE IF NOT EXISTS archetype_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    archetype_id INTEGER NOT NULL REFERENCES genre_archetypes(id) ON DELETE CASCADE,
    semitone_offset INTEGER NOT NULL,
    start_beat REAL NOT NULL,
    duration_beats REAL NOT NULL,
    velocity INTEGER NOT NULL CHECK (velocity >= 1 AND velocity <= 127)
);

CREATE INDEX IF NOT EXISTS idx_genre_archetypes_genre ON genre_archetypes(genre_id);
CREATE INDEX IF NOT EXISTS idx_archetype_knob_mappings_archetype ON archetype_knob_mappings(archetype_id);
CREATE INDEX IF NOT EXISTS idx_archetype_notes_archetype ON archetype_notes(archetype_id);
