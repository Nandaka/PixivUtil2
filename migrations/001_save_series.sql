-- Pixiv Series
CREATE TABLE IF NOT EXISTS pixiv_master_series (
    series_id VARCHAR(255) PRIMARY KEY,
    series_title VARCHAR(255),
    series_type VARCHAR(255),
    series_description TEXT,
    created_date DATE,
    last_update_date DATE
);

CREATE TABLE IF NOT EXISTS pixiv_image_to_series (
    series_id VARCHAR(255) REFERENCES pixiv_master_series(series_id),
    series_order INTEGER,
    image_id INTEGER REFERENCES pixiv_master_image(image_id),
    created_date DATE,
    last_update_date DATE,
    PRIMARY KEY (series_id, series_order),
    UNIQUE (image_id)
);