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
    'Disponible', 1,
    'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80&fit=crop'
),
(
    '102', 'Doble', 180.00,
    'Habitación doble con dos camas individuales, baño privado, TV, escritorio y WiFi.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=800&q=80&fit=crop'
),
(
    '103', 'Doble', 195.00,
    'Habitación doble con cama matrimonial, baño privado, TV, frigobar y WiFi.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&q=80&fit=crop'
),
(
    '201', 'Suite', 320.00,
    'Suite amplia con cama king, sala de estar, minibar, jacuzzi y vista al mar.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80&fit=crop'
),
(
    '202', 'Suite', 350.00,
    'Suite premium con terraza privada, cama king, sala, minibar y vista panorámica.',
    'Disponible', 3,
    'https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800&q=80&fit=crop'
),
(
    '301', 'Simple', 110.00,
    'Habitación simple acogedora con cama individual, baño privado y WiFi.',
    'Bloqueada', 1,
    'https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=800&q=80&fit=crop'
);

-- ── Reservas de prueba para demostrar HU17 (notificaciones) ──
INSERT INTO reservas (
    codigo_reserva, id_habitacion,
    nombre_cliente, apellido_cliente, dni_cliente,
    correo_cliente, telefono_cliente,
    fecha_checkin, fecha_checkout, precio_total, estado
)
VALUES
(
    'RES-DEMO01', 1,
    'Carlos', 'Mendoza García', '45678901',
    'carlos.mendoza@gmail.com', '987654321',
    CURRENT_DATE + INTERVAL '2 days',
    CURRENT_DATE + INTERVAL '5 days',
    360.00, 'pendiente'
),
(
    'RES-DEMO02', 3,
    'María', 'Torres Quispe', '52341678',
    'maria.torres@outlook.com', '943215678',
    CURRENT_DATE + INTERVAL '1 day',
    CURRENT_DATE + INTERVAL '4 days',
    585.00, 'pendiente'
);

-- ── Notificaciones de prueba para el panel de recepción (HU17) ──
INSERT INTO notificaciones (id_reserva, tipo, leido)
VALUES
(1, 'nueva_reserva', FALSE),
(2, 'nueva_reserva', FALSE);
