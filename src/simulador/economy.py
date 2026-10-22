"""Cálculos económicos y financieros deterministas para el Simulador.
Utiliza Decimal con redondeo ROUND_HALF_UP para asegurar precisión financiera al centavo.
"""

from decimal import Decimal, ROUND_HALF_UP
import random
from typing import Optional, Tuple

CENT = Decimal("0.01")
RATE_PRECISION = Decimal("0.000001")
IPC_PRECISION = Decimal("0.0001")


def round_currency(value: Decimal) -> Decimal:
    """Redondea un monto monetario al centavo más cercano usando ROUND_HALF_UP."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_tem(tna: Decimal) -> Decimal:
    """Convierte la TNA (Tasa Nominal Anual) a TEM (Tasa Efectiva Mensual).
    
    Fórmula estándar bancaria:
        TEM = TNA / 12
    """
    if tna < Decimal("0.0"):
        raise ValueError("La TNA no puede ser negativa.")
    return (tna / Decimal("12")).quantize(RATE_PRECISION, rounding=ROUND_HALF_UP)


def calculate_tea(tem: Decimal) -> Decimal:
    """Calcula la TEA (Tasa Efectiva Anual) correspondiente a una TEM.
    
    Fórmula de capitalización compuesta:
        TEA = (1 + TEM)^12 - 1
    """
    if tem < Decimal("0.0"):
        raise ValueError("La TEM no puede ser negativa.")
    one_plus_tem = Decimal("1.0") + tem
    tea = (one_plus_tem ** 12) - Decimal("1.0")
    return tea.quantize(RATE_PRECISION, rounding=ROUND_HALF_UP)


def apply_debt_interest(debt: Decimal, tem: Decimal) -> Tuple[Decimal, Decimal]:
    """Aplica la tasa mensual de interés (TEM) al saldo deudor.
    
    Retorna:
        (interes_generado, deuda_total_con_intereses)
    Ambos redondeados exactamente al centavo.
    """
    if debt <= Decimal("0.00"):
        return Decimal("0.00"), Decimal("0.00")
    
    interest = round_currency(debt * tem)
    total_debt = round_currency(debt + interest)
    return interest, total_debt


def apply_inflation(base_amount: Decimal, ipc_index: Decimal) -> Decimal:
    """Ajusta un precio base por el Índice de Precios al Consumidor (IPC).
    
    Fórmula:
        Precio_Ajustado = Base * IPC
    Redondeado al centavo exacto.
    """
    if base_amount < Decimal("0.00"):
        raise ValueError("El monto base no puede ser negativo.")
    if ipc_index < Decimal("0.0000"):
        raise ValueError("El IPC no puede ser negativo.")
    return round_currency(base_amount * ipc_index)


class MacroEconomyEngine:
    """Motor de simulación macroeconómica: gestiona inflación acumulada e IPC."""

    def __init__(
        self,
        base_monthly_inflation: Decimal = Decimal("0.0350"),  # 3.5% mensual basal
        shock_month: Optional[int] = None,
        shock_rate: Optional[Decimal] = None,
        seed: Optional[int] = None
    ) -> None:
        self.base_monthly_inflation = base_monthly_inflation
        self.rng = random.Random(seed)
        # Si no se especifica, el shock ocurre aleatoriamente en el mes 3 o 4
        self.shock_month = shock_month if shock_month is not None else self.rng.choice([3, 4])
        # Magnitud del shock aleatorio entre 10% y 18% si no está definido
        if shock_rate is not None:
            self.shock_rate = shock_rate
        else:
            random_pct = self.rng.randint(100, 180) / 1000.0  # 0.10 a 0.18
            self.shock_rate = Decimal(str(round(random_pct, 4)))

        self.current_ipc = Decimal("1.0000")
        self.history: list[dict[str, Decimal]] = []

    def get_monthly_inflation_rate(self, month: int) -> Decimal:
        """Determina la tasa de inflación para un mes específico."""
        if month == 1:
            return Decimal("0.0000")  # Mes 1 es la base (IPC = 1.0)
        if month == self.shock_month:
            # En el mes del shock se suma el salto inflacionario al ritmo base
            return (self.base_monthly_inflation + self.shock_rate).quantize(
                RATE_PRECISION, rounding=ROUND_HALF_UP
            )
        return self.base_monthly_inflation.quantize(RATE_PRECISION, rounding=ROUND_HALF_UP)

    def advance_month(self, month: int) -> Tuple[Decimal, Decimal]:
        """Avanza al mes indicado y actualiza el IPC acumulado.
        
        Retorna:
            (tasa_inflacion_mes, nuevo_ipc)
        """
        inflation_rate = self.get_monthly_inflation_rate(month)
        if month == 1:
            self.current_ipc = Decimal("1.0000")
        else:
            self.current_ipc = (self.current_ipc * (Decimal("1.0") + inflation_rate)).quantize(
                IPC_PRECISION, rounding=ROUND_HALF_UP
            )
        
        self.history.append({
            "month": Decimal(month),
            "rate": inflation_rate,
            "ipc": self.current_ipc
        })
        return inflation_rate, self.current_ipc
