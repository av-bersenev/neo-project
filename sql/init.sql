CREATE TABLE IF NOT EXISTS dim_heroes (
    hero_id INT PRIMARY KEY,
    name VARCHAR(64) NOT NULL,
    localized_name VARCHAR(64) NOT NULL,
    primary_attr VARCHAR(16),
    attack_type VARCHAR(16),
    roles TEXT [],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_dim_heroes_localized_name ON dim_heroes(localized_name);