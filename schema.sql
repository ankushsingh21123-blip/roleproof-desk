PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sessions (
 id TEXT PRIMARY KEY CHECK(length(id)=64),
 expires_at INTEGER NOT NULL,
 write_window INTEGER NOT NULL DEFAULT 0,
 write_count INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
CREATE TABLE IF NOT EXISTS tickets (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
 title TEXT NOT NULL CHECK(length(title) BETWEEN 3 AND 120),
 description TEXT NOT NULL CHECK(length(description) BETWEEN 5 AND 2000),
 category TEXT NOT NULL CHECK(category IN ('Account','Billing','Product','Other')),
 priority TEXT NOT NULL CHECK(priority IN ('High','Medium','Low')),
 status TEXT NOT NULL CHECK(status IN ('Open','In progress','Resolved')),
 version INTEGER NOT NULL DEFAULT 1 CHECK(version>0),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS tickets_session ON tickets(session_id);
