-- =========================================================
-- DATOS DE PRUEBA: Hotel Costa Azul (PostgreSQL)
-- Ejecutar DESPUÉS de postgres_schema.sql
-- =========================================================

TRUNCATE TABLE notificaciones, pagos, reservas, habitaciones RESTART IDENTITY CASCADE;

INSERT INTO habitaciones (numero, tipo, precio_base, descripcion, estado, capacidad, imagen)
VALUES
(
    '101', 'Simple', 120.00,
    'Habitación simple con cama individual, baño privado, TV y WiFi de alta velocidad.',
    'Disponible', 1,
    'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800&q=80&fit=crop'
),
(
    '102', 'Simple', 115.00,
    'Habitación simple luminosa con cama individual, baño privado, aire acondicionado y WiFi.',
    'Disponible', 1,
    'https://images.unsplash.com/photo-1505693314120-0d443867891c?w=800&q=80&fit=crop'
),
(
    '103', 'Simple', 125.00,
    'Habitación simple con vista al jardín, cama individual, baño privado y WiFi.',
    'Disponible', 1,
    'https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?w=800&q=80&fit=crop'
),
(
    '104', 'Simple', 108.00,
    'Habitación simple económica con cama individual, baño privado y WiFi.',
    'Disponible', 1,
    'https://images.unsplash.com/photo-1540518614846-7eded433c457?w=800&q=80&fit=crop'
),
(
    '201', 'Doble', 180.00,
    'Habitación doble con dos camas individuales, baño privado, TV, escritorio y WiFi.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=800&q=80&fit=crop'
),
(
    '202', 'Doble', 195.00,
    'Habitación doble con cama matrimonial, baño privado, TV, frigobar y WiFi.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800&q=80&fit=crop'
),
(
    '203', 'Doble', 185.00,
    'Habitación doble con dos camas twin, escritorio amplio, baño privado y WiFi.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1574643156929-51fa098b0394?w=800&q=80&fit=crop'
),
(
    '204', 'Doble', 200.00,
    'Habitación doble con cama matrimonial king, baño con tina, frigobar y WiFi.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=800&q=80&fit=crop'
),
(
    '301', 'Suite', 320.00,
    'Suite amplia con cama king, sala de estar, minibar, jacuzzi y vista al mar.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800&q=80&fit=crop'
),
(
    '302', 'Suite', 350.00,
    'Suite premium con terraza privada, cama king, sala, minibar y vista panorámica.',
    'Disponible', 3,
    'https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800&q=80&fit=crop'
),
(
    '303', 'Suite', 300.00,
    'Suite junior con sala de estar, cama king, jacuzzi y vista a la ciudad.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=800&q=80&fit=crop'
),
(
    '304', 'Suite', 380.00,
    'Suite presidencial con terraza panorámica, sala, comedor, cama king y jacuzzi.',
    'Disponible', 4,
    'https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800&q=80&fit=crop'
),
(
    '105', 'Simple', 118.00,
    'Habitación simple con escritorio, baño privado, WiFi y vista interior tranquila.',
    'Disponible', 1,
    'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&q=80&fit=crop'
),
(
    '106', 'Simple', 130.00,
    'Habitación simple superior con cama plaza y media, aire acondicionado y TV.',
    'Disponible', 1,
    'https://images.unsplash.com/photo-1560448075-bb485b067938?w=800&q=80&fit=crop'
),
(
    '107', 'Simple', 112.00,
    'Habitación simple compacta con baño privado, WiFi y desayuno incluido.',
    'Disponible', 1,
    'https://images.unsplash.com/photo-1551776235-dde6d482980b?w=800&q=80&fit=crop'
),
(
    '108', 'Simple', 135.00,
    'Habitación simple ejecutiva con escritorio amplio, TV y buena iluminación natural.',
    'Disponible', 1,
    'https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=800&q=80&fit=crop'
),
(
    '205', 'Doble', 210.00,
    'Habitación doble familiar con cama matrimonial, cama individual y baño privado.',
    'Disponible', 3,
    'https://images.unsplash.com/photo-1598928636135-d146006ff4be?w=800&q=80&fit=crop'
),
(
    '206', 'Doble', 175.00,
    'Habitación doble estándar con dos camas, ventilación natural y WiFi.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1584132967334-10e028bd69f7?w=800&q=80&fit=crop'
),
(
    '207', 'Doble', 220.00,
    'Habitación doble superior con frigobar, TV, escritorio y vista a la ciudad.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1595576508898-0ad5c879a061?w=800&q=80&fit=crop'
),
(
    '208', 'Doble', 230.00,
    'Habitación doble premium con cama queen, baño moderno y zona de trabajo.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800&q=80&fit=crop'
),
(
    '305', 'Suite', 340.00,
    'Suite ejecutiva con sala pequeña, cama king, minibar y baño con tina.',
    'Disponible', 3,
    'https://images.unsplash.com/photo-1590490359683-658d3d23f972?w=800&q=80&fit=crop'
),
(
    '306', 'Suite', 360.00,
    'Suite familiar con dos ambientes, cama king, sofá cama y vista al jardín.',
    'Disponible', 4,
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&q=80&fit=crop'
),
(
    '307', 'Suite', 390.00,
    'Suite deluxe con terraza, jacuzzi, minibar y sala de estar independiente.',
    'Disponible', 4,
    'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=800&q=80&fit=crop'
),
(
    '308', 'Suite', 310.00,
    'Suite junior acogedora con cama king, escritorio, baño privado y WiFi.',
    'Disponible', 2,
    'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&q=80&fit=crop'
),
(
    '401', 'Simple', 110.00,
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
    'RES-DEMO02', 5,
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
