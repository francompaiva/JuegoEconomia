"""Modelos de datos y estructuras tipadas para el Simulador Económico.
Implementa dataclasses inmutables y enums para Teoría del Consumidor y Finanzas.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional


class Category(str, Enum):
    """Categorías de decisiones de consumo y costos."""
    TRANSPORT = "Transporte"
    FOOD = "Alimentación"
    PERSONAL_CARE = "Cuidado Personal"
    PETS = "Cuidado de Mascotas (Perro y Gato)"


@dataclass(frozen=True)
class ConsumptionChoice:
    """Representa una alternativa de consumo dentro de la canasta de bienes.
    
    Aplica conceptos de Teoría del Consumidor:
    - Costo monetario (restricción presupuestaria)
    - Utilidad ordinal/cardinal asociada (preferencias del consumidor)
    - Sensibilidad a la inflación (ajuste por IPC)
    """
    id: str
    category: Category
    name: str
    description: str
    base_cost: Decimal
    utility: Decimal
    is_subject_to_ipc: bool = True

    def calculate_cost(self, ipc_index: Decimal) -> Decimal:
        """Calcula el costo indexado por inflación al centavo exacto."""
        if not self.is_subject_to_ipc:
            return self.base_cost
        from simulador.economy import apply_inflation
        return apply_inflation(self.base_cost, ipc_index)


@dataclass(frozen=True)
class FixedCostItem:
    """Costo fijo mensual obligatorio del jugador."""
    name: str
    base_cost: Decimal
    is_subject_to_ipc: bool = False

    def calculate_cost(self, ipc_index: Decimal) -> Decimal:
        """Calcula el costo del item fijo aplicando IPC si corresponde."""
        if not self.is_subject_to_ipc:
            return self.base_cost
        from simulador.economy import apply_inflation
        return apply_inflation(self.base_cost, ipc_index)


@dataclass
class FinancialState:
    """Estado financiero consolidado del jugador en un momento dado."""
    month: int
    cash: Decimal
    debt: Decimal
    cumulative_utility: Decimal
    monthly_salary: Decimal
    tna: Decimal
    ipc_index: Decimal

    @property
    def net_worth(self) -> Decimal:
        """Patrimonio neto = Efectivo disponible - Deuda acumulada."""
        return self.cash - self.debt


@dataclass(frozen=True)
class UnforeseenEvent:
    """Evento imprevisto que afecta la restricción presupuestaria."""
    month: int
    title: str
    description: str
    base_cost: Decimal
    utility_impact: Decimal

    def calculate_cost(self, ipc_index: Decimal) -> Decimal:
        from simulador.economy import apply_inflation
        return apply_inflation(self.base_cost, ipc_index)


@dataclass(frozen=True)
class MonthTurnResult:
    """Reporte detallado del cierre de un turno/mes."""
    month: int
    starting_cash: Decimal
    salary_received: Decimal
    fixed_costs: Dict[str, Decimal]
    total_fixed_cost: Decimal
    selected_choices: List[ConsumptionChoice]
    variable_costs: Dict[str, Decimal]
    total_variable_cost: Decimal
    unforeseen_event: Optional[UnforeseenEvent]
    unforeseen_cost: Decimal
    inflation_rate_turn: Decimal
    ipc_index_turn: Decimal
    interest_applied: Decimal
    ending_cash: Decimal
    new_debt: Decimal
    utility_gained: Decimal
    cumulative_utility: Decimal
