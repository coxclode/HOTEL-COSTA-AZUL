function estadoBadge(estado) {
    if (!estado) return '<span class="pbadge pbadge-pendiente">Pendiente</span>';
    const e = estado.toLowerCase();
    if (e === 'pendiente')      return '<span class="pbadge pbadge-reciente">RECIENTE</span>';
    if (e === 'confirmada')     return '<span class="pbadge pbadge-confirmado">CONFIRMADO</span>';
    if (e === 'pendiente_pago') return '<span class="pbadge pbadge-pendiente-pago">PENDIENTE PAGO</span>';
    return `<span class="pbadge pbadge-pendiente">${estado.toUpperCase()}</span>`;
}

function cardClass(estado) {
    if (!estado) return '';
    const e = estado.toLowerCase();
    if (e === 'pendiente')      return 'reciente';
    if (e === 'confirmada')     return 'confirmado';
    if (e === 'pendiente_pago') return 'pendiente-pago';
    return '';
}

function renderNotifCards(lista) {
    const contenedor = document.getElementById('lista-notificaciones');
    if (lista.length === 0) {
        contenedor.innerHTML = `
            <div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--muted);">
                <div style="font-size:40px;margin-bottom:10px;">🔕</div>
                <p>No hay reservas nuevas por gestionar.</p>
            </div>`;
        return;
    }

    contenedor.innerHTML = lista.map(n => {
        const precio = n.precio_total ? `S/ ${parseFloat(n.precio_total).toFixed(2)}` : '—';
        return `
        <div class="res-card ${cardClass(n.estado_reserva)}" id="notif-${n.id_notificacion}">
            <div class="res-card-header">
                <span class="res-card-code">#${n.codigo_reserva}</span>
                ${estadoBadge(n.estado_reserva)}
            </div>
            <div class="res-guest">${n.nombre_cliente} ${n.apellido_cliente}</div>
            <div class="res-detail">🛏 ${n.tipo_habitacion} · Nro. ${n.numero_habitacion}</div>
            <div class="res-detail">📅 ${n.fecha_checkin} → ${n.fecha_checkout}</div>
            <div class="res-detail">🕐 ${formatearFecha(n.fecha_creacion)}</div>
            <div class="res-amount">${precio}</div>
            <div style="display:flex;gap:8px;justify-content:space-between;align-items:center;">
                <button class="res-ver-btn" onclick="verDetalleReserva('${n.codigo_reserva}', ${n.id_notificacion})">
                    Ver detalle →
                </button>
                <button class="tbtn tbtn-on" style="font-size:11px;" onclick="marcarLeida(${n.id_notificacion})">
                    ✓ Marcar leída
                </button>
            </div>
        </div>`;
    }).join('');
}

async function pollAhora() {
    try {
        const resp = await fetch(`${API_BASE}/api/recepcion/notificaciones`);
        const data = await resp.json();
        if (!resp.ok) return;

        const cantidad = data.cantidad;
        const lista    = data.notificaciones;

        const badge = document.getElementById('badge-contador');
        const bell  = document.getElementById('bell-badge');
        if (cantidad > 0) {
            badge.textContent   = cantidad;
            badge.style.display = 'inline';
            if (bell) { bell.textContent = cantidad; bell.style.display = 'inline'; }
        } else {
            badge.style.display = 'none';
            if (bell) bell.style.display = 'none';
        }

        document.getElementById('titulo-contador').textContent =
            cantidad > 0 ? `${cantidad} sin leer` : 'Sin reservas pendientes';

        const ahora = new Date().toLocaleTimeString('es-PE');
        const pollEl = document.getElementById('ultimo-poll');
        if (pollEl) pollEl.textContent = `Última actualización: ${ahora}`;

        // Stats
        const setEl = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
        setEl('stat-hoy',      lista.filter(n => n.fecha_creacion && n.fecha_creacion.startsWith(new Date().toISOString().slice(0,10))).length || cantidad);
        setEl('stat-ocup',     '—');
        setEl('stat-pend',     lista.filter(n => n.estado_reserva === 'pendiente_pago').length);
        setEl('stat-sinleer',  cantidad);

        if (typeof window._setNotif === 'function') window._setNotif(lista);
        renderNotifCards(lista);
    } catch {
        const p = document.getElementById('ultimo-poll');
        if (p) p.textContent = 'Sin conexión';
    }
}

async function marcarLeida(id) {
    try {
        const resp = await fetch(`${API_BASE}/api/recepcion/notificaciones/${id}/leer`, { method: 'PATCH' });
        if (resp.ok) {
            const el = document.getElementById(`notif-${id}`);
            if (el) { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; setTimeout(() => el.remove(), 300); }
            pollAhora();
        }
    } catch { /* silencioso */ }
}

async function verDetalleReserva(codigoReserva, idNotificacion) {
    await marcarLeida(idNotificacion);
    const modal  = document.getElementById('modal-detalle');
    const cuerpo = document.getElementById('modal-cuerpo');
    if (!modal || !cuerpo) return;

    cuerpo.innerHTML = `<p style="text-align:center;color:var(--muted);padding:24px;">Cargando...</p>`;
    modal.classList.add('open');

    try {
        const resp = await fetch(`${API_BASE}/api/reservas/${codigoReserva}/detalle`);
        if (resp.ok) {
            const r = await resp.json();
            cuerpo.innerHTML = `
                <h3 style="font-size:20px;font-weight:900;color:var(--navy);margin-bottom:20px;">Reserva: ${r.codigo_reserva}</h3>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;font-size:13px;">
                    <div><div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;">Cliente</div><strong>${r.nombre_cliente} ${r.apellido_cliente}</strong></div>
                    <div><div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;">DNI</div><strong>${r.dni_cliente}</strong></div>
                    <div><div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;">Correo</div><strong>${r.correo_cliente}</strong></div>
                    <div><div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;">Teléfono</div><strong>${r.telefono_cliente}</strong></div>
                    <div><div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;">Habitación</div><strong>${r.tipo_habitacion} · Nro. ${r.numero_habitacion}</strong></div>
                    <div><div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;">Personas</div><strong>${r.cantidad_personas}</strong></div>
                    <div><div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;">Check-in</div><strong>${r.fecha_checkin}</strong></div>
                    <div><div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;">Check-out</div><strong>${r.fecha_checkout}</strong></div>
                    <div><div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;">Total</div><strong style="color:var(--navy);font-size:15px;">S/ ${parseFloat(r.precio_total).toFixed(2)}</strong></div>
                    <div><div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;">Estado</div>${estadoBadge(r.estado)}</div>
                </div>`;
        } else {
            cuerpo.innerHTML = `<div class="palert palert-error">No se encontró detalle de la reserva.</div>`;
        }
    } catch {
        cuerpo.innerHTML = `<div class="palert palert-error">Error de conexión al cargar la reserva.</div>`;
    }
}

function cerrarModal() {
    const modal = document.getElementById('modal-detalle');
    if (modal) modal.classList.remove('open');
}

function formatearFecha(isoString) {
    if (!isoString) return '';
    return new Date(isoString).toLocaleString('es-PE');
}
