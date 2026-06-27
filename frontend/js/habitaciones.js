// ── HU2: Buscar y mostrar habitaciones disponibles ──

const SERVICIOS = {
    Simple: ["WiFi", "TV Cable", "AC", "Baño privado"],
    Doble:  ["WiFi", "TV Cable", "AC", "Minibar", "Baño privado", "Desayuno"],
    Suite:  ["WiFi", "TV Cable", "AC", "Jacuzzi", "Sala privada", "Minibar", "Desayuno", "Mayordomo"],
};

const ICONOS = { Simple: "🛏️", Doble: "🛏️🛏️", Suite: "🌟" };

async function buscarHabitaciones(checkin, checkout, tipo, personas) {
    const contenedor = document.getElementById("contenedor-resultado");
    const infoEl     = document.getElementById("info-busqueda");

    if (!checkin || !checkout) {
        contenedor.innerHTML = `
            <div class="alert alert-info">
                Ingresa las fechas de check-in y check-out para ver habitaciones disponibles.
            </div>`;
        return;
    }

    contenedor.innerHTML = `<p style="color:#64748b;text-align:center;padding:40px 0;">
        Buscando habitaciones disponibles…</p>`;

    const params = new URLSearchParams({ checkin, checkout });
    if (tipo)    params.append("tipo",    tipo);
    if (personas) params.append("personas", personas);

    try {
        const resp = await fetch(`${API_BASE}/api/habitaciones/disponibles?${params.toString()}`);
        const data = await resp.json();

        if (!resp.ok) {
            contenedor.innerHTML = `<div class="alert alert-error">${data.error}</div>`;
            return;
        }

        const p = parseInt(personas) || 1;
        infoEl.textContent =
            `${data.total} habitación(es) disponible(s) · ${checkin} → ${checkout} · ${p} persona(s)`;

        if (data.total === 0) {
            contenedor.innerHTML = `
                <div class="alert alert-info" style="text-align:center;padding:36px;">
                    No hay habitaciones disponibles para las fechas seleccionadas.<br>
                    <a href="index.html" style="color:#0f4c81;font-weight:700;margin-top:8px;display:inline-block;">
                        Modificar búsqueda
                    </a>
                </div>`;
            return;
        }

        const noches = Math.max(1, Math.ceil(
            (new Date(checkout) - new Date(checkin)) / (1000 * 60 * 60 * 24)
        ));

        const cards = data.habitaciones.map(h => {
            const servicios  = SERVICIOS[h.tipo] || [];
            const icono      = ICONOS[h.tipo]    || "🛏️";
            const precioTotal = parseFloat((h.precio_base * noches).toFixed(2));

            const imgHtml = h.imagen
                ? `<img src="${h.imagen}" alt="Habitación ${h.tipo}"
                        onerror="this.style.display='none'">`
                : `<span style="font-size:58px;z-index:1;">${icono}</span>`;

            const serviciosTags = servicios
                .map(s => `<span class="servicio-tag">${s}</span>`)
                .join("");

            return `
                <div class="hab-card">
                    <div class="hab-card-img">
                        ${imgHtml}
                        <span class="hab-badge">${h.tipo}</span>
                    </div>
                    <div class="hab-card-body">
                        <h3>Habitación Nro. ${h.numero}</h3>
                        <p class="descripcion">${h.descripcion}</p>
                        <div class="hab-meta">
                            <span class="hab-meta-item">👥 Hasta ${h.capacidad} persona(s)</span>
                            <span class="hab-meta-item">🌙 ${noches} noche(s)</span>
                            <span class="hab-meta-item" style="color:#166534;background:#dcfce7;">✓ Disponible</span>
                        </div>
                        <div class="servicios-lista">${serviciosTags}</div>
                    </div>
                    <div class="hab-card-footer">
                        <div>
                            <div class="precio">S/ ${parseFloat(h.precio_base).toFixed(2)} <span>/ noche</span></div>
                            <div style="font-size:12px;color:#64748b;">Total: S/ ${precioTotal.toFixed(2)}</div>
                        </div>
                        <button class="btn-sel"
                            onclick="seleccionarHabitacion(
                                ${h.id_habitacion},'${h.numero}','${h.tipo}',
                                ${h.precio_base},${h.capacidad},
                                '${checkin}','${checkout}',${p},${noches},${precioTotal}
                            )">
                            Seleccionar
                        </button>
                    </div>
                </div>`;
        }).join("");

        contenedor.innerHTML = `<div class="hab-grid">${cards}</div>`;

    } catch {
        contenedor.innerHTML = `
            <div class="alert alert-error">
                No se pudo conectar con el servidor. Verifica que el backend esté activo.
            </div>`;
    }
}

function seleccionarHabitacion(idHab, numero, tipo, precioBase, capacidad,
                                checkin, checkout, personas, noches, precioTotal) {
    const reserva_hab = {
        id_habitacion: idHab,
        numero,
        tipo,
        precio_base:  precioBase,
        capacidad,
        checkin,
        checkout,
        personas,
        noches,
        precio_total: precioTotal,
    };
    localStorage.setItem("reserva_hab", JSON.stringify(reserva_hab));
    window.location.href = "datos.html";
}
