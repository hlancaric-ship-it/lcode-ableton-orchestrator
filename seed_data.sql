-- Vlozeni hlavnich zanru
INSERT INTO genres (id, name, description) VALUES
(1, 'Peak-Time / Driving Techno', 'Tlak, industrialni spina, hutne spodky a agresivni leady pro hlavni stage.'),
(2, 'Tech-House', 'Groovove basy, slapave haty, hravi plucky a dynamicke filtry.'),
(3, 'Melodic Techno', 'Epicke protazene wavetable matice, siroke unisono plochy a hluboka atmosfera.'),
(4, 'Minimal / Deep Tech', 'Subtilni perkuse, tlumene basy, cisty prostor a jemne pohybove modulace.');

-- Vlozeni archetypu pro jednotlive zanry
INSERT INTO genre_archetypes (id, genre_id, name) VALUES
(1, 1, 'Peak-Time Lead Synth (Saw/Warp)'),
(2, 1, 'Driving Sub-Bass (Mono Pure)'),
(3, 2, 'Groove Tech-House Stab'),
(4, 3, 'Melodic Supersaw Lead'),
(5, 4, 'Minimal Deep Pluck');

-- Archetyp 1: Peak-Time Lead Synth
INSERT INTO archetype_knob_mappings (archetype_id, parameter_name, target_value, acoustic_role) VALUES
(1, 'wt_pos', 0.82, 'Agresivni horni harmonicke kmitocty ve wavetablu'),
(1, 'warp_mode', 0.50, 'Rezim deformace vlnove delky (Bend/Sync)'),
(1, 'filter_cutoff', 0.75, 'Otevreny, dravy filtr pousteje stredy ven'),
(1, 'filter_resonance', 0.35, 'Mirna rezonance pro pistivy charakter'),
(1, 'unison_voices', 0.44, 'Siroky stereo obraz (7 hlasu)');

-- Archetyp 2: Driving Sub-Bass
INSERT INTO archetype_knob_mappings (archetype_id, parameter_name, target_value, acoustic_role) VALUES
(2, 'wt_pos', 0.05, 'Cista sub-basova vlnova delka (Sine/Triangle zaklad)'),
(2, 'warp_mode', 0.00, 'Bez zkresleni tvaru - cisty spodek'),
(2, 'filter_cutoff', 0.15, 'Zalomeny filtr, propousteje pouze spodek pod 100 Hz'),
(2, 'unison_voices', 0.00, 'Monofonni cisty stred bez rozpadu faze'),
(2, 'filter_drive', 0.20, 'Lehka lampova teplota pro prurraznost na malych bednach');

-- Archetyp 3: Groove Tech-House Stab
INSERT INTO archetype_knob_mappings (archetype_id, parameter_name, target_value, acoustic_role) VALUES
(3, 'wt_pos', 0.45, 'Kulaty, uderny platena zvuk'),
(3, 'filter_cutoff', 0.60, 'Stredne otevreny filtr s rychlou obalkou'),
(3, 'filter_resonance', 0.40, 'Charakteristicky "rubber" rezonancni odskok'),
(3, 'unison_voices', 0.22, 'Mirne rozsireni do sterea');

-- Archetyp 4: Melodic Supersaw Lead
INSERT INTO archetype_knob_mappings (archetype_id, parameter_name, target_value, acoustic_role) VALUES
(4, 'wt_pos', 0.30, 'Plna pilova vlnova delka'),
(4, 'unison_voices', 0.90, 'Maximalni pocet hlasu (16 hlasu pro epickou stenu)'),
(4, 'unison_detune', 0.65, 'Siroky rozptyl centu pro analogovy detune efekt'),
(4, 'filter_cutoff', 0.85, 'Vysoko posazeny filtr pro maximalni jas');

-- Archetyp 5: Minimal Deep Pluck
INSERT INTO archetype_knob_mappings (archetype_id, parameter_name, target_value, acoustic_role) VALUES
(5, 'wt_pos', 0.15, 'Mekky digitalni ton'),
(5, 'filter_cutoff', 0.40, 'Zavrenejsi filtr s kratkym uderem obalky'),
(5, 'filter_resonance', 0.10, 'Hladky bez rezonancnich spicek');
