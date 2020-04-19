drop database if exists web_app;
create database web_app;
use web_app;
CREATE USER 'Aileon'@'localhost' identified by '767872313';
grant select, insert, update, delete on web_app.* to 'Aileon'@'localhost';

-- CREATE TABLE `news` (
--   `id` int(11) NOT NULL AUTO_INCREMENT,
--   `name` varchar(50) NOT NULL,
--   `sex` varchar(1) DEFAULT NULL,
--   `borndate` datetime DEFAULT NULL,
--   `phone` varchar(11) NOT NULL,
--   `photo` tinyint(1) DEFAULT NULL,
--   PRIMARY KEY (`id`),
--   CONSTRAINT `news_chk_1` CHECK ((`photo` in (0,1)))
-- ) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=gbk;

create table users (
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `passwd` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_at` real not null,
    unique key `idx_email` (`email`),
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table blogs (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `name` varchar(50) not null,
    `summary` varchar(200) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table comments (
    `id` varchar(50) not null,
    `blog_id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;