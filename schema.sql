CREATE DATABASE IF NOT EXISTS anime_club;
USE anime_club;

CREATE TABLE IF NOT EXISTS shelf (
    id INT AUTO_INCREMENT PRIMARY KEY,
    member_name VARCHAR(50) NOT NULL,
    anime_id VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    poster VARCHAR(500),
    status VARCHAR(20) NOT NULL,
    rating INT,
    opinion TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (member_name, anime_id)
);

CREATE TABLE IF NOT EXISTS votes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    month_key VARCHAR(7) NOT NULL,
    member_name VARCHAR(50) NOT NULL,
    anime_id VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (month_key, member_name)
);