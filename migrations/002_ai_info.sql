-- image ID is primary key, may not reference to pixiv_master_image as it may not
-- be downloaded. Used for filtering out AI images.
CREATE TABLE IF NOT EXISTS pixiv_ai_info (
    image_id INTEGER PRIMARY KEY,
    ai_type INTEGER,
    created_date DATE,
    last_update_date DATE
);