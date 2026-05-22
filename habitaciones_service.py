ESTADO_HABITACION_BLOQUEADA = "Bloqueada"


def habitacion_apta_para_reserva(habitacion):
    return habitacion.get("estado") != ESTADO_HABITACION_BLOQUEADA


def filtrar_habitaciones_para_reserva(habitaciones):
    return [
        habitacion
        for habitacion in habitaciones
        if habitacion_apta_para_reserva(habitacion)
    ]
