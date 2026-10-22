"""Pruebas unitarias para ajuste inflacionario, IPC y shocks macroeconómicos al centavo."""

from decimal import Decimal
import pytest

from simulador.economy import apply_inflation, MacroEconomyEngine


class TestInflationMath:
    """Pruebas matemáticas del cálculo de inflación e indexación."""

    def test_apply_inflation_exact_calculation(self) -> None:
        """Verifica la indexación de un precio base por el IPC."""
        base_cost = Decimal("100000.00")
        ipc = Decimal("1.1250")  # 12.5% de inflación acumulada
        adjusted = apply_inflation(base_cost, ipc)
        assert adjusted == Decimal("112500.00")

    def test_apply_inflation_fractional_cents(self) -> None:
        """Verifica el redondeo al centavo en cálculo con decimales no exactos.
        35000.00 * 1.1523 = 40330.50
        """
        base_cost = Decimal("35000.00")
        ipc = Decimal("1.1523")
        adjusted = apply_inflation(base_cost, ipc)
        assert adjusted == Decimal("40330.50")

    def test_apply_inflation_base_one(self) -> None:
        """Con IPC base de 1.0000, el precio debe mantenerse inalterado."""
        base_cost = Decimal("550000.00")
        ipc = Decimal("1.0000")
        assert apply_inflation(base_cost, ipc) == base_cost

    def test_apply_inflation_negative_amount_raises_error(self) -> None:
        """Precios negativos no están permitidos."""
        with pytest.raises(ValueError):
            apply_inflation(Decimal("-10.00"), Decimal("1.0000"))

    def test_macro_shock_occurrence_between_month_3_and_4(self) -> None:
        """Verifica que el shock macroeconómico ocurra en el mes 3 o mes 4."""
        for seed in range(20):
            engine = MacroEconomyEngine(seed=seed)
            assert engine.shock_month in (3, 4)
            assert Decimal("0.10") <= engine.shock_rate <= Decimal("0.18")

    def test_macro_engine_ipc_progression_deterministic(self) -> None:
        """Verifica la evolución mes a mes del IPC con tasa basal y shock programado."""
        engine = MacroEconomyEngine(
            base_monthly_inflation=Decimal("0.0400"),  # 4% mensual
            shock_month=3,
            shock_rate=Decimal("0.1500")  # +15% de shock en mes 3 (total 19% en mes 3)
        )

        # Mes 1: Base
        rate_m1, ipc_m1 = engine.advance_month(1)
        assert rate_m1 == Decimal("0.000000")
        assert ipc_m1 == Decimal("1.0000")

        # Mes 2: 4% regular
        rate_m2, ipc_m2 = engine.advance_month(2)
        assert rate_m2 == Decimal("0.040000")
        # IPC_2 = 1.0000 * 1.04 = 1.0400
        assert ipc_m2 == Decimal("1.0400")

        # Mes 3: Shock! 4% + 15% = 19%
        rate_m3, ipc_m3 = engine.advance_month(3)
        assert rate_m3 == Decimal("0.190000")
        # IPC_3 = 1.0400 * 1.19 = 1.2376
        assert ipc_m3 == Decimal("1.2376")

        # Mes 4: Vuelve al 4% regular
        rate_m4, ipc_m4 = engine.advance_month(4)
        assert rate_m4 == Decimal("0.040000")
        # IPC_4 = 1.2376 * 1.04 = 1.287104 -> redondeo a 4 decimales: 1.2871
        assert ipc_m4 == Decimal("1.2871")
