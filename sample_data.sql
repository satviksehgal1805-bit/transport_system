-- Sample data. Run AFTER schema.sql:
--   mysql -u root -p public_transport < database/sample_data.sql
-- Travel dates are relative to today, so the demo always has upcoming trips.

USE public_transport;

INSERT INTO Passengers (name, email, phone) VALUES
('Aarav Sharma',  'aarav.sharma@example.com',  '9876500001'),
('Diya Patel',    'diya.patel@example.com',    '9876500002'),
('Rohan Verma',   'rohan.verma@example.com',   '9876500003'),
('Ananya Iyer',   'ananya.iyer@example.com',   '9876500004'),
('Kabir Singh',   'kabir.singh@example.com',   '9876500005'),
('Meera Nair',    'meera.nair@example.com',    '9876500006'),
('Ishaan Gupta',  'ishaan.gupta@example.com',  '9876500007'),
('Sara Khan',     'sara.khan@example.com',     '9876500008');

INSERT INTO Routes (route_name, start_point, end_point) VALUES
('R1 City Circular',    'Central Bus Stand',  'Railway Station'),
('R2 Airport Express',  'Railway Station',    'Airport'),
('R3 Campus Line',      'Central Bus Stand',  'University Campus'),
('R4 Tech Park Shuttle','Old Market',         'Tech Park'),
('R5 Lake Road',        'Hospital Junction',  'Lake Road'),
('R6 Ring Road',        'Airport',            'Old Market');

INSERT INTO Buses (route_id, bus_number, capacity) VALUES
(1, 'PT-1001', 40),
(1, 'PT-1002', 40),
(2, 'PT-2001', 30),
(2, 'PT-2002', 30),
(3, 'PT-3001', 36),
(4, 'PT-4001', 24),
(4, 'PT-4002', 24),
(5, 'PT-5001', 32),
(6, 'PT-6001', 40),
(6, 'PT-6002', 40);

INSERT INTO Tickets (passenger_id, bus_id, travel_date, seat_number) VALUES
(1, 1, DATE_ADD(CURDATE(), INTERVAL 1 DAY), 5),
(2, 1, DATE_ADD(CURDATE(), INTERVAL 1 DAY), 6),
(7, 1, DATE_ADD(CURDATE(), INTERVAL 1 DAY), 7),
(3, 1, DATE_ADD(CURDATE(), INTERVAL 2 DAY), 12),
(4, 2, DATE_ADD(CURDATE(), INTERVAL 1 DAY), 1),
(5, 3, DATE_ADD(CURDATE(), INTERVAL 1 DAY), 10),
(6, 3, DATE_ADD(CURDATE(), INTERVAL 1 DAY), 11),
(1, 3, DATE_ADD(CURDATE(), INTERVAL 3 DAY), 2),
(7, 4, DATE_ADD(CURDATE(), INTERVAL 2 DAY), 7),
(8, 5, DATE_ADD(CURDATE(), INTERVAL 1 DAY), 20),
(2, 5, DATE_ADD(CURDATE(), INTERVAL 4 DAY), 21),
(3, 6, DATE_ADD(CURDATE(), INTERVAL 1 DAY), 3),
(4, 8, DATE_ADD(CURDATE(), INTERVAL 2 DAY), 15),
(6, 9, DATE_ADD(CURDATE(), INTERVAL 1 DAY), 30),
(5, 10, DATE_ADD(CURDATE(), INTERVAL 5 DAY), 8),
(1, 2, DATE_SUB(CURDATE(), INTERVAL 3 DAY), 4);
