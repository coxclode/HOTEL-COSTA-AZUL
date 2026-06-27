-- =========================================================
-- Sprint 4: Métodos de pago múltiples y pago mixto
-- Hotel Costa Azul · PostgreSQL (Neon)
-- =========================================================

BEGIN;

-- 1. Ampliar métodos de pago permitidos
ALTER TABLE pagos DROP CONSTRAINT IF EXISTS chk_metodo_pago;
ALTER TABLE pagos ADD CONSTRAINT chk_metodo_pago
    CHECK (metodo_pago IN (
        'efectivo',
        'yape',
        'plin',
        'tarjeta_credito',
        'tarjeta_debito',
        'transferencia'
    ));

-- 2. Columnas para pago en efectivo
ALTER TABLE pagos
    ADD COLUMN IF NOT EXISTS monto_entregado DECIMAL(10,2) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS vuelto          DECIMAL(10,2) DEFAULT NULL;

-- 3. Número de operación para Yape / Plin / Transferencia
ALTER TABLE pagos
    ADD COLUMN IF NOT EXISTS numero_operacion VARCHAR(60) DEFAULT NULL;

-- 4. Índices de rendimiento
CREATE INDEX IF NOT EXISTS idx_pagos_id_reserva ON pagos(id_reserva);
CREATE INDEX IF NOT EXISTS idx_pagos_estado      ON pagos(estado);
CREATE INDEX IF NOT EXISTS idx_reservas_estado   ON reservas(estado);

COMMIT;
