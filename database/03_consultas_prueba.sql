-- =========================================================
-- CONSULTAS DE PRUEBA
-- Sirven para comprobar que la base de datos funciona.
-- =========================================================

USE hotel_costa_azul;

-- Ver todas las habitaciones
SELECT * FROM habitaciones;

-- Ver solo habitaciones disponibles para el cliente
SELECT * FROM habitaciones
WHERE estado = 'Disponible';

-- Probar bloqueo de una habitación
UPDATE habitaciones
SET estado = 'Bloqueada'
WHERE numero = '102';

-- Verificar que la habitación 102 quedó bloqueada
SELECT * FROM habitaciones
WHERE numero = '102';

-- Verificar que la habitación bloqueada ya no sale como disponible
SELECT * FROM habitaciones
WHERE estado = 'Disponible';

-- Devolver la habitación 102 a disponible
UPDATE habitaciones
SET estado = 'Disponible'
WHERE numero = '102';