-- =========================================================
-- DATOS DE PRUEBA
-- Habitaciones iniciales para probar HU15 y HU18
-- =========================================================

USE hotel_costa_azul;

DELETE FROM habitaciones;

ALTER TABLE habitaciones AUTO_INCREMENT = 1;

INSERT INTO habitaciones 
(numero, tipo, precio_base, descripcion, estado, capacidad, imagen)
VALUES
(
    '101',
    'Simple',
    120.00,
    'Habitación simple con cama individual, baño privado y WiFi.',
    'Disponible',
    1,
    'habitacion_simple.jpg'
),
(
    '102',
    'Doble',
    180.00,
    'Habitación doble con dos camas, baño privado, TV y WiFi.',
    'Disponible',
    2,
    'habitacion_doble.jpg'
),
(
    '201',
    'Suite',
    320.00,
    'Suite amplia con cama queen, sala pequeña, minibar y vista exterior.',
    'Disponible',
    2,
    'habitacion_suite.jpg'
);

SELECT * FROM habitaciones;