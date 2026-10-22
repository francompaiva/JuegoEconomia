"""Motor de Simulación Web del Calendario Mensual de 30 Días.
Gestiona asistencia laboral diaria, horas extras, gastos fijos/discrecionales,
eventos imprevistos, liquidación salarial determinista y ajuste por IPC.
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
    """Gasto discrecional de estilo de vida / ocio."""
    id: str
    category: str
    name: str
    description: str
    base_cost: Decimal
    utility: Decimal
    is_subject_to_ipc: bool = True

    def calculate_cost(self, ipc_index: Decimal) -> Decimal:
        if not self.is_subject_to_ipc:
            return self.base_cost
        return apply_inflation(self.base_cost, ipc_index)


def get_default_discretionary_catalog() -> Dict[str, List[DiscretionaryExpense]]:
    """Catálogo de gastos discrecionales organizados por categoría."""
    return {
        "transporte": [
            DiscretionaryExpense(
                id="trans_uber",
                category="transporte",
                name="Uber y Viajes Privados Diarios",
                description="Traslados rápidos y confortables por la ciudad",
                base_cost=Decimal("160000.00"),
                utility=Decimal("80.0")
            ),
            DiscretionaryExpense(
                id="trans_publico",
                category="transporte",
                name="Transporte Público (Subte y Colectivo)",
                description="Opción económica y sustentable",
                base_cost=Decimal("35000.00"),
                utility=Decimal("30.0")
            )
        ],
        "comida_ocio": [
            DiscretionaryExpense(
                id="food_delivery",
                category="comida_ocio",
                name="Restaurantes, Cenas y Rappi Turbo",
                description="Salidas gourmet, pedidos frecuentes y cafetería de especialidad",
                base_cost=Decimal("220000.00"),
                utility=Decimal("100.0")
            ),
            DiscretionaryExpense(
                id="food_cocina",
                category="comida_ocio",
                name="Cocinar en Casa y Viandas Semanales",
                description="Ahorro financiero cocinando en casa",
                base_cost=Decimal("95000.00"),
                utility=Decimal("45.0")
            )
        ],
        "ropa_shopping": [
            DiscretionaryExpense(
                id="shopping_ropa",
                category="ropa_shopping",
                name="Ropa, Calzado y Shopping",
                description="Indumentaria de temporada y accesorios",
                base_cost=Decimal("70000.00"),
                utility=Decimal("60.0")
            ),
            DiscretionaryExpense(
                id="shopping_basico",
                category="ropa_shopping",
                name="Cuidado de Prendas y Cero Compras",
                description="Reutilización y postergación de compras de ropa",
                base_cost=Decimal("0.00"),
                utility=Decimal("0.0")
            )
        ],
        "cuidado_personal": [
            DiscretionaryExpense(
                id="care_barberia",
                category="cuidado_personal",
                name="La Sagrada Barberia / Salón VIP",
                description="Corte, estilismo y tratamiento de barba",
                base_cost=Decimal("30000.00"),
                utility=Decimal("50.0")
            ),
            DiscretionaryExpense(
                id="care_barrio",
                category="cuidado_personal",
                name="Peluquería de Barrio / Cuidado Casero",
                description="Arreglo básico y económico",
                base_cost=Decimal("10000.00"),
                utility=Decimal("15.0")
            )
        ],
        "entretenimiento": [
            DiscretionaryExpense(
                id="ocio_salidas",
                category="entretenimiento",
                name="Salidas, Cine, Teatro y Boliche",
                description="Entretenimiento cultural y vida social nocturna",
                base_cost=Decimal("60000.00"),
                utility=Decimal("70.0")
            ),
            DiscretionaryExpense(
                id="ocio_hogar",
                category="entretenimiento",
                name="Entretenimiento en Casa (Streaming / Libros)",
                description="Películas en casa y planes tranquilos",
                base_cost=Decimal("15000.00"),
                utility=Decimal("25.0")
            )
        ]
    }


@dataclass
class EmergentUnforeseenEvent:
    """Evento imprevisto emergente que ocurre durante el mes."""
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
        title="Consulta médica por cuadro gripal y medicamentos",
        description="Copago médico de guardia y compra de antibióticos en farmacia",
        base_cost=Decimal("45000.00"),
        impact_utility=Decimal("-10.0")
    ),
    EmergentUnforeseenEvent(
        id="auto_reparacion",
        title="Reparación imprevista del auto / pinchadura de neumático",
        description="Gomería de urgencia, alineación y repuesto mecánico menor",
        base_cost=Decimal("65000.00"),
        impact_utility=Decimal("-15.0")
    ),
    EmergentUnforeseenEvent(
        id="hogar_plomeria",
        title="Arreglo urgente del hogar (Plomería y cerrajería)",
        description="Filtración en el baño y cambio urgente de cerradura averiada",
        base_cost=Decimal("50000.00"),
        impact_utility=Decimal("-10.0")
    ),
    EmergentUnforeseenEvent(
        id="vet_mascota",
        title="Urgencia veterinaria de mascota",
        description="Chequeo urgente y medicación antiparasitaria de guardia",
        base_cost=Decimal("42000.00"),
        impact_utility=Decimal("-8.0")
    )
]


class WebEconomicGame:
    """Motor integral de la simulación web mensual."""

    TOTAL_MONTHS = 6
    DAYS_PER_MONTH = 30

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
        self.current_month: int = 1
        self.current_day: int = 1
        self.cash: Decimal = Decimal("1200000.00")  # Saldo inicial líquido al empezar
        self.debt: Decimal = Decimal("0.00")
        self.cumulative_utility: Decimal = Decimal("0.0")
        self.current_ipc: Decimal = Decimal("1.0000")

        # Registro de asistencia del mes actual: día (1..30) -> bool (True: trabajado, False: ausencia)
        self.attendance: Dict[int, bool] = {}

        # Horas extras acumuladas en el mes
        self.overtime_bonus_accumulated: Decimal = Decimal("0.00")
        self.overtime_challenges_completed: int = 0

        # Selecciones de estilo de vida para el mes en curso (categoría -> ID de opción elegida)
        self.selected_discretionary: Dict[str, str] = {
            "transporte": "trans_publico",
            "comida_ocio": "food_cocina",
            "ropa_shopping": "shopping_basico",
            "cuidado_personal": "care_barrio",
            "entretenimiento": "ocio_hogar"
        }

        # Eventos imprevistos ocurridos en el mes actual
        self.current_month_unforeseen: List[EmergentUnforeseenEvent] = []

        # Registro histórico de meses cerrados
        self.month_history: List[Dict[str, Any]] = []

        # Desafío de horas extras activo (opcional)
        self.active_overtime_challenge: Optional[Dict[str, Any]] = None

    @property
    def worked_days_count(self) -> int:
        """Cantidad de días trabajados en el mes actual."""
        return sum(1 for status in self.attendance.values() if status is True)

    @property
    def unworked_days_count(self) -> int:
        """Cantidad de días no trabajados (ausencias) computados hasta hoy."""
        return sum(1 for status in self.attendance.values() if status is False)

    @property
    def projected_salary(self) -> Decimal:
        """Salario devengado proyectado por asistencia efectiva."""
        return (Decimal(self.worked_days_count) * self.daily_salary).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def projected_absence_deduction(self) -> Decimal:
        """Monto proyectado a descontar por días de inasistencia."""
        return (Decimal(self.unworked_days_count) * self.daily_salary).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def net_worth(self) -> Decimal:
        """Patrimonio neto = Efectivo - Deuda."""
        return self.cash - self.debt

    def get_fixed_costs_breakdown(self) -> Dict[str, Decimal]:
        """Calcula los gastos fijos obligatorios del mes ajustados por el IPC actual."""
        ipc = self.current_ipc
        return {
            "Alquiler (Recoleta)": apply_inflation(Decimal("550000.00"), ipc),
            "Expensas": apply_inflation(Decimal("90000.00"), ipc),
            "Luz (Edesur)": apply_inflation(Decimal("45000.00"), ipc),
            "Agua (AySA)": apply_inflation(Decimal("25000.00"), ipc),
            "Gas (Metrogas)": apply_inflation(Decimal("15000.00"), ipc),
            "Comida básica indispensable": apply_inflation(Decimal("120000.00"), ipc),
        }

    def get_total_fixed_costs(self) -> Decimal:
        """Suma total de gastos fijos obligatorios."""
        return sum(self.get_fixed_costs_breakdown().values(), Decimal("0.00"))

    def get_daily_quiz(self) -> Dict[str, Any]:
        """Retorna la pregunta de jornada laboral del día actual."""
        return get_daily_question(self.current_day, self.current_month)

    def answer_work_quiz(self, selected_option_index: int) -> Dict[str, Any]:
        """Procesa la respuesta al mini-juego diario de jornada laboral.
        Si el jugador responde el cuestionario, se computa como DÍA TRABAJADO.
        """
        if self.current_day in self.attendance:
            return {"error": "El día de trabajo ya fue computado previamente."}

        quiz = self.get_daily_quiz()
        is_correct = (selected_option_index == quiz["correct_index"])

        # Jugar el mini-juego computa el DÍA TRABAJADO (suma al salario)
        self.attendance[self.current_day] = True
        reward = self.daily_salary

        # Bono adicional de utilidad por responder correctamente
        utility_bonus = Decimal("10.0") if is_correct else Decimal("2.0")
        self.cumulative_utility += utility_bonus

        # Ocurrencia eventual de un imprevisto aleatorio con probabilidad del 10%
        unforeseen_msg = None
        if self.rng.random() < 0.10 and len(self.current_month_unforeseen) < 2:
            event = self.rng.choice(POSSIBLE_UNFORESEEN_EVENTS)
            self.current_month_unforeseen.append(event)
            unforeseen_msg = f"⚡ Imprevisto del día: {event.title} (${event.calculate_cost(self.current_ipc):,.2f})"

        return {
            "worked": True,
            "is_correct": is_correct,
            "daily_salary_earned": reward,
            "explanation": quiz["explanation"],
            "utility_bonus": utility_bonus,
            "unforeseen_message": unforeseen_msg,
            "current_day": self.current_day
        }

    def skip_day_unworked(self) -> Dict[str, Any]:
        """El jugador decide NO ir a trabajar en el día actual (Ausencia).
        Se marca el día como NO trabajado (descuento proporcional a fin de mes).
        """
        if self.current_day in self.attendance:
            return {"error": "El día ya fue registrado."}

        self.attendance[self.current_day] = False
        deduction = self.daily_salary

        # Ocurrencia eventual de un imprevisto
        unforeseen_msg = None
        if self.rng.random() < 0.08 and len(self.current_month_unforeseen) < 2:
            event = self.rng.choice(POSSIBLE_UNFORESEEN_EVENTS)
            self.current_month_unforeseen.append(event)
            unforeseen_msg = f"⚡ Imprevisto del día: {event.title} (${event.calculate_cost(self.current_ipc):,.2f})"

        return {
            "worked": False,
            "deduction_projected": deduction,
            "message": f"Día {self.current_day} registrado como AUSENCIA. Se descontará ${deduction:,.2f} en la liquidación mensual.",
            "unforeseen_message": unforeseen_msg,
            "current_day": self.current_day
        }

    def advance_calendar_day(self) -> Dict[str, Any]:
        """Avanza al siguiente día del calendario (hasta el día 30)."""
        if self.current_day not in self.attendance:
            # Si no jugó ni salteó explícitamente, se computa como ausencia automática
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
        """Genera un nuevo desafío matemático/financiero de Horas Extras con cifras reales."""
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
        """Valida la respuesta del desafío de Horas Extras."""
        if not self.active_overtime_challenge:
            return {"error": "No hay ningún desafío de horas extras activo."}

        challenge = self.active_overtime_challenge
        is_correct = (option_index == challenge["correct_index"])

        if is_correct:
            reward = challenge["reward_amount"]
            self.overtime_bonus_accumulated += reward
            self.overtime_challenges_completed += 1
            self.cumulative_utility += Decimal("15.0")
            msg = f"¡Fórmula resuelta con éxito! Ganaste ${reward:,.2f} en concepto de horas extras."
        else:
            msg = f"Respuesta incorrecta. {challenge['explanation']}"

        self.active_overtime_challenge = None
        return {
            "is_correct": is_correct,
            "message": msg,
            "total_overtime_accumulated": self.overtime_bonus_accumulated,
            "completed_count": self.overtime_challenges_completed
        }

    def set_discretionary_choice(self, category: str, option_id: str) -> bool:
        """Actualiza la elección de estilo de vida para una categoría."""
        if category in self.catalog:
            for opt in self.catalog[category]:
                if opt.id == option_id:
                    self.selected_discretionary[category] = option_id
                    return True
        return False

    def close_month(self) -> Dict[str, Any]:
        """Liquida el mes actual (día 30) y ejecuta el balance financiero completo:
        1. Salario devengado por días trabajados + horas extras.
        2. Deducción por ausencias.
        3. Costos fijos obligatorios con ajuste IPC.
        4. Costos de estilo de vida elegidos.
        5. Imprevistos emergentes.
        6. Intereses y deuda bancaria si hay déficit.
        7. Ajuste macroeconómico del IPC para el próximo mes.
        """
        if self.current_month > self.TOTAL_MONTHS:
            raise RuntimeError("La simulación ya ha completado los 6 meses de duración.")

        # Completar días restantes si no se jugaron
        for day in range(1, self.DAYS_PER_MONTH + 1):
            if day not in self.attendance:
                self.attendance[day] = False

        worked = self.worked_days_count
        unworked = self.unworked_days_count

        # 1. Liquidación de Salario
        base_earned = (Decimal(worked) * self.daily_salary).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        absence_deduction = (Decimal(unworked) * self.daily_salary).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        overtime_earned = self.overtime_bonus_accumulated
        net_salary_liquidated = base_earned + overtime_earned

        # 2. Intereses por deuda previa
        interest_applied, total_debt = apply_debt_interest(self.debt, self.tem)

        # 3. Restricción Presupuestaria: Saldo disponible
        # Efectivo disponible = saldo en cuenta + sueldo liquidado - intereses inmediatos
        available_cash = self.cash + net_salary_liquidated - interest_applied

        # 4. Pago de Costos Fijos
        fixed_costs = self.get_fixed_costs_breakdown()
        total_fixed = sum(fixed_costs.values(), Decimal("0.00"))
        available_cash -= total_fixed

        # 5. Pago de Costos Discrecionales (Estilo de vida)
        discretionary_costs: Dict[str, Decimal] = {}
        discretionary_utility = Decimal("0.0")
        for cat, opt_id in self.selected_discretionary.items():
            for opt in self.catalog[cat]:
                if opt.id == opt_id:
                    cost = opt.calculate_cost(self.current_ipc)
                    discretionary_costs[opt.name] = cost
                    available_cash -= cost
                    discretionary_utility += opt.utility

        total_discretionary = sum(discretionary_costs.values(), Decimal("0.00"))
        self.cumulative_utility += discretionary_utility

        # 6. Pago de Gastos Imprevistos
        unforeseen_costs: Dict[str, Decimal] = {}
        for ev in self.current_month_unforeseen:
            cost = ev.calculate_cost(self.current_ipc)
            unforeseen_costs[ev.title] = cost
            available_cash -= cost
            self.cumulative_utility += ev.impact_utility

        total_unforeseen = sum(unforeseen_costs.values(), Decimal("0.00"))

        # 7. Resolución de Saldo y Deuda
        starting_debt = self.debt
        if available_cash >= Decimal("0.00"):
            # Hay superávit: amortizar deuda si existía
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
            # Déficit: préstamo bancario automático
            deficit = abs(available_cash)
            ending_debt = starting_debt + deficit
            ending_cash = Decimal("0.00")

        self.cash = round_currency(ending_cash)
        self.debt = round_currency(ending_debt)

        # 8. Actualizar Macroeconomía e IPC para el próximo período
        inflation_rate, next_ipc = self.macro_engine.advance_month(self.current_month + 1)
        prev_ipc = self.current_ipc
        self.current_ipc = next_ipc

        summary = {
            "month": self.current_month,
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
        self.current_month_unforeseen = []

        return summary

    def get_state(self) -> Dict[str, Any]:
        """Serializa el estado completo del juego para consumo de la API web."""
        fixed = self.get_fixed_costs_breakdown()
        daily_quiz = self.get_daily_quiz() if self.current_day <= self.DAYS_PER_MONTH else None

        # Describir elecciones discrecionales actuales con sus costos e impactos
        disc_state = {}
        for cat, opt_id in self.selected_discretionary.items():
            for opt in self.catalog[cat]:
                if opt.id == opt_id:
                    disc_state[cat] = {
                        "id": opt.id,
                        "name": opt.name,
                        "description": opt.description,
                        "cost": opt.calculate_cost(self.current_ipc),
                        "utility": opt.utility
                    }

        # Opciones disponibles en catálogo
        catalog_serialized = {}
        for cat, options in self.catalog.items():
            catalog_serialized[cat] = [
                {
                    "id": o.id,
                    "name": o.name,
                    "description": o.description,
                    "cost": o.calculate_cost(self.current_ipc),
                    "utility": o.utility
                }
                for o in options
            ]

        # Estado del día actual en la asistencia
        day_status = "pending"
        if self.current_day in self.attendance:
            day_status = "worked" if self.attendance[self.current_day] else "absent"

        return {
            "current_month": self.current_month,
            "total_months": self.TOTAL_MONTHS,
            "current_day": self.current_day,
            "days_per_month": self.DAYS_PER_MONTH,
            "day_status": day_status,
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
            "current_month_unforeseen": [
                {
                    "title": ev.title,
                    "description": ev.description,
                    "cost": ev.calculate_cost(self.current_ipc)
                }
                for ev in self.current_month_unforeseen
            ],
            "discretionary_choices": disc_state,
            "catalog": catalog_serialized,
            "daily_quiz": daily_quiz,
            "has_active_overtime": (self.active_overtime_challenge is not None),
            "month_history": self.month_history,
            "is_game_over": (self.current_month > self.TOTAL_MONTHS)
        }
