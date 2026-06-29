const SERVICIOS = {
    Simple: ['WiFi', 'TV Cable', 'AC', 'Baño privado'],
    Doble:  ['WiFi', 'TV Cable', 'AC', 'Minibar', 'Desayuno'],
    Suite:  ['WiFi', 'TV Cable', 'AC', 'Jacuzzi', 'Sala privada', 'Desayuno', 'Mayordomo'],
};

const TIPO_GRADIENT = {
    Simple: 'linear-gradient(145deg,#1a4a7a,#0d3560)',
    Doble:  'linear-gradient(145deg,#2c1810,#5c3420)',
    Suite:  'linear-gradient(145deg,#1a3a1a,#2a5a30)',
};
const TIPO_ICON = { Simple: '🛏', Doble: '🛏', Suite: '🌟' };
const TIPO_AREA = { Simple: '25', Doble: '35', Suite: '65' };

async function buscarHabitaciones(checkin, checkout, tipo, personas) {
    const contenedor = document.getElementById('contenedor-resultado');
    const infoEl     = document.getElementById('info-busqueda');

    if (!checkin || !checkout) {
        contenedor.innerHTML = `
            <div class="palert palert-info">
                Ingresa las fechas de check-in y check-out para ver habitaciones disponibles.
            </div>`;
        return;
    }

    contenedor.innerHTML = `<p style="color:var(--muted);text-align:center;padding:48px 0;">Buscando habitaciones disponibles…</p>`;

    const qp = new URLSearchParams({ checkin, checkout });
    if (tipo)    qp.append('tipo',    tipo);
    if (personas) qp.append('personas', personas);

    try {
        const resp = await fetch(`${API_BASE}/api/habitaciones/disponibles?${qp.toString()}`);
        const data = await resp.json();

        if (!resp.ok) {
            contenedor.innerHTML = `<div class="palert palert-error">${data.error}</div>`;
            return;
        }

        const p = parseInt(personas) || 1;
        infoEl.textContent = `${data.total} habitación(es) disponible(s) · ${checkin} → ${checkout} · ${p} persona(s)`;

        if (data.total === 0) {
            contenedor.innerHTML = `
                <div class="palert palert-info" style="text-align:center;padding:36px;">
                    No hay habitaciones disponibles para las fechas seleccionadas.<br>
                    <a href="index.html" style="color:var(--navy-mid);font-weight:700;margin-top:8px;display:inline-block;">Modificar búsqueda →</a>
                </div>`;
            return;
        }

        const noches = Math.max(1, Math.ceil((new Date(checkout) - new Date(checkin)) / 86400000));

        const cards = data.habitaciones.map(h => {
            const servicios   = SERVICIOS[h.tipo] || [];
            const grad        = TIPO_GRADIENT[h.tipo] || TIPO_GRADIENT.Simple;
            const icon        = TIPO_ICON[h.tipo] || '🛏';
            const area        = TIPO_AREA[h.tipo] || '?';
            const precioTotal = parseFloat((h.precio_base * noches).toFixed(2));
            const imgHtml     = h.imagen
                ? `<img src="${h.imagen}" alt="Habitación ${h.tipo}" onerror="this.style.display='none'">`
                : `<span class="room-img-fallback">${icon}</span>`;
            const tags = servicios.map(s => `<span class="room-tag">${s}</span>`).join('');

            return `
            <div class="room-card">
                <div class="room-img" style="background:${grad}">
                    <span class="pbadge pbadge-disponible" style="position:absolute;top:12px;right:12px;z-index:1;">Disponible</span>
                    ${imgHtml}
                </div>
                <div class="room-body">
                    <div class="room-header">
                        <div>
                            <div class="room-name">Habitación Nro. ${h.numero}</div>
                            <span style="font-size:11px;font-weight:700;color:var(--muted);">${h.tipo} · ${area} m² · hasta ${h.capacidad} pers.</span>
                        </div>
                        <div>
                            <div class="room-price-label">Por noche</div>
                            <div class="room-price-amount">S/ ${parseFloat(h.precio_base).toFixed(0)}</div>
                        </div>
                    </div>
                    <div class="room-specs" style="margin-top:8px;">
                        <span class="room-spec">🌙 ${noches} noche(s)</span>
                        <span class="room-spec" style="color:var(--navy);font-weight:700;">Total: S/ ${precioTotal.toFixed(2)}</span>
                    </div>
                    <p class="room-desc" style="margin-top:8px;">${h.descripcion}</p>
                    <div class="room-tags">${tags}</div>
                </div>
                <div class="room-footer">
                    <button class="pbtn pbtn-dark pbtn-full"
                        onclick="seleccionarHabitacion(
                            ${h.id_habitacion},'${h.numero}','${h.tipo}',
                            ${h.precio_base},${h.capacidad},
                            '${checkin}','${checkout}',${p},${noches},${precioTotal}
                        )">
                        Seleccionar habitación
                    </button>
                </div>
            </div>`;
        }).join('');

        contenedor.innerHTML = `<div class="room-grid">${cards}</div>`;
    } catch {
        contenedor.innerHTML = `<div class="palert palert-error">No se pudo conectar con el servidor. Verifica que el backend esté activo.</div>`;
    }
}

function seleccionarHabitacion(idHab, numero, tipo, precioBase, capacidad,
                                checkin, checkout, personas, noches, precioTotal) {
    localStorage.setItem('reserva_hab', JSON.stringify({
        id_habitacion: idHab, numero, tipo,
        precio_base: precioBase, capacidad,
        checkin, checkout, personas, noches,
        precio_total: precioTotal,
    }));
    window.location.href = 'datos.html';
}
