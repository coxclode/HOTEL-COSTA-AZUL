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
                <div class="notif-info">
                    <h4>Nueva reserva · ${n.codigo_reserva}</h4>
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

function formatearFecha(isoString) {
    if (!isoString) return "";
    const d = new Date(isoString);
    return d.toLocaleString("es-PE");
}
