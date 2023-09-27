BEGIN;

create table students(id text primary key, name text, age int);

insert into students values
  ('aaa', 'Alex', 10),
  ('bbb', 'Brian', 20),
  ('ccc', 'Craig', 30);

COMMIT;
