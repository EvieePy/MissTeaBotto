CREATE TABLE IF NOT EXISTS tokens(
    user_id TEXT PRIMARY KEY,
    access_token TEXT UNIQUE NOT NULL,
    refresh_token TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS gambles(
    user_id TEXT PRIMARY KEY,
    points BIGINT DEFAULT 0
);