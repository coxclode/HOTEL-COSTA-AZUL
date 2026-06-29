const TIPO_GRADIENT = {
    Simple: 'linear-gradient(145deg,#1a4a7a,#0d3560)',
    Doble:  'linear-gradient(145deg,#2c1810,#5c3420)',
    Suite:  'linear-gradient(145deg,#1a3a1a,#2a5a30)',
};
const TIPO_ICON = { Simple: '🛏', Doble: '🛏', Suite: '🌟' };
const TIPO_AREA = { Simple: '25', Doble: '35', Suite: '65' };
const TIPO_POPULAR = { Doble: true };

async function cargarCatalogo() {
    const contenedor = document.getElementById('catalogo-contenedor');
    const contador   = document.getElementById('catalogo-contador');

    try {
        const resp = await fetch(`${API_BASE}/api/habitaciones`);
        const data = await resp.json();

        if (!resp.ok) {
            contenedor.innerHTML = `<div class="palert palert-error">${data.error}</div>`;
            return;
        }

        contador.textContent = `${data.total} habitación(es) en catálogo`;

        if (data.total === 0) {
            contenedor.innerHTML = `<div class="palert palert-info" style="text-align:center;padding:32px;">No hay habitaciones en catálogo.</div>`;
            return;
        }

        const cards = data.habitaciones.map(h => {
            const grad   = TIPO_GRADIENT[h.tipo] || TIPO_GRADIENT.Simple;
            const icon   = TIPO_ICON[h.tipo] || '🛏';
            const area   = TIPO_AREA[h.tipo] || '?';
            const pop    = TIPO_POPULAR[h.tipo] ? '<span class="room-badge-popular">MÁS POPULAR</span>' : '';
            const imgHtml = h.imagen
                ? `<img src="${h.imagen}" alt="Habitación ${h.tipo}" onerror="this.style.display='none'">`
                : `<span class="room-img-fallback">${icon}</span>`;

            return `
            <div class="room-card">
                <div class="room-img" style="background:${grad}">
                    ${pop}
                    ${imgHtml}
                </div>
                <div class="room-body">
                    <div class="room-header">
                        <span class="room-name">Hab. ${h.numero} · ${h.tipo}</span>
                        <div>
                            <div class="room-price-label">Por noche</div>
                            <div class="room-price-amount">S/ ${parseFloat(h.precio_base).toFixed(0)}</div>
                        </div>
                    </div>
                    <div class="room-specs">
                        <span class="room-spec">🏠 ${area} m²</span>
                        <span class="room-spec">👥 Hasta ${h.capacidad} pers.</span>
                    </div>
                    <p class="room-desc">${h.descripcion}</p>
                </div>
                <div class="room-footer">
                    <a href="habitaciones.html" class="pbtn pbtn-dark pbtn-full">Reservar Ahora</a>
                </div>
            </div>`;
        }).join('');

        contenedor.innerHTML = `<div class="room-grid">${cards}</div>`;
    } catch {
        contenedor.innerHTML = `<div class="palert palert-error">No se pudo conectar con el servidor. Verifica que el backend esté activo.</div>`;
    }
}
