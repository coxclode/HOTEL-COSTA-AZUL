-- =========================================================
-- BASE DE DATOS: Hotel Costa Azul
-- Proyecto: Sistema de Reservas Web
-- Curso: Agile Development
-- Sprint 1: HU15 y HU18
-- 
-- HU15: Gestión de habitaciones y precios
-- HU18: Gestión de disponibilidad de habitaciones
-- =========================================================

CREATE DATABASE IF NOT EXISTS hotel_costa_azul
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE hotel_costa_azul;

-- =========================================================
-- TABLA: habitaciones
-- Esta tabla almacena las habitaciones del hotel.
-- Sirve para registrar habitaciones, precios, tipos
-- y controlar si están disponibles o bloqueadas.
-- =========================================================

CREATE TABLE IF NOT EXISTS habitaciones (
    id_habitacion INT AUTO_INCREMENT PRIMARY KEY,

    numero VARCHAR(10) NOT NULL UNIQUE,

    tipo ENUM('Simple', 'Doble', 'Suite') NOT NULL,

    precio_base DECIMAL(10,2) NOT NULL,

    descripcion VARCHAR(255) NOT NULL,

    estado ENUM('Disponible', 'Bloqueada', 'Mantenimiento') 
        NOT NULL DEFAULT 'Disponible',

    capacidad INT NOT NULL DEFAULT 1,

    imagen VARCHAR(255) DEFAULT NULL,

    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    fecha_actualizacion TIMESTAMP 
        DEFAULT CURRENT_TIMESTAMP 
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_precio_base_no_negativo 
        CHECK (precio_base >= 0),

    CONSTRAINT chk_capacidad_positiva 
        CHECK (capacidad > 0)
);