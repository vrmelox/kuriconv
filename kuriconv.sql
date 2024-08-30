CREATE DATABASE IF NOT EXISTS `kuriconv`;
USE `kuriconv`;

CREATE TABLE devise_rates (
    id INT NOT NULL AUTO_INCREMENT,
    devise VARCHAR(20) NOT NULL UNIQUE,
    devise_name VARCHAR(150) NOT NULL,
    rates DECIMAL(10,4) NOT NULL,
    date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

CREATE TABLE rates_history (
    id INT NOT NULL AUTO_INCREMENT,
    devise VARCHAR(20) NOT NULL UNIQUE,
    devise_name VARCHAR(150) NOT NULL,
    rates DECIMAL(10,4) NOT NULL,
    date DATETIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(devise) REFERENCES devise_rates(devise)
);

INSERT INTO devise_rates (devise, devise_name, rates)
VALUES ('USD', 'Dollar américain', 1.1000);