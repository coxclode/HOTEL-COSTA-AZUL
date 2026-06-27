-- =========================================================
-- BASE DE DATOS: Hotel Costa Azul
-- Motor: PostgreSQL (Neon - Vercel)
-- Sprint 1: HU15, HU18, HU2, HU17
-- Sprint 2: HU3, HU4, HU5, HU6
-- Sprint 3: HU7, HU9, HU10
-- =========================================================

-- TABLA: habitaciones (HU15, HU18)
CREATE TABLE IF NOT EXISTS habitaciones (
    id_habitacion   SERIAL PRIMARY KEY,
    numero          VARCHAR(10)     NOT NULL UNIQUE,
    tipo            VARCHAR(10)     NOT NULL,
    precio_base     DECIMAL(10,2)   NOT NULL,
    descripcion     VARCHAR(255)    NOT NULL,
    estado          VARCHAR(20)     NOT NULL DEFAULT 'Disponible',
    capacidad       INT             NOT NULL DEFAULT 1,
    imagen          VARCHAR(255)    DEFAULT NULL,
    fecha_creacion      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_tipo_habitacion
        CHECK (tipo IN ('Simple', 'Doble', 'Suite')),
    CONSTRAINT chk_estado_habitacion
        CHECK (estado IN ('Disponible', 'Bloqueada', 'Mantenimiento')),
    CONSTRAINT chk_precio_no_negativo
        CHECK (precio_base >= 0),
    CONSTRAINT chk_capacidad_positiva
        CHECK (capacidad > 0)
);

-- TABLA: reservas (HU6, HU7)
CREATE TABLE IF NOT EXISTS reservas (
    id_reserva      SERIAL PRIMARY KEY,
    codigo_reserva  VARCHAR(20)     NOT NULL UNIQUE,
    id_habitacion   INT             NOT NULL REFERENCES habitaciones(id_habitacion),
    nombre_cliente  VARCHAR(100)    NOT NULL,
    apellido_cliente VARCHAR(100)   NOT NULL,
    dni_cliente     VARCHAR(20)     NOT NULL,
    correo_cliente  VARCHAR(150)    NOT NULL,
    telefono_cliente VARCHAR(20)    NOT NULL,
    cantidad_personas INT           NOT NULL DEFAULT 1,
    fecha_checkin   DATE            NOT NULL,
    fecha_checkout  DATE            NOT NULL,
    precio_total    DECIMAL(10,2)   NOT NULL,
    estado          VARCHAR(20)     NOT NULL DEFAULT 'pendiente',
    fecha_creacion  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_estado_reserva
        CHECK (estado IN ('pendiente','confirmada','en_hospedaje','finalizada','cancelada','rechazado')),
    CONSTRAINT chk_fechas_validas
        CHECK (fecha_checkout > fecha_checkin),
    CONSTRAINT chk_cantidad_personas_positiva
        CHECK (cantidad_personas > 0)
);

-- TABLA: pagos (HU9, HU10)
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
    fecha_pago     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_metodo_pago
        CHECK (metodo_pago IN ('tarjeta', 'transferencia')),
    CONSTRAINT chk_estado_pago
        CHECK (estado IN ('exitoso', 'rechazado')),
    CONSTRAINT chk_monto_pago_no_negativo
        CHECK (monto >= 0)
);

-- TABLA: notificaciones (HU17)
CREATE TABLE IF NOT EXISTS notificaciones (
    id_notificacion SERIAL PRIMARY KEY,
    id_reserva      INT             NOT NULL REFERENCES reservas(id_reserva),
    tipo            VARCHAR(50)     NOT NULL DEFAULT 'nueva_reserva',
    leido           BOOLEAN         NOT NULL DEFAULT FALSE,
    fecha_creacion  TIMESTAMP       DEFAULT CURRENT_TIMESTAMP
);
