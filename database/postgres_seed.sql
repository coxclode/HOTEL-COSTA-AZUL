-- =========================================================
-- DATOS DE PRUEBA: Hotel Costa Azul (PostgreSQL)
-- Ejecutar DESPUÉS de postgres_schema.sql
-- =========================================================

TRUNCATE TABLE notificaciones, reservas, habitaciones RESTART IDENTITY CASCADE;

INSERT INTO habitaciones (numero, tipo, precio_base, descripcion, estado, capacidad, imagen)
VALUES
(
    '101', 'Simple', 120.00,
    'Habitación simple con cama individual, baño privado, TV y WiFi de alta velocidad.',
    'Disponible', 1, NULL
),
(
    '102', 'Doble', 180.00,
    'Habitación doble con dos camas, baño privado, TV, escritorio y WiFi.',
    'Disponible', 2, NULL
),
(
    '103', 'Doble', 195.00,
    'Habitación doble con cama matrimonial, baño privado, TV, frigobar y WiFi.',
    'Disponible', 2, NULL
),
(
    '201', 'Suite', 320.00,
    'Suite amplia con cama king, sala de estar, minibar, jacuzzi y vista al mar.',
    'Disponible', 2, NULL
),
(
    '202', 'Suite', 350.00,
    'Suite premium con terraza privada, cama king, sala, minibar y vista panorámica.',
    'Disponible', 3, NULL
),
(
    '301', 'Simple', 110.00,
    'Habitación simple acogedora con cama individual, baño privado y WiFi.',
    'Bloqueada', 1, NULL
);
