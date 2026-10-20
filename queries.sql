-- Useful queries for the Public Transport System (for viva / demo).
USE public_transport;

-- 1. Full ticket details (joins all four tables)
SELECT t.ticket_id, p.name AS passenger, r.route_name, b.bus_number,
       t.travel_date, t.seat_number
FROM Tickets t
JOIN Passengers p ON p.passenger_id = t.passenger_id
JOIN Buses b      ON b.bus_id       = t.bus_id
JOIN Routes r     ON r.route_id     = b.route_id
ORDER BY t.travel_date, r.route_name, t.seat_number;

-- 2. Buses on a given route
SELECT b.bus_number, b.capacity
FROM Buses b JOIN Routes r ON r.route_id = b.route_id
WHERE r.route_name = 'R1 City Circular';

-- 3. Seats still free on every bus for tomorrow
SELECT b.bus_number, b.capacity,
       b.capacity - COUNT(t.ticket_id) AS seats_free
FROM Buses b
LEFT JOIN Tickets t
       ON t.bus_id = b.bus_id AND t.travel_date = DATE_ADD(CURDATE(), INTERVAL 1 DAY)
GROUP BY b.bus_id, b.bus_number, b.capacity;

-- 4. Number of buses per route (including routes with none)
SELECT r.route_name, COUNT(b.bus_id) AS buses
FROM Routes r LEFT JOIN Buses b ON b.route_id = r.route_id
GROUP BY r.route_id, r.route_name;

-- 5. Passengers ranked by number of tickets
SELECT p.name, COUNT(*) AS tickets
FROM Passengers p JOIN Tickets t ON t.passenger_id = p.passenger_id
GROUP BY p.passenger_id, p.name
ORDER BY tickets DESC;

-- 6. Passengers who have never booked
SELECT p.name, p.email
FROM Passengers p LEFT JOIN Tickets t ON t.passenger_id = p.passenger_id
WHERE t.ticket_id IS NULL;

-- 7. Busiest route (most tickets)
SELECT r.route_name, COUNT(t.ticket_id) AS tickets
FROM Routes r
JOIN Buses b   ON b.route_id = r.route_id
JOIN Tickets t ON t.bus_id   = b.bus_id
GROUP BY r.route_id, r.route_name
ORDER BY tickets DESC
LIMIT 1;

-- 8. Proof that double booking is blocked (the second insert fails with error 1062)
-- INSERT INTO Tickets (passenger_id, bus_id, travel_date, seat_number)
-- VALUES (1, 1, DATE_ADD(CURDATE(), INTERVAL 1 DAY), 5);
