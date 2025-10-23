! rm -f metropolis.db gotham.db superman-files.db batman-files.db luthor-files.db internal.db

attach database 'metropolis.db' as metropolis;
create table metropolis.heros(
  name text,
  powers text
);
insert into metropolis.heros (name, powers) values
  ('superman', 'flight, super strength, x-ray vision'),
  ('supergirl', 'flight, super strength, heat vision');


attach database 'gotham.db' as gotham;
create table gotham.villains(
  name text,
  crimes text
);
insert into gotham.villains (name, crimes) values
  ('joker', 'theft, murder, chaos'),
  ('penguin', 'theft, smuggling');

attach database 'superman-files.db' as superman;
create table superman.superman_sightings(
  sighted_at date,
  description text
);
insert into superman.superman_sightings values
  ('2025-10-20', 'Saved a bus from falling off a bridge'),
  ('2025-10-21', 'Stopped a bank robbery downtown');

attach database 'batman-files.db' as batman;
create table batman.accomplices(
  name text,
  description text
);
insert into batman.accomplices values
  ('Robin', 'The Boy Wonder, trusted sidekick'),
  ('Alfred', 'Butler and confidant');

attach database 'luthor-files.db' as luthor;
create table luthor.crimes(
  ocurred_at date,
  location text,
  description text
);
insert into luthor.crimes values
  ('2025-10-15', 'LexCorp Tower', 'Unauthorized kryptonite experiments'),
  ('2025-10-18', 'Metropolis Bank', 'Embezzlement scheme');
  


! uv run sqlite-utils migrate internal.db datasette_comments/internal_migrations.py
attach database "internal.db" as internal;
INSERT INTO datasette_comments_threads VALUES
  ('01k876xkvyk0za7dj95t52mfkk','2025-10-23 00:18:54','alfred','row','gotham','villains','["1"]',NULL,NULL);

INSERT INTO datasette_comments_comments VALUES
  ('01k876xkw00a3y001gk2z29rt9','01k876xkvyk0za7dj95t52mfkk','2025-10-23 00:18:54','2025-10-23 00:18:54','alfred','What is going on here??? #confusion','[]','["confusion"]','[]'),
  ('01k876xkw00a3y001gk2z29rt0','01k876xkvyk0za7dj95t52mfkk','2025-10-23 00:19:54','2025-10-23 00:19:54','bruce','Bro I can explain','[]','[]','[]');