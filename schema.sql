-- Public Transport System : database schema (MySQL 8.0+)
--
-- Run:  mysql -u root -p < database/schema.sql
-- WARNING: re-running this file drops the four tables and all their data.

CREATE DATABASE IF NOT EXISTS public_transport CHARACTER SET utf8mb4;
USE public_transport;

-- Drop in reverse dependency order (children first)
DROP TABLE IF EXISTS Tickets;
DROP TABLE IF EXISTS Buses;
DROP TABLE IF EXISTS Routes;
DROP TABLE IF EXISTS Passengers;

-- A person who travels. Email is unique so one person = one row.
CREATE TABLE Passengers (
    passenger_id INT          NOT NULL AUTO_INCREMENT,
    name         VARCHAR(100) NOT NULL,
    email        VARCHAR(100) NOT NULL,
    phone        VARCHAR(15)  NOT NULL,
    PRIMARY KEY (passenger_id),
    UNIQUE (email)
) ENGINE=InnoDB;

-- A named path from one stop to another.
CREATE TABLE Routes (
    route_id    INT          NOT NULL AUTO_INCREMENT,
    route_name  VARCHAR(100) NOT NULL,
    start_point VARCHAR(100) NOT NULL,
    end_point   VARCHAR(100) NOT NULL,
    PRIMARY KEY (route_id)
) ENGINE=InnoDB;

-- A physical bus that runs on exactly one route.
CREATE TABLE Buses (
    bus_id     INT         NOT NULL AUTO_INCREMENT,
    route_id   INT         NOT NULL,
    bus_number VARCHAR(20) NOT NULL,
    capacity   INT         NOT NULL,
    PRIMARY KEY (bus_id),
    UNIQUE (bus_number),
    CHECK (capacity > 0),
    FOREIGN KEY (route_id) REFERENCES Routes (route_id)
) ENGINE=InnoDB;

-- One seat, on one bus, on one day, for one passenger.
-- The UNIQUE key makes double-booking a seat impossible, even if two
-- people click "book" at the same moment.
CREATE TABLE Tickets (
    ticket_id    INT  NOT NULL AUTO_INCREMENT,
    passenger_id INT  NOT NULL,
    bus_id       INT  NOT NULL,
    travel_date  DATE NOT NULL,
    seat_number  INT  NOT NULL,
    PRIMARY KEY (ticket_id),
    UNIQUE (bus_id, travel_date, seat_number),
    CHECK (seat_number > 0),
    FOREIGN KEY (passenger_id) REFERENCES Passengers (passenger_id),
    FOREIGN KEY (bus_id)       REFERENCES Buses (bus_id)
) ENGINE=InnoDB;

-- Foreign keys use the default ON DELETE RESTRICT: you cannot delete a route
-- that still has buses, or a bus/passenger that still has tickets.
