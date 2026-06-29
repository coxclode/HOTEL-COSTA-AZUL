-- Migracion Sprint 3 real: pagos, proveedor externo y correo.
-- Ejecutar una vez sobre una base existente antes de usar el flujo de pago real.

ALTER TABLE reservas
    ADD COLUMN IF NOT EXISTS cantidad_personas INT NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS pagos (
    id_pago        SERIAL PRIMARY KEY,
    id_reserva     INT             NOT NULL REFERENCES reservas(id_reserva),
    codigo_operacion VARCHAR(30)   NOT NULL UNIQUE,
    proveedor_transaccion_id VARCHAR(100) DEFAULT NULL,
    proveedor_estado VARCHAR(50)    DEFAULT NULL,
    metodo_pago    VARCHAR(30)     NOT NULL,
    monto          DECIMAL(10,2)   NOT NULL,
    estado         VARCHAR(20)     NOT NULL,
    proveedor_respuesta JSONB       DEFAULT NULL,
    correo_enviado BOOLEAN         NOT NULL DEFAULT FALSE,
    fecha_correo   TIMESTAMP       DEFAULT NULL,
    fecha_pago     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE pagos
    ADD COLUMN IF NOT EXISTS proveedor_transaccion_id VARCHAR(100) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS proveedor_estado VARCHAR(50) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS proveedor_respuesta JSONB DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS correo_enviado BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS fecha_correo TIMESTAMP DEFAULT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_metodo_pago'
    ) THEN
        ALTER TABLE pagos
            ADD CONSTRAINT chk_metodo_pago
            CHECK (metodo_pago IN ('tarjeta', 'transferencia'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_estado_pago'
    ) THEN
        ALTER TABLE pagos
            ADD CONSTRAINT chk_estado_pago
            CHECK (estado IN ('exitoso', 'rechazado'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_monto_pago_no_negativo'
    ) THEN
        ALTER TABLE pagos
            ADD CONSTRAINT chk_monto_pago_no_negativo
            CHECK (monto >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_cantidad_personas_positiva'
    ) THEN
        ALTER TABLE reservas
            ADD CONSTRAINT chk_cantidad_personas_positiva
            CHECK (cantidad_personas > 0);
    END IF;
END $$;
