-- Fiber e2e seed: create a table with 1000 rows of random data
CREATE TABLE IF NOT EXISTS e2e_data (
    id   SERIAL PRIMARY KEY,
    val  TEXT NOT NULL
);

INSERT INTO e2e_data (val)
SELECT md5(random()::text)
FROM generate_series(1, 1000);
