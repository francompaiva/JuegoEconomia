"""Motor del juego de supervivencia económica a 6 meses.
Implementa Teoría del Consumidor (curvas de indiferencia, efecto sustitución),
restricción presupuestaria dinámica y contabilidad financiera determinista.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from simulador.economy import (
    calculate_tea,
    calculate_tem,
    apply_debt_interest,
    apply_inflation,
    round_currency,
    MacroEconomyEngine
)
from simulador.models import (
    Category,
    ConsumptionChoice,
    FinancialState,
    FixedCostItem,
    MonthTurnResult,
    UnforeseenEvent
)


def get_default_fixed_costs() -> List[FixedCostItem]:
    """Retorna los costos fijos obligatorios del modelo:
    - Alquiler en Recoleta
    - Tarifas Edesur y AySA
    - Membresía Platino Plus en Megatlon
    """
    return [
        FixedCostItem(
            name="Alquiler Departamento (Recoleta)",
            base_cost=Decimal("550000.00"),
            is_subject_to_ipc=False  # Contrato fijo durante el semestre
        ),
        FixedCostItem(
            name="Servicios Públicos (Edesur $45.000 + AySA $25.000)",
            base_cost=Decimal("70000.00"),
            is_subject_to_ipc=True  # Tarifas ajustables por IPC
        ),
        FixedCostItem(
            name="Membresía Platino Plus (Megatlon)",
            base_cost=Decimal("65000.00"),
            is_subject_to_ipc=True  # Cuota de gimnasio indexada
        ),
    ]


def get_catalog_choices() -> Dict[Category, List[ConsumptionChoice]]:
    """Catálogo de opciones de consumo estructurado por categoría.
    Refleja el Efecto Sustitución:
    - Opción costosa: Mayor utilidad cardinal / comodidad.
    - Opción económica: Menor costo monetario, menor utilidad.
    """
    return {
        Category.TRANSPORT: [
            ConsumptionChoice(
                id="trans_uber",
                category=Category.TRANSPORT,
                name="Viajar en Uber todos los días",
                description="Comodidad y rapidez para trasladarse por CABA",
                base_cost=Decimal("160000.00"),
                utility=Decimal("80.0"),
                is_subject_to_ipc=True
            ),
            ConsumptionChoice(
                id="trans_subte",
                category=Category.TRANSPORT,
                name="Transporte público (Subte D / Colectivo)",
                description="Económico pero con mayor tiempo de viaje y aglomeraciones",
                base_cost=Decimal("35000.00"),
                utility=Decimal("30.0"),
                is_subject_to_ipc=True
            )
        ],
        Category.FOOD: [
            ConsumptionChoice(
                id="food_delivery",
                category=Category.FOOD,
                name="Pedir comida por Rappi Turbo o McDonald's",
                description="Cero tiempo de cocina, pedidos premium y conveniencia",
                base_cost=Decimal("220000.00"),
                utility=Decimal("100.0"),
                is_subject_to_ipc=True
            ),
            ConsumptionChoice(
                id="food_home",
                category=Category.FOOD,
                name="Cocinar en casa (compras de mercado y tuppers)",
                description="Ahorro financiero requiriendo tiempo de preparación",
                base_cost=Decimal("95000.00"),
                utility=Decimal("45.0"),
                is_subject_to_ipc=True
            )
        ],
        Category.PERSONAL_CARE: [
            ConsumptionChoice(
                id="care_barberia",
                category=Category.PERSONAL_CARE,
                name="Cortarse el pelo en La Sagrada Barberia",
                description="Atención VIP, café de especialidad y estilismo",
                base_cost=Decimal("30000.00"),
                utility=Decimal("50.0"),
                is_subject_to_ipc=True
            ),
            ConsumptionChoice(
                id="care_barrio",
                category=Category.PERSONAL_CARE,
                name="Peluquería económica de barrio / Cuidado casero",
                description="Corte estándar y prolijo a bajo costo",
                base_cost=Decimal("10000.00"),
                utility=Decimal("15.0"),
                is_subject_to_ipc=True
            )
        ],
        Category.PETS: [
            ConsumptionChoice(
                id="pet_premium",
                category=Category.PETS,
                name="Alimento balanceado Súper Premium + Chequeo Veterinario",
                description="Máxima nutrición y prevención de salud para perro y gato",
                base_cost=Decimal("90000.00"),
                utility=Decimal("60.0"),
                is_subject_to_ipc=True
            ),
            ConsumptionChoice(
                id="pet_standard",
                category=Category.PETS,
                name="Alimento balanceado estándar de supermercado",
                description="Cobertura nutricional básica para perro y gato",
                base_cost=Decimal("45000.00"),
                utility=Decimal("25.0"),
                is_subject_to_ipc=True
            )
        ]
    }


def get_default_unforeseen_events() -> Dict[int, UnforeseenEvent]:
    """Eventos imprevistos programados en el horizonte temporal."""
    return {
        2: UnforeseenEvent(
            month=2,
            title="Urgencia veterinaria: El gato ingirió un cuerpo extraño",
            description="Consulta veterinaria de guardia, ecografía y medicación",
            base_cost=Decimal("45000.00"),
            utility_impact=Decimal("-5.0")
        ),
        5: UnforeseenEvent(
            month=5,
            title="Vacunación y antiparasitarios obligatorios del perro",
            description="Refuerzo anual séxtuple y pipetas antipulgas para ambos",
            base_cost=Decimal("38000.00"),
            utility_impact=Decimal("0.0")
        )
    }


class EconomicSurvivalGame:
    """Simulador de 6 meses de supervivencia económica en terminal."""

    TOTAL_MONTHS = 6

    def __init__(
        self,
        initial_salary: Decimal = Decimal("1200000.00"),
        initial_cash: Decimal = Decimal("0.00"),
        tna: Decimal = Decimal("0.60"),
        macro_engine: Optional[MacroEconomyEngine] = None,
        fixed_costs: Optional[List[FixedCostItem]] = None,
        catalog: Optional[Dict[Category, List[ConsumptionChoice]]] = None,
        unforeseen_events: Optional[Dict[int, UnforeseenEvent]] = None
    ) -> None:
        self.initial_salary = initial_salary
        self.tna = tna
        self.tem = calculate_tem(tna)
        self.tea = calculate_tea(self.tem)
        self.macro_engine = macro_engine or MacroEconomyEngine()
        self.fixed_costs = fixed_costs if fixed_costs is not None else get_default_fixed_costs()
        self.catalog = catalog if catalog is not None else get_catalog_choices()
        self.unforeseen_events = (
            unforeseen_events if unforeseen_events is not None else get_default_unforeseen_events()
        )

        self.state = FinancialState(
            month=1,
            cash=initial_cash,
            debt=Decimal("0.00"),
            cumulative_utility=Decimal("0.0"),
            monthly_salary=initial_salary,
            tna=tna,
            ipc_index=Decimal("1.0000")
        )
        self.history: List[MonthTurnResult] = []

    def get_effective_fixed_costs(self, ipc_index: Decimal) -> Dict[str, Decimal]:
        """Calcula el detalle de costos fijos del mes actual."""
        return {item.name: item.calculate_cost(ipc_index) for item in self.fixed_costs}

    def execute_turn(
        self,
        chosen_choices: List[ConsumptionChoice]
    ) -> MonthTurnResult:
        """Ejecuta un mes de simulación y devuelve el resultado detallado."""
        if self.state.month > self.TOTAL_MONTHS:
            raise RuntimeError("La simulación ya ha alcanzado el límite de 6 meses.")

        current_month = self.state.month
        starting_cash = self.state.cash
        starting_debt = self.state.debt

        # 1. Macroeconomía: Actualizar inflación e IPC
        inflation_rate, current_ipc = self.macro_engine.advance_month(current_month)
        self.state.ipc_index = current_ipc

        # 2. Intereses por deuda previa
        interest_applied, total_debt = apply_debt_interest(starting_debt, self.tem)

        # 3. Restricción Presupuestaria: Cobro de salario
        # El jugador dispone de: saldo previo + salario mensual
        available_cash = starting_cash + self.state.monthly_salary

        # 4. Pago de intereses bancarios obligatorios (se debitan de inmediato)
        available_cash -= interest_applied

        # 5. Costos Fijos
        fixed_costs_dict = self.get_effective_fixed_costs(current_ipc)
        total_fixed_cost = sum(fixed_costs_dict.values(), Decimal("0.00"))
        available_cash -= total_fixed_cost

        # 6. Costos Variables y Efecto Sustitución
        variable_costs_dict: Dict[str, Decimal] = {}
        turn_utility = Decimal("0.0")

        for choice in chosen_choices:
            cost = choice.calculate_cost(current_ipc)
            variable_costs_dict[f"{choice.category.value}: {choice.name}"] = cost
            available_cash -= cost
            turn_utility += choice.utility

        total_variable_cost = sum(variable_costs_dict.values(), Decimal("0.00"))

        # 7. Gastos Imprevistos
        unforeseen = self.unforeseen_events.get(current_month)
        unforeseen_cost = Decimal("0.00")
        if unforeseen:
            unforeseen_cost = unforeseen.calculate_cost(current_ipc)
            available_cash -= unforeseen_cost
            turn_utility += unforeseen.utility_impact

        # 8. Liquidación final del mes y Deuda
        # Si había deuda previa del capital (total_debt - interest_applied = starting_debt)
        remaining_debt_principal = starting_debt

        if available_cash >= Decimal("0.00"):
            # Hay superávit: amortizar deuda si existía
            if remaining_debt_principal > Decimal("0.00"):
                if available_cash >= remaining_debt_principal:
                    available_cash -= remaining_debt_principal
                    ending_debt = Decimal("0.00")
                else:
                    ending_debt = remaining_debt_principal - available_cash
                    available_cash = Decimal("0.00")
            else:
                ending_debt = Decimal("0.00")
            ending_cash = available_cash
        else:
            # Hay déficit (saldo negativo): se convierte en préstamo bancario
            new_deficit = abs(available_cash)
            ending_debt = remaining_debt_principal + new_deficit
            ending_cash = Decimal("0.00")

        # 9. Actualizar estado financiero
        self.state.cash = round_currency(ending_cash)
        self.state.debt = round_currency(ending_debt)
        self.state.cumulative_utility += turn_utility

        result = MonthTurnResult(
            month=current_month,
            starting_cash=round_currency(starting_cash),
            salary_received=round_currency(self.state.monthly_salary),
            fixed_costs=fixed_costs_dict,
            total_fixed_cost=round_currency(total_fixed_cost),
            selected_choices=chosen_choices,
            variable_costs=variable_costs_dict,
            total_variable_cost=round_currency(total_variable_cost),
            unforeseen_event=unforeseen,
            unforeseen_cost=round_currency(unforeseen_cost),
            inflation_rate_turn=inflation_rate,
            ipc_index_turn=current_ipc,
            interest_applied=round_currency(interest_applied),
            ending_cash=self.state.cash,
            new_debt=self.state.debt,
            utility_gained=turn_utility,
            cumulative_utility=self.state.cumulative_utility
        )

        self.history.append(result)
        self.state.month += 1
        return result
