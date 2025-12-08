CREATE TABLE IF NOT EXISTS pixiv_master_member (
    member_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
    name TEXT,
    save_folder TEXT,
    created_date DATE,
    last_update_date DATE,
    last_image INTEGER
);

-- add column isDeleted
-- 0 = false, 1 = true
ALTER TABLE
    pixiv_master_member
ADD
    COLUMN is_deleted INTEGER DEFAULT 0;

-- add column for artist token
ALTER TABLE
    pixiv_master_member
ADD
    COLUMN member_token TEXT;

CREATE TABLE IF NOT EXISTS pixiv_master_image (
    image_id INTEGER PRIMARY KEY,
    member_id INTEGER,
    title TEXT,
    save_name TEXT,
    created_date DATE,
    last_update_date DATE
);

-- add column isManga
ALTER TABLE
    pixiv_master_image
ADD
    COLUMN is_manga TEXT;

-- add column caption
ALTER TABLE
    pixiv_master_image
ADD
    COLUMN caption TEXT;

CREATE TABLE IF NOT EXISTS pixiv_manga_image (
    image_id INTEGER,
    page INTEGER,
    save_name TEXT,
    created_date DATE,
    last_update_date DATE,
    PRIMARY KEY (image_id, page)
);

-- Pixiv Tags
CREATE TABLE IF NOT EXISTS pixiv_master_tag (
    tag_id VARCHAR(255) PRIMARY KEY,
    created_date DATE,
    last_update_date DATE
);

CREATE TABLE IF NOT EXISTS pixiv_tag_translation (
    tag_id VARCHAR(255) REFERENCES pixiv_master_tag(tag_id),
    translation_type VARCHAR(255),
    translation VARCHAR(255),
    created_date DATE,
    last_update_date DATE,
    PRIMARY KEY (tag_id, translation_type)
);

-- FANBOX
CREATE TABLE IF NOT EXISTS fanbox_master_post (
    member_id INTEGER,
    post_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
    title TEXT,
    fee_required INTEGER,
    published_date DATE,
    updated_date DATE,
    post_type TEXT,
    last_update_date DATE
);

CREATE TABLE IF NOT EXISTS fanbox_post_image (
    post_id INTEGER,
    page INTEGER,
    save_name TEXT,
    created_date DATE,
    last_update_date DATE,
    PRIMARY KEY (post_id, page)
);

-- Sketch
CREATE TABLE IF NOT EXISTS sketch_master_post (
    member_id INTEGER,
    post_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
    title TEXT,
    published_date DATE,
    updated_date DATE,
    post_type TEXT,
    last_update_date DATE
);
CREATE TABLE IF NOT EXISTS sketch_post_image (
    post_id INTEGER,
    page INTEGER,
    save_name TEXT,
    created_date DATE,
    last_update_date DATE,
    PRIMARY KEY (post_id, page)
);