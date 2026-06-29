# HOTEL-COSTA-AZUL

Sistema de reservas web para el Hotel Costa Azul - Trujillo, Peru.
Desarrollado en el curso de Agile Development (ISIA-109) - UPAO.

## Estructura del proyecto

- `backend/`   → Flask REST API (Python + PostgreSQL)
- `frontend/`  → HTML + CSS + JS
- `database/`  → Scripts SQL (PostgreSQL / Neon)

## HU cubiertas (Sprint 1 + Sprint 2 + Sprint 3)

HU15, HU18, HU2, HU17, HU3, HU4, HU5, HU6, HU7, HU9, HU10

---

## Flujo del cliente — Botones web

### 1. Página principal (`index.html`)
| Botón / Acción | Descripción |
|---|---|
| **Buscar habitaciones** | Filtra por tipo, precio mínimo/máximo, check-in, check-out y número de personas |
| **Ver detalle** (tarjeta) | Abre la ficha completa de la habitación (HU3) |
| **Seleccionar** (detalle) | Guarda la habitación elegida y avanza al paso "Tus datos" (HU4) |

### 2. Catálogo (`catalogo.html`)
| Botón / Acción | Descripción |
|---|---|
| **Buscar** | Aplica los filtros de búsqueda en tiempo real |
| **Ver detalle / Seleccionar** | Igual que en la página principal |

### 3. Formulario de datos del cliente (`datos.html` — HU5)
| Botón / Campo | Descripción |
|---|---|
| Campo **DNI** | Solo acepta dígitos (0–9). Máximo 8 dígitos exactos. Consulta RENIEC automáticamente al completar los 8 dígitos |
| Campo **Teléfono** | Solo acepta dígitos (0–9). Exactamente 9 dígitos (formato Perú) |
| **← Volver** | Regresa a la selección de habitaciones |
| **Continuar → Confirmar** | Valida todos los campos y avanza al resumen de reserva |

### 4. Confirmar reserva (`confirmar.html` — HU6)
| Botón / Acción | Descripción |
|---|---|
| **← Editar datos** | Regresa al formulario de datos |
| **Generar reserva y pagar** | Envía la reserva al servidor y redirige al pago. Se bloquea automáticamente si ya existe una reserva generada para evitar duplicados |

### 5. Pago (`pago.html` — HU9)
| Botón / Tab | Descripción |
|---|---|
| Tab **💵 Efectivo** | Registra pago en efectivo; calcula vuelto en tiempo real |
| Tab **📱 Yape** | Muestra QR Yape; requiere ingresar número de operación |
| Tab **📱 Plin** | Muestra QR Plin; requiere ingresar número de operación |
| Tab **💳 T. Crédito** | Formulario de tarjeta de crédito (número, titular, vencimiento, CVV) |
| Tab **💳 T. Débito** | Formulario de tarjeta de débito |
| Tab **🛒 Mercado Pago** | Redirige al checkout oficial de Mercado Pago; al regresar, confirma el pago automáticamente |
| **Agregar pago** | Registra el pago del método seleccionado. Permite pagos mixtos hasta completar el total |
| **🛒 Ir a Mercado Pago** | Abre el checkout de Mercado Pago en la misma ventana |
| **Descargar comprobante PDF** | Genera y descarga el PDF del comprobante (HU10) |
| **Ver resumen** | Redirige a `exitosa.html` con el detalle de la reserva confirmada |

---

## Flujo del personal — Botones web

### Acceso personal (`personal.html` + `login.html`)
| Botón / Acción | Descripción |
|---|---|
| **Recepcionista** | Muestra el formulario de login con rol Recepcionista preseleccionado |
| **Administrador** | Muestra el formulario de login con rol Administrador preseleccionado |
| **Ingresar** (login) | Valida usuario y contraseña; redirige al panel correspondiente |
| **🚪 Cerrar sesión** (sidebar) | Elimina la sesión y regresa a `personal.html` |

Credenciales de acceso:
- **Administrador** → usuario: `admin` / contraseña: `hotel2025`
- **Recepcionista** → usuario: `recepcion` / contraseña: `hotel2025`

### Panel Administrador (`admin/index.html` — HU15/HU18)
| Botón | Descripción |
|---|---|
| **+ Nueva habitación** | Abre el formulario de alta de habitación |
| **Editar** (fila tabla) | Abre el formulario con los datos de esa habitación para editarlos |
| **Disponible / Bloqueada** (toggle) | Cambia el estado de disponibilidad de la habitación (HU18) |
| **Eliminar** (fila tabla) | Elimina la habitación tras confirmación |

### Panel Recepcionista (`recepcion/index.html` — HU17)
| Botón | Descripción |
|---|---|
| **Actualizar ahora** | Consulta las notificaciones de nuevas reservas al instante |
| **Ver detalle** (notificación) | Abre modal con el detalle completo de la reserva |
| Polling automático | Se actualiza cada 15 segundos sin intervención del usuario |

---

## Integraciones reales (Sprint 3)

Configura en `backend/.env`:

```
DATABASE_URL=postgresql://...          # Neon (PostgreSQL)
MP_ACCESS_TOKEN=TEST-...               # Mercado Pago (sandbox) o APP_USR-... (producción)
FRONTEND_URL=https://tu-frontend.vercel.app
BACKEND_URL=https://tu-backend.vercel.app
APIS_NET_PE_TOKEN=...                  # Validación DNI
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tucorreo@gmail.com
SMTP_PASSWORD=tu_app_password
SMTP_FROM=tucorreo@gmail.com
```

Si la base ya existe, ejecutar primero `database/sprint3_real_migration.sql`.

Instalar dependencias:
```
pip install -r requirements.txt
```
