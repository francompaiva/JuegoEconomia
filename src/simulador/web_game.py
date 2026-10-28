"""Motor de Simulacion Web del Calendario Mensual de 30 Dias.
Gestiona asistencia laboral diaria, horas extras condicionales, arbol de consumo,
gastos fijos obligatorios, eventos imprevistos de crisis, liquidacion determinista y ajuste por IPC.
SIN EMOJIS - Diseno estructurado para videojuego de simulacion economica.
"""

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import random
from typing import Any, Dict, List, Optional, Tuple

from simulador.economy import (
    calculate_tea,
    calculate_tem,
    apply_debt_interest,
    apply_inflation,
    round_currency,
    MacroEconomyEngine
)
from simulador.work_engine import (
    get_daily_question,
    generate_live_overtime_challenge
)


@dataclass
class DiscretionaryExpense:
    """Gasto discrecional de estilo de vida / ocio con soporte de arbol de opciones."""
    id: str
    category: str
    name: str
    description: str
    base_cost: Decimal
    utility: Decimal
    parent_id: Optional[str] = None
    is_subject_to_ipc: bool = True

    def calculate_cost(self, ipc_index: Decimal) -> Decimal:
        if not self.is_subject_to_ipc:
            return self.base_cost
        return apply_inflation(self.base_cost, ipc_index)


def get_default_discretionary_catalog() -> Dict[str, List[DiscretionaryExpense]]:
    """Catalogo de gastos discrecionales organizados con estructura de arbol de decisiones."""
    return {
        "transporte": [
            DiscretionaryExpense(
                id="trans_publico",
                category="transporte",
                name="Transporte Publico (Subte y Colectivo)",
                description="Opcion economica sustentable y de bajo costo",
                base_cost=Decimal("35000.00"),
                utility=Decimal("30.0")
            ),
            DiscretionaryExpense(
                id="trans_uber",
                category="transporte",
                name="Viajes Privados: Uber y Cabify Diarios",
                description="Traslados rapidos y confortables en plataforma privada",
                base_cost=Decimal("160000.00"),
                utility=Decimal("80.0"),
                parent_id="trans_privado"
            ),
            DiscretionaryExpense(
                id="trans_taxi",
                category="transporte",
                name="Viajes Privados: Taxi Tradicional y Remis",
                description="Traslados urbanos en taxi de calle y remis barrial",
                base_cost=Decimal("130000.00"),
                utility=Decimal("60.0"),
                parent_id="trans_privado"
            )
        ],
        "comida_ocio": [
            DiscretionaryExpense(
                id="food_cocina",
                category="comida_ocio",
                name="Cocinar en Casa y Viandas Semanales",
                description="Ahorro financiero cocinando en casa con compras mayoristas (tarea cotidiana, no genera bienestar extra)",
                base_cost=Decimal("95000.00"),
                utility=Decimal("0.0")
            ),
            DiscretionaryExpense(
                id="food_delivery_pizza",
                category="comida_ocio",
                name="Delivery: Pizza Portena y Gaseosa",
                description="Pizzeria de barrio con entrega rapida",
                base_cost=Decimal("180000.00"),
                utility=Decimal("80.0"),
                parent_id="food_delivery"
            ),
            DiscretionaryExpense(
                id="food_delivery_burger",
                category="comida_ocio",
                name="Delivery: Hamburguesa Artesanal y Cerveza",
                description="Combo gourmet con papas y bebida artesanal",
                base_cost=Decimal("220000.00"),
                utility=Decimal("100.0"),
                parent_id="food_delivery"
            ),
            DiscretionaryExpense(
                id="food_delivery_salad",
                category="comida_ocio",
                name="Delivery: Ensalada Gourmet y Vianda Fit",
                description="Opcion nutritiva, balanceada y fresca a domicilio",
                base_cost=Decimal("150000.00"),
                utility=Decimal("70.0"),
                parent_id="food_delivery"
            ),
            DiscretionaryExpense(
                id="food_delivery",
                category="comida_ocio",
                name="Restaurantes, Cenas y Rappi Turbo",
                description="Salidas gourmet, pedidos frecuentes y cafeteria de especialidad",
                base_cost=Decimal("220000.00"),
                utility=Decimal("100.0")
            )
        ],
        "ropa_shopping": [
            DiscretionaryExpense(
                id="shopping_basico",
                category="ropa_shopping",
                name="Cuidado de Prendas y Cero Compras",
                description="Reutilizacion, arreglo y postergacion de compras de ropa",
                base_cost=Decimal("0.00"),
                utility=Decimal("0.0")
            ),
            DiscretionaryExpense(
                id="shopping_ropa",
                category="ropa_shopping",
                name="Ropa, Calzado y Shopping",
                description="Indumentaria de temporada y compras de marca",
                base_cost=Decimal("70000.00"),
                utility=Decimal("60.0")
            )
        ],
        "cuidado_personal": [
            DiscretionaryExpense(
                id="care_barrio",
                category="cuidado_personal",
                name="Peluqueria de Barrio / Cuidado Casero",
                description="Arreglo basico, economico y tradicional",
                base_cost=Decimal("10000.00"),
                utility=Decimal("15.0")
            ),
            DiscretionaryExpense(
                id="care_barberia",
                category="cuidado_personal",
                name="La Sagrada Barberia / Salon VIP",
                description="Corte, estilismo completo y tratamiento capilar premium",
                base_cost=Decimal("30000.00"),
                utility=Decimal("50.0")
            )
        ],
        "entretenimiento": [
            DiscretionaryExpense(
                id="ocio_hogar",
                category="entretenimiento",
                name="Entretenimiento en Casa (Streaming / Libros)",
                description="Suscripciones de streaming, lectura y planes hogarenos",
                base_cost=Decimal("15000.00"),
                utility=Decimal("25.0")
            ),
            DiscretionaryExpense(
                id="ocio_salidas",
                category="entretenimiento",
                name="Salidas, Cine, Teatro y Boliche",
                description="Entretenimiento cultural y vida nocturna en la ciudad",
                base_cost=Decimal("60000.00"),
                utility=Decimal("70.0")
            )
        ],
        "mascotas": [
            DiscretionaryExpense(
                id="pet_estandar",
                category="mascotas",
                name="Alimento Estandar y Paseos Caseros (Perro y Gato)",
                description="Nutricion comercial regular y cuidados basicos en el hogar",
                base_cost=Decimal("45000.00"),
                utility=Decimal("35.0")
            ),
            DiscretionaryExpense(
                id="pet_premium",
                category="mascotas",
                name="Alimento Super Premium y Guarderia Canina/Felina",
                description="Nutricion veterinaria de alta gama y atencion especializada",
                base_cost=Decimal("110000.00"),
                utility=Decimal("85.0")
            )
        ]
    }


@dataclass
class EmergentUnforeseenEvent:
    """Evento imprevisto emergente (crisis) que ocurre durante el mes."""
    id: str
    title: str
    description: str
    base_cost: Decimal
    impact_utility: Decimal

    def calculate_cost(self, ipc_index: Decimal) -> Decimal:
        return apply_inflation(self.base_cost, ipc_index)


POSSIBLE_UNFORESEEN_EVENTS = [
    EmergentUnforeseenEvent(
        id="med_consulta",
        title="Consulta medica de guardia y farmacia",
        description="Copago medico de urgencia por cuadro agudo y compra de antibioticos",
        base_cost=Decimal("45000.00"),
        impact_utility=Decimal("-20.0")
    ),
    EmergentUnforeseenEvent(
        id="vet_mascota",
        title="Urgencia veterinaria de mascota (Perro y gato)",
        description="Atencion veterinaria de urgencia, ecografia y medicacion de guardia",
        base_cost=Decimal("42000.00"),
        impact_utility=Decimal("-25.0")
    ),
    EmergentUnforeseenEvent(
        id="auto_reparacion",
        title="Reparacion imprevista del auto / gomeria",
        description="Pinchadura en avenida, auxilio mecanico menor y alineacion",
        base_cost=Decimal("55000.00"),
        impact_utility=Decimal("-18.0")
    ),
    EmergentUnforeseenEvent(
        id="hogar_plomeria",
        title="Arreglo urgente de plomeria en el hogar",
        description="Rotura imprevista de flexible en bano y filtracion urgente",
        base_cost=Decimal("46000.00"),
        impact_utility=Decimal("-18.0")
    ),
    EmergentUnforeseenEvent(
        id="pantalla_celular",
        title="Rotura accidental de pantalla de smartphone",
        description="Modulo tactil astillado tras caida fortuita en la via publica",
        base_cost=Decimal("49000.00"),
        impact_utility=Decimal("-15.0")
    ),
    EmergentUnforeseenEvent(
        id="multa_transito",
        title="Notificacion de infraccion de transito en CABA",
        description="Multa imprevista por mal estacionamiento o fotomulta urbana",
        base_cost=Decimal("32000.00"),
        impact_utility=Decimal("-12.0")
    ),
    EmergentUnforeseenEvent(
        id="cerrajeria_urgente",
        title="Cerrajeria de urgencia en puerta principal",
        description="Cerradura trabada y cambio de perno de seguridad",
        base_cost=Decimal("36000.00"),
        impact_utility=Decimal("-14.0")
    ),
    EmergentUnforeseenEvent(
        id="humedad_hogar",
        title="Filtracion de humedad y pintura de emergencia",
        description="Impermeabilizacion urgente de pared medianera deteriorada",
        base_cost=Decimal("44000.00"),
        impact_utility=Decimal("-16.0")
    )
]


class WebEconomicGame:
    """Motor integral de la simulacion web mensual con HUD y mecanica RPG."""

    TOTAL_MONTHS = 6
    DAYS_PER_MONTH = 30
    MONTH_NAMES = ["Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto"]

    def __init__(
        self,
        base_salary: Decimal = Decimal("1200000.00"),
        tna: Decimal = Decimal("0.60"),
        macro_engine: Optional[MacroEconomyEngine] = None,
        seed: Optional[int] = None
    ) -> None:
        self.base_salary = base_salary
        self.daily_salary = (base_salary / Decimal("30")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.tna = tna
        self.tem = calculate_tem(tna)
        self.tea = calculate_tea(self.tem)
        self.macro_engine = macro_engine or MacroEconomyEngine(seed=seed)
        self.catalog = get_default_discretionary_catalog()
        self.rng = random.Random(seed)

        # Estado financiero del jugador
        self.username: str = "jugador"
        self.is_demo_mode: bool = False
        self.current_month: int = 1
        self.current_day: int = 1
        self.cash: Decimal = Decimal("1200000.00")  # Saldo inicial liquido
        self.debt: Decimal = Decimal("0.00")
        self.cumulative_utility: Decimal = Decimal("0.0")
        self.current_ipc: Decimal = Decimal("1.0000")

        # Gasto discrecional acumulado debitado en tiempo real este mes
        self.discretionary_spent_this_month: Decimal = Decimal("0.00")

        # Control de paro de transporte (maximo 1 vez por mes)
        self.transit_strike_occurred_this_month: bool = False

        # Cooldown y pool de eventos imprevistos para evitar repeticiones consecutivas
        self.recent_crisis_ids: List[str] = []

        # Registro de asistencia del mes actual: dia (1..30) -> bool (True: trabajado, False: ausencia)
        self.attendance: Dict[int, bool] = {}

        # Horas extras acumuladas en el mes
        self.overtime_bonus_accumulated: Decimal = Decimal("0.00")
        self.overtime_challenges_completed: int = 0
        self.overtime_done_today: Dict[int, bool] = {}

        # Selecciones activas de consumo
        self.selected_discretionary: Dict[str, str] = {
            "transporte": "trans_publico",
            "comida_ocio": "food_cocina",
            "ropa_shopping": "shopping_basico",
            "cuidado_personal": "care_barrio",
            "entretenimiento": "ocio_hogar",
            "mascotas": "pet_estandar"
        }

        # Eventos imprevistos ocurridos en el mes actual
        self.current_month_unforeseen: List[EmergentUnforeseenEvent] = []

        # Evento de crisis activo que requiere respuesta inmediata
        self.active_crisis: Optional[Dict[str, Any]] = None

        # Registro historico de meses cerrados
        self.month_history: List[Dict[str, Any]] = []

        # Desafio de horas extras activo
        self.active_overtime_challenge: Optional[Dict[str, Any]] = None

    @property
    def month_name(self) -> str:
        """Nombre del mes en curso dentro del calendario semestral (inicia en Marzo)."""
        idx = min(max(self.current_month - 1, 0), len(self.MONTH_NAMES) - 1)
        return self.MONTH_NAMES[idx]

    @property
    def worked_days_count(self) -> int:
        """Cantidad de dias trabajados en el mes actual."""
        return sum(1 for status in self.attendance.values() if status is True)

    @property
    def unworked_days_count(self) -> int:
        """Cantidad de dias no trabajados (ausencias) computados hasta hoy."""
        return sum(1 for status in self.attendance.values() if status is False)

    @property
    def projected_salary(self) -> Decimal:
        """Salario devengado proyectado por asistencia efectiva."""
        return (Decimal(self.worked_days_count) * self.daily_salary).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def projected_absence_deduction(self) -> Decimal:
        """Monto proyectado a descontar por dias de inasistencia."""
        return (Decimal(self.unworked_days_count) * self.daily_salary).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def net_worth(self) -> Decimal:
        """Patrimonio neto = Efectivo - Deuda."""
        return self.cash - self.debt

    @property
    def can_request_overtime(self) -> bool:
        """Horas extras condicionales:
        UNICAMENTE disponibles si el jugador asistio a trabajar hoy.
        """
        return (self.attendance.get(self.current_day) is True)

    def get_fixed_costs_breakdown(self) -> Dict[str, Decimal]:
        """Calcula los gastos fijos obligatorios del mes ajustados por el IPC actual.
        Tope y calibracion inicial exacta de $620.000 ARS:
        - Alquiler en Recoleta: $370.000,00
        - Expensas: $60.000,00
        - Luz (Edesur): $30.000,00
        - Agua (AySA): $20.000,00
        - Gas (Metrogas): $10.000,00
        - Membresia Platino Plus en Megatlon: $50.000,00
        - Canasta basica indispensable: $80.000,00
        Total base a IPC 1.0000 = $620.000,00 ARS exactos.
        """
        ipc = self.current_ipc
        return {
            "Alquiler (Recoleta)": apply_inflation(Decimal("370000.00"), ipc),
            "Expensas": apply_inflation(Decimal("60000.00"), ipc),
            "Luz (Edesur)": apply_inflation(Decimal("30000.00"), ipc),
            "Agua (AySA)": apply_inflation(Decimal("20000.00"), ipc),
            "Gas (Metrogas)": apply_inflation(Decimal("10000.00"), ipc),
            "Gimnasio (Megatlon Platino Plus)": apply_inflation(Decimal("50000.00"), ipc),
            "Comida basica indispensable": apply_inflation(Decimal("80000.00"), ipc),
        }

    def get_total_fixed_costs(self) -> Decimal:
        """Suma total de gastos fijos obligatorios (exactamente $620.000 ARS a IPC base)."""
        return sum(self.get_fixed_costs_breakdown().values(), Decimal("0.00"))

    def get_daily_quiz(self) -> Dict[str, Any]:
        """Retorna la pregunta de jornada laboral del dia actual."""
        return get_daily_question(self.current_day, self.current_month)

    def _pick_unforeseen_event(self) -> EmergentUnforeseenEvent:
        """Selecciona un evento imprevisto aplicando cooldown para evitar repeticiones consecutivas o recientes."""
        available = [ev for ev in POSSIBLE_UNFORESEEN_EVENTS if ev.id not in self.recent_crisis_ids]
        if not available:
            self.recent_crisis_ids.clear()
            available = POSSIBLE_UNFORESEEN_EVENTS
        event = self.rng.choice(available)
        self.recent_crisis_ids.append(event.id)
        if len(self.recent_crisis_ids) > 4:
            self.recent_crisis_ids.pop(0)
        return event

    def answer_work_quiz(self, selected_option_index: int) -> Dict[str, Any]:
        """Procesa la respuesta al mini-juego diario de jornada laboral.
        Si el jugador responde el cuestionario, se computa como DIA TRABAJADO.
        """
        if self.current_day in self.attendance:
            return {"error": "El dia de trabajo ya fue computado previamente."}

        quiz = self.get_daily_quiz()
        is_correct = (selected_option_index == quiz["correct_index"])

        # Jugar el mini-juego computa el DIA TRABAJADO
        self.attendance[self.current_day] = True
        reward = self.daily_salary

        # Bono de utilidad por rendimiento
        utility_bonus = Decimal("10.0") if is_correct else Decimal("2.0")
        self.cumulative_utility += utility_bonus

        # Ocurrencia eventual de crisis / imprevisto (probabilidad 12%)
        crisis_info = None
        if self.rng.random() < 0.12 and len(self.current_month_unforeseen) < 3:
            event = self._pick_unforeseen_event()
            crisis_info = self._trigger_crisis_event(event)

        return {
            "worked": True,
            "is_correct": is_correct,
            "daily_salary_earned": reward,
            "explanation": quiz["explanation"],
            "utility_bonus": utility_bonus,
            "crisis_event": crisis_info,
            "unforeseen_message": f"Alerta de Crisis: Imprevisto del dia: {crisis_info['title']}" if crisis_info else None,
            "current_day": self.current_day,
            "can_request_overtime": self.can_request_overtime
        }

    def skip_day_unworked(self) -> Dict[str, Any]:
        """El jugador decide NO ir a trabajar en el dia actual (Ausencia).
        Se marca el dia como NO trabajado (descuento proporcional a fin de mes).
        BLOQUEA horas extras para el dia.
        """
        if self.current_day in self.attendance:
            return {"error": "El dia ya fue registrado."}

        self.attendance[self.current_day] = False
        deduction = self.daily_salary

        crisis_info = None
        if self.rng.random() < 0.08 and len(self.current_month_unforeseen) < 3:
            event = self._pick_unforeseen_event()
            crisis_info = self._trigger_crisis_event(event)

        return {
            "worked": False,
            "deduction_projected": deduction,
            "message": f"Dia {self.current_day} registrado como AUSENCIA. Se descontara ${deduction:,.2f} en la liquidacion mensual.",
            "crisis_event": crisis_info,
            "unforeseen_message": f"Alerta de Crisis: Imprevisto del dia: {crisis_info['title']}" if crisis_info else None,
            "current_day": self.current_day,
            "can_request_overtime": False
        }

    def _trigger_crisis_event(self, event: EmergentUnforeseenEvent) -> Dict[str, Any]:
        """Activa una crisis financiera emergente que requiere decision inmediata."""
        cost = event.calculate_cost(self.current_ipc)
        finance_cost = (cost * Decimal("1.15")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        crisis_data = {
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "base_cost": event.base_cost,
            "cost": cost,
            "finance_cost": finance_cost,
            "impact_utility": event.impact_utility
        }
        self.active_crisis = crisis_data
        return crisis_data

    def resolve_crisis_decision(self, choice: str) -> Dict[str, Any]:
        """Resuelve la decision ante una tarjeta de crisis:
        - 'cash': Pago al contado inmediato (impacto normal en utilidad).
        - 'finance': Pago financiado (+15% de recargo por tasa de financiamiento, mayor perdida de utilidad).
        """
        if not self.active_crisis:
            return {"error": "No hay ninguna tarjeta de crisis activa."}

        crisis = self.active_crisis
        cost = crisis["cost"] if choice == "cash" else crisis["finance_cost"]
        utility_impact = crisis["impact_utility"] if choice == "cash" else (crisis["impact_utility"] * Decimal("1.5"))

        # Descontar del efectivo o aumentar deuda
        if self.cash >= cost:
            self.cash -= cost
        else:
            diff = cost - self.cash
            self.cash = Decimal("0.00")
            self.debt += diff

        self.cumulative_utility += utility_impact

        # Registrar en la lista de imprevistos afrontados este mes
        resolved_event = EmergentUnforeseenEvent(
            id=crisis["id"],
            title=f"{crisis['title']} ({'Contado' if choice == 'cash' else 'Financiado +15%'})",
            description=crisis["description"],
            base_cost=cost,
            impact_utility=utility_impact
        )
        self.current_month_unforeseen.append(resolved_event)
        self.active_crisis = None

        return {
            "success": True,
            "choice": choice,
            "amount_paid": cost,
            "utility_impact": utility_impact,
            "remaining_cash": self.cash,
            "current_debt": self.debt
        }

    def advance_calendar_day(self) -> Dict[str, Any]:
        """Avanza al siguiente dia del calendario (hasta el dia 30)."""
        if self.current_day not in self.attendance:
            # Si no jugo ni salteo explicitamente, se computa como ausencia automatica
            self.attendance[self.current_day] = False

        if self.current_day < self.DAYS_PER_MONTH:
            self.current_day += 1
            return {
                "success": True,
                "current_day": self.current_day,
                "is_month_end": False
            }
        else:
            return {
                "success": True,
                "current_day": self.current_day,
                "is_month_end": True
            }

    def request_overtime_challenge(self) -> Dict[str, Any]:
        """Genera un nuevo desafio matematico/financiero de Horas Extras con cifras reales.
        RESTRICCION CRITICA: UNICAMENTE disponible si el jugador asistio a trabajar hoy.
        """
        if not self.can_request_overtime:
            raise ValueError("Acceso denegado: Las horas extras solo estan disponibles si has asistido a trabajar hoy.")

        fixed = self.get_fixed_costs_breakdown()
        challenge = generate_live_overtime_challenge(
            current_ipc=self.current_ipc,
            tna=self.tna,
            tem=self.tem,
            edesur_cost=fixed["Luz (Edesur)"],
            aysa_cost=fixed["Agua (AySA)"],
            gas_cost=fixed["Gas (Metrogas)"],
            expensas_cost=fixed["Expensas"],
            unworked_days=self.unworked_days_count,
            daily_salary=self.daily_salary
        )
        self.active_overtime_challenge = challenge
        return challenge

    def submit_overtime_answer(self, option_index: int) -> Dict[str, Any]:
        """Valida la respuesta del desafio de Horas Extras."""
        if not self.active_overtime_challenge:
            return {"error": "No hay ningun desafio de horas extras activo."}

        challenge = self.active_overtime_challenge
        is_correct = (option_index == challenge["correct_index"])

        reward = challenge["reward_amount"]
        self.overtime_bonus_accumulated += reward
        self.overtime_challenges_completed += 1
        self.overtime_done_today[self.current_day] = True

        if is_correct:
            self.cumulative_utility += Decimal("15.0")
            msg = f"Formula resuelta con exito. Ganaste ${reward:,.2f} en concepto de horas extras."
        else:
            self.cumulative_utility += Decimal("5.0")
            msg = f"Actividad de horas extras completada (+${reward:,.2f} acreditados al sueldo). Explicacion de la formula: {challenge['explanation']}"

        self.active_overtime_challenge = None
        return {
            "is_correct": is_correct,
            "message": msg,
            "total_overtime_accumulated": self.overtime_bonus_accumulated,
            "completed_count": self.overtime_challenges_completed
        }

    def record_daily_choice(
        self,
        category: Optional[str] = None,
        option_id: Optional[str] = None,
        bonus_utility: Decimal = Decimal("0.0"),
        cost: Decimal = Decimal("0.0")
    ) -> Dict[str, Any]:
        """Registra una eleccion de consumo cotidiano durante la jornada diaria.
        Descuenta el dinero de la billetera del jugador en tiempo real inmediatamente
        despues de cada decision individual (o incrementa descubierto si no alcanza).
        """
        if category and option_id:
            self.set_discretionary_choice(category, option_id)

        # Aplicar inflacion al costo individual
        cost_indexed = apply_inflation(cost, self.current_ipc) if cost > Decimal("0.00") else Decimal("0.00")

        if cost_indexed > Decimal("0.00"):
            self.discretionary_spent_this_month += cost_indexed
            if self.cash >= cost_indexed:
                self.cash -= cost_indexed
            else:
                diff = cost_indexed - self.cash
                self.cash = Decimal("0.00")
                self.debt += diff

        self.cumulative_utility += bonus_utility

        return {
            "success": True,
            "cost_applied": cost_indexed,
            "remaining_cash": self.cash,
            "current_debt": self.debt,
            "cumulative_utility": self.cumulative_utility
        }

    def set_discretionary_choice(self, category: str, option_id: str) -> bool:
        """Actualiza la eleccion de consumo para una categoria (soporta sub-opciones)."""
        if category in self.catalog:
            for opt in self.catalog[category]:
                if opt.id == option_id:
                    self.selected_discretionary[category] = option_id
                    return True
        return False

    def close_month(self) -> Dict[str, Any]:
        """Liquida el mes actual (dia 30) y ejecuta el balance financiero determinista."""
        if self.current_month > self.TOTAL_MONTHS:
            raise RuntimeError("La simulacion ya ha completado los 6 meses de duracion.")

        # Completar dias restantes si no se jugaron
        for day in range(1, self.DAYS_PER_MONTH + 1):
            if day not in self.attendance:
                self.attendance[day] = False

        worked = self.worked_days_count
        unworked = self.unworked_days_count

        # 1. Liquidacion de Salario
        base_earned = (Decimal(worked) * self.daily_salary).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        absence_deduction = (Decimal(unworked) * self.daily_salary).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        overtime_earned = self.overtime_bonus_accumulated
        net_salary_liquidated = base_earned + overtime_earned

        # 2. Intereses por deuda previa
        interest_applied, total_debt = apply_debt_interest(self.debt, self.tem)

        # 3. Restriccion Presupuestaria: Saldo disponible
        available_cash = self.cash + net_salary_liquidated - interest_applied

        # 4. Pago de Costos Fijos
        fixed_costs = self.get_fixed_costs_breakdown()
        total_fixed = sum(fixed_costs.values(), Decimal("0.00"))
        available_cash -= total_fixed

        # 5. Pago de Costos Discrecionales (Estilo de vida)
        discretionary_costs: Dict[str, Decimal] = {}
        discretionary_utility = Decimal("0.0")
        for cat, opt_id in self.selected_discretionary.items():
            if cat in self.catalog:
                for opt in self.catalog[cat]:
                    if opt.id == opt_id:
                        cost = opt.calculate_cost(self.current_ipc)
                        discretionary_costs[opt.name] = cost
                        discretionary_utility += opt.utility

        if self.discretionary_spent_this_month > Decimal("0.00"):
            # Si el jugador realizo consumos diarios en tiempo real, ya fueron debitados de la billetera.
            # No debitar por duplicado; registrar el gasto total real para el informe contable.
            total_discretionary = self.discretionary_spent_this_month
        else:
            # Caso sin decisiones en tiempo real (ej. ejecucion directa de liquidacion mensual):
            total_discretionary = sum(discretionary_costs.values(), Decimal("0.00"))
            available_cash -= total_discretionary
            self.cumulative_utility += discretionary_utility

        # 6. Pago de Gastos Imprevistos
        unforeseen_costs: Dict[str, Decimal] = {}
        for ev in self.current_month_unforeseen:
            cost = ev.calculate_cost(self.current_ipc)
            unforeseen_costs[ev.title] = cost
            # Notar que los imprevistos ya se debitaron inmediatamente en resolve_crisis_decision()
            # por lo que no se debitan nuevamente de available_cash.

        total_unforeseen = sum(unforeseen_costs.values(), Decimal("0.00"))

        # 7. Resolucion de Saldo y Deuda Bancaria
        starting_debt = self.debt
        if available_cash >= Decimal("0.00"):
            if starting_debt > Decimal("0.00"):
                if available_cash >= starting_debt:
                    available_cash -= starting_debt
                    ending_debt = Decimal("0.00")
                else:
                    ending_debt = starting_debt - available_cash
                    available_cash = Decimal("0.00")
            else:
                ending_debt = Decimal("0.00")
            ending_cash = available_cash
        else:
            deficit = abs(available_cash)
            ending_debt = starting_debt + deficit
            ending_cash = Decimal("0.00")

        self.cash = round_currency(ending_cash)
        self.debt = round_currency(ending_debt)

        # 8. Actualizar Macroeconomia e IPC
        inflation_rate, next_ipc = self.macro_engine.advance_month(self.current_month + 1)
        prev_ipc = self.current_ipc
        self.current_ipc = next_ipc

        summary = {
            "month": self.current_month,
            "month_name": self.month_name,
            "worked_days": worked,
            "unworked_days": unworked,
            "base_salary_earned": base_earned,
            "absence_deduction": absence_deduction,
            "overtime_earned": overtime_earned,
            "net_salary_liquidated": net_salary_liquidated,
            "fixed_costs": fixed_costs,
            "total_fixed_cost": total_fixed,
            "discretionary_costs": discretionary_costs,
            "total_discretionary_cost": total_discretionary,
            "unforeseen_costs": unforeseen_costs,
            "total_unforeseen_cost": total_unforeseen,
            "interest_applied": interest_applied,
            "ending_cash": self.cash,
            "ending_debt": self.debt,
            "net_worth": self.net_worth,
            "utility_earned_this_month": discretionary_utility,
            "cumulative_utility": self.cumulative_utility,
            "ipc_month": prev_ipc,
            "next_ipc": next_ipc,
            "inflation_shock_rate": inflation_rate
        }

        self.month_history.append(summary)

        # Preparar siguiente mes
        self.current_month += 1
        self.current_day = 1
        self.attendance = {}
        self.overtime_bonus_accumulated = Decimal("0.00")
        self.overtime_challenges_completed = 0
        self.overtime_done_today = {}
        self.current_month_unforeseen = []
        self.active_crisis = None
        self.discretionary_spent_this_month = Decimal("0.00")
        self.transit_strike_occurred_this_month = False

        return summary

    def get_state(self) -> Dict[str, Any]:
        """Serializa el estado completo del juego para consumo del HUD web y tarjetas."""
        fixed = self.get_fixed_costs_breakdown()
        daily_quiz = self.get_daily_quiz() if self.current_day <= self.DAYS_PER_MONTH else None

        # Elecciones activas
        disc_state = {}
        for cat, opt_id in self.selected_discretionary.items():
            if cat in self.catalog:
                for opt in self.catalog[cat]:
                    if opt.id == opt_id:
                        disc_state[cat] = {
                            "id": opt.id,
                            "name": opt.name,
                            "description": opt.description,
                            "cost": opt.calculate_cost(self.current_ipc),
                            "utility": opt.utility,
                            "parent_id": opt.parent_id
                        }

        # Catalogo completo estructurado
        catalog_serialized = {}
        for cat, options in self.catalog.items():
            catalog_serialized[cat] = [
                {
                    "id": o.id,
                    "name": o.name,
                    "description": o.description,
                    "cost": o.calculate_cost(self.current_ipc),
                    "utility": o.utility,
                    "parent_id": o.parent_id
                }
                for o in options
            ]

        # Estado del dia actual
        day_status = "pending"
        if self.current_day in self.attendance:
            day_status = "worked" if self.attendance[self.current_day] else "absent"

        return {
            "is_demo_mode": self.is_demo_mode,
            "game_mode": "demo" if self.is_demo_mode else "standard",
            "current_month": self.current_month,
            "current_month_name": self.month_name,
            "month_name": self.month_name,
            "transit_strike_occurred": self.transit_strike_occurred_this_month,
            "discretionary_spent_this_month": self.discretionary_spent_this_month,
            "total_months": self.TOTAL_MONTHS,
            "current_day": self.current_day,
            "days_per_month": self.DAYS_PER_MONTH,
            "day_status": day_status,
            "can_request_overtime": self.can_request_overtime,
            "cash": self.cash,
            "debt": self.debt,
            "net_worth": self.net_worth,
            "cumulative_utility": self.cumulative_utility,
            "base_salary": self.base_salary,
            "daily_salary": self.daily_salary,
            "worked_days": self.worked_days_count,
            "unworked_days": self.unworked_days_count,
            "projected_salary": self.projected_salary,
            "projected_absence_deduction": self.projected_absence_deduction,
            "overtime_bonus_accumulated": self.overtime_bonus_accumulated,
            "overtime_challenges_completed": self.overtime_challenges_completed,
            "tna": self.tna,
            "tem": self.tem,
            "tea": self.tea,
            "current_ipc": self.current_ipc,
            "fixed_costs": fixed,
            "total_fixed_costs": self.get_total_fixed_costs(),
            "attendance_calendar": {str(d): self.attendance.get(d) for d in range(1, self.DAYS_PER_MONTH + 1)},
            "overtime_calendar": {str(d): self.overtime_done_today.get(d, False) for d in range(1, self.DAYS_PER_MONTH + 1)},
            "current_month_unforeseen": [
                {
                    "title": ev.title,
                    "description": ev.description,
                    "cost": ev.calculate_cost(self.current_ipc)
                }
                for ev in self.current_month_unforeseen
            ],
            "active_crisis": self.active_crisis,
            "discretionary_choices": disc_state,
            "catalog": catalog_serialized,
            "daily_quiz": daily_quiz,
            "has_active_overtime": (self.active_overtime_challenge is not None),
            "month_history": self.month_history,
            "username": self.username,
            "is_game_over": self.is_game_over,
            "final_evaluation": self.get_final_evaluation() if self.is_game_over else None
        }

    @property
    def is_game_over(self) -> bool:
        """Indica si el juego ha concluido tras finalizar los 6 meses."""
        return self.current_month > self.TOTAL_MONTHS

    def get_final_evaluation(self) -> Dict[str, Any]:
        """Genera el balance consolidado y evaluacion pedagogica final de los 6 meses."""
        total_months_played = len(self.month_history)
        total_salary_earned = sum((m["net_salary_liquidated"] for m in self.month_history), Decimal("0.00"))
        total_fixed_costs = sum((m["total_fixed_cost"] for m in self.month_history), Decimal("0.00"))
        total_discretionary = sum((m["total_discretionary_cost"] for m in self.month_history), Decimal("0.00"))
        total_unforeseen = sum((m["total_unforeseen_cost"] for m in self.month_history), Decimal("0.00"))
        total_interest = sum((m["interest_applied"] for m in self.month_history), Decimal("0.00"))
        total_overtime = sum((m["overtime_earned"] for m in self.month_history), Decimal("0.00"))
        total_worked_days = sum((m["worked_days"] for m in self.month_history), 0)
        total_unworked_days = sum((m["unworked_days"] for m in self.month_history), 0)

        # Diagnostico de salud financiera
        if self.debt == Decimal("0.00") and self.cash >= Decimal("1000000.00"):
            status_code = "excelente"
            status_title = "Solvencia Financiera Sobresaliente (Superavit y Ahorro)"
            status_badge_class = "badge-mint"
        elif self.debt == Decimal("0.00"):
            status_code = "estable"
            status_title = "Equilibrio Financiero Sustentable (Supervivencia Exitosa)"
            status_badge_class = "badge-mint"
        elif self.debt < Decimal("500000.00"):
            status_code = "vulnerable"
            status_title = "Vulnerabilidad Financiera Moderada (Endeudamiento con Tasa TEM)"
            status_badge_class = "badge-honey"
        else:
            status_code = "critica"
            status_title = "Crisis de Sobreendeudamiento (Deficit Estructural y Quiebra)"
            status_badge_class = "badge-rose"

        # Dictamen pedagogico de Teoria del Consumidor
        if self.debt == Decimal("0.00"):
            verdict_text = (
                f"Has completado con exito la simulacion de 6 meses para el perfil '{self.username}'. "
                "Lograste administrar tu restriccion presupuestaria frente a los shocks de inflacion y los costos "
                "fijos obligatorios en Recoleta sin caer en descubierto bancario ni incurrir en intereses financieros. "
                "Aplicaste de forma eficiente el efecto sustitucion en bienes cotidianos (optando por alternativas "
                "economicas en momentos de restriccion), lo que permitio resguardar tu liquidez y maximizar "
                f"tu utilidad global acumulada ({self.cumulative_utility:.1f} puntos de bienestar)."
            )
        else:
            verdict_text = (
                f"Finalizaste el semestre para el perfil '{self.username}' con una deuda bancaria de "
                f"${self.debt:,.2f}. La tasa de interes mensual (TEM) genero un costo de oportunidad severo "
                "sobre tu ingreso disponible. La falta de sustitucion de bienes y el impacto inflacionario sobre "
                "la canasta de consumo sobrepasaron tu restriccion presupuestaria."
            )

        ipc_pct = ((self.current_ipc - Decimal("1.0000")) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "total_months": total_months_played,
            "username": self.username,
            "total_salary_earned": total_salary_earned,
            "total_fixed_costs": total_fixed_costs,
            "total_discretionary_costs": total_discretionary,
            "total_unforeseen_costs": total_unforeseen,
            "total_interest_paid": total_interest,
            "total_overtime_earned": total_overtime,
            "total_worked_days": total_worked_days,
            "total_unworked_days": total_unworked_days,
            "final_cash": self.cash,
            "final_debt": self.debt,
            "final_net_worth": self.net_worth,
            "final_utility": self.cumulative_utility,
            "final_ipc": self.current_ipc,
            "ipc_inflation_pct": ipc_pct,
            "status_code": status_code,
            "status_title": status_title,
            "status_badge_class": status_badge_class,
            "tutor_verdict": verdict_text,
            "months_summary": self.month_history
        }


def create_demo_game_day_28(seed: Optional[int] = 42) -> WebEconomicGame:
    """Crea una partida precargada y coherente en el Dia 28 de Agosto (Mes 6 de 6).
    Simula el avance historico de los primeros 5 meses completos (Mes 1 al 5)
    para el usuario 'prueba', acumulando salarios, gastos e inflacion por IPC.
    Permite demostrar en vivo los ultimos 2 dias del semestre (dias 28, 29 y 30)
    y el cierre y balance global consolidado de los 6 meses sin alterar la partida estandar.
    """
    game = WebEconomicGame(seed=seed)
    game.is_demo_mode = True
    game.username = "prueba"

    # 1. Simular el avance historico de los primeros 5 meses (Mes 1 a 5)
    for m in range(1, 6):
        # Asistencias regulares: 26 dias trabajados y 4 ausencias por mes
        for d in range(1, 31):
            game.attendance[d] = (d not in (7, 14, 21, 28))

        # 3 horas extras completadas por mes (dias 4, 11 y 18)
        game.overtime_done_today = {}
        for d in (4, 11, 18):
            game.overtime_done_today[d] = True
        game.overtime_challenges_completed = 3
        game.overtime_bonus_accumulated = Decimal("105000.00")

        # Gasto discrecional mensual indexado
        disc_spent = Decimal("720000.00") + Decimal(str((m - 1) * 35000))
        game.discretionary_spent_this_month = disc_spent
        game.cumulative_utility += Decimal("95.0")

        # 1 evento imprevisto por mes
        ev_cost = apply_inflation(Decimal("45000.00"), game.current_ipc)
        ev = EmergentUnforeseenEvent(
            id=f"crisis_m{m}",
            title=f"Gasto imprevisto Mes {m}",
            description="Emergencia afrontada al contado",
            base_cost=ev_cost,
            impact_utility=Decimal("-15.0")
        )
        game.current_month_unforeseen.append(ev)
        game.cash -= ev_cost

        # Cierre del mes historico
        game.close_month()

    # 2. Configurar el Mes 6 (Agosto) posicionado exactamente en el Dia 28
    game.current_day = 28
    game.attendance = {}
    for d in range(1, 28):
        if d in (7, 14, 21):
            game.attendance[d] = False
        else:
            game.attendance[d] = True

    # 3 desafios de horas extras completados en el Mes 6 (dias 4, 11 y 18)
    game.overtime_done_today = {}
    for d in (4, 11, 18):
        game.overtime_done_today[d] = True
    game.overtime_challenges_completed = 3
    game.overtime_bonus_accumulated = Decimal("105000.00")

    # Consumo de estilo de vida debitado en tiempo real en los 27 dias de Agosto
    month_6_disc_spent = Decimal("880000.00")
    game.discretionary_spent_this_month = month_6_disc_spent
    game.cash -= month_6_disc_spent

    # 1 Imprevisto resuelto en el Mes 6
    m6_crisis_cost = apply_inflation(Decimal("45000.00"), game.current_ipc)
    m6_crisis = EmergentUnforeseenEvent(
        id="med_consulta_m6",
        title="Consulta medica de guardia y farmacia (Contado)",
        description="Copago medico de urgencia por cuadro agudo y compra de antibioticos",
        base_cost=m6_crisis_cost,
        impact_utility=Decimal("-20.0")
    )
    game.current_month_unforeseen.append(m6_crisis)
    game.recent_crisis_ids.append("med_consulta_m6")
    game.cash -= m6_crisis_cost

    # Bienestar acumulado de los primeros 27 dias de Agosto
    game.cumulative_utility += Decimal("95.0")

    # Paro de transporte ya acontecido en el Mes 6
    game.transit_strike_occurred_this_month = True

    return game
