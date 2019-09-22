-- drop table gang_session;
create table gang_session (
id INTEGER PRIMARY KEY AUTOINCREMENT,
guild TEXT NOT NULL,
loot TEXT NOT NULL,
start_time timestamp NOT NULL,
stop_time INTEGER,
money INTEGER
);




-- drop table gang_members;
create table gang_members (
id INTEGER PRIMARY KEY AUTOINCREMENT,
session_id INTEGER NOT NULL,
start_time timestamp NOT NULL,
stop_time INTEGER,
user_id INTEGER NOT NULL,
got_money INTEGER
);
