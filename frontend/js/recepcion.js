// ── HU17: Polling de notificaciones para recepcionista ──

async function pollAhora() {
    try {
        const resp = await fetch(`${API_BASE}/api/recepcion/notificaciones`);
        const data = await resp.json();

        if (!resp.ok) { return; }

        const cantidad = data.cantidad;
        const lista    = data.notificaciones;

        // Actualizar badge en sidebar
        const badge = document.getElementById("badge-contador");
        if (cantidad > 0) {
            badge.textContent   = cantidad;
            badge.style.display = "inline";
        } else {
            badge.style.display = "none";
        }

        // Actualizar título
        document.getElementById("titulo-contador").textContent =
            cantidad > 0 ? `(${cantidad} sin leer)` : "(ninguna pendiente)";

        // Actualizar hora del último poll
        const ahora = new Date().toLocaleTimeString("es-PE");
        document.getElementById("ultimo-poll").textContent = `· ${ahora}`;

        // Renderizar lista de notificaciones
        const contenedor = document.getElementById("lista-notificaciones");

        if (lista.length === 0) {
            contenedor.innerHTML = `
                <div style="text-align:center;padding:40px;color:#64748b;">
                    <div style="font-size:40px;margin-bottom:10px;">🔕</div>
                    <p>No hay reservas web nuevas por gestionar.</p>
                </div>`;
            return;
        }

        const items = lista.map(n => `
            <div class="notif-item" id="notif-${n.id_notificacion}">
                <div class="notif-info" style="cursor:pointer;"
                     onclick="verDetalleReserva('${n.codigo_reserva}', ${n.id_notificacion})">
                    <h4>🔔 Nueva reserva · <span style="color:#0f4c81;">${n.codigo_reserva}</span>
                        <span style="font-size:11px;color:#94a3b8;font-weight:400;margin-left:8px;">
                            (clic para ver detalle)
                        </span>
                    </h4>
                    <p>
                        <strong>${n.nombre_cliente} ${n.apellido_cliente}</strong> reservó la
                        habitación <strong>${n.numero_habitacion}</strong>
                        (${n.tipo_habitacion}) del
                        <strong>${n.fecha_checkin}</strong> al
                        <strong>${n.fecha_checkout}</strong>
                    </p>
                    <p style="font-size:12px;color:#94a3b8;margin-top:4px;">
                        ${formatearFecha(n.fecha_creacion)}
                    </p>
                </div>
                <button class="btn btn-sm btn-secondary"
                        onclick="marcarLeida(${n.id_notificacion})">
                    Marcar leída
                </button>
            </div>`).join("");

        contenedor.innerHTML = `<div class="notif-lista">${items}</div>`;

    } catch (err) {
        // Silencioso — no interrumpir la UI si hay un fallo momentáneo de red
        document.getElementById("ultimo-poll").textContent = "· sin conexión";
    }
}

async function marcarLeida(id) {
    try {
        const resp = await fetch(
            `${API_BASE}/api/recepcion/notificaciones/${id}/leer`,
            { method: "PATCH" }
        );
        if (resp.ok) {
            // Quitar el elemento visualmente sin esperar el poll
            const el = document.getElementById(`notif-${id}`);
            if (el) el.remove();
            // Refrescar contadores
            pollAhora();
        }
    } catch { /* ignorar */ }
}

async function verDetalleReserva(codigoReserva, idNotificacion) {
    await marcarLeida(idNotificacion);
    // Abre modal con detalle de reserva inline
    const modal = document.getElementById("modal-detalle");
    const cuerpo = document.getElementById("modal-cuerpo");
    if (!modal || !cuerpo) return;

    cuerpo.innerHTML = `<p style="text-align:center;color:#64748b;">Cargando...</p>`;
    modal.style.display = "flex";

    try {
        const resp = await fetch(`${API_BASE}/api/reservas/${codigoReserva}/detalle`);
        if (resp.ok) {
            const r = await resp.json();
            cuerpo.innerHTML = `
                <h3 style="margin-bottom:16px;color:#0b2f4f;">Reserva: ${r.codigo_reserva}</h3>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:14px;">
                    <div><span style="color:#64748b;">Cliente</span><br><strong>${r.nombre_cliente} ${r.apellido_cliente}</strong></div>
                    <div><span style="color:#64748b;">DNI</span><br><strong>${r.dni_cliente}</strong></div>
                    <div><span style="color:#64748b;">Correo</span><br><strong>${r.correo_cliente}</strong></div>
                    <div><span style="color:#64748b;">Teléfono</span><br><strong>${r.telefono_cliente}</strong></div>
                    <div><span style="color:#64748b;">Habitación</span><br><strong>${r.tipo_habitacion} · Nro. ${r.numero_habitacion}</strong></div>
                    <div><span style="color:#64748b;">Personas</span><br><strong>${r.cantidad_personas}</strong></div>
                    <div><span style="color:#64748b;">Check-in</span><br><strong>${r.fecha_checkin}</strong></div>
                    <div><span style="color:#64748b;">Check-out</span><br><strong>${r.fecha_checkout}</strong></div>
                    <div><span style="color:#64748b;">Total</span><br><strong>S/ ${parseFloat(r.precio_total).toFixed(2)}</strong></div>
                    <div><span style="color:#64748b;">Estado</span><br>
                        <span style="background:#dcfce7;color:#166534;padding:3px 10px;border-radius:20px;font-weight:700;font-size:12px;">
                            ${r.estado}
                        </span>
                    </div>
                </div>`;
        } else {
            cuerpo.innerHTML = `<p style="color:#991b1b;">No se encontró detalle de la reserva.</p>`;
        }
    } catch {
        cuerpo.innerHTML = `<p style="color:#991b1b;">Error de conexión al cargar la reserva.</p>`;
    }
}

function cerrarModal() {
    const modal = document.getElementById("modal-detalle");
    if (modal) modal.style.display = "none";
}

function formatearFecha(isoString) {
    if (!isoString) return "";
    const d = new Date(isoString);
    return d.toLocaleString("es-PE");
}
