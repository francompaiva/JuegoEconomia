"""Pruebas unitarias para el ajuste progresivo por inflación sobre gastos fijos y canasta básica."""

from decimal import Decimal
import pytest

from simulador.economy import apply_inflation
from simulador.web_game import WebEconomicGame


class TestWebFixedCostsInflation:
    """Verifica el cálculo de inflación e indexación de gastos fijos al centavo."""

    def test_base_fixed_costs_at_ipc_one(self) -> None:
        """A IPC = 1.0000x (mes inicial), los costos fijos coinciden con sus valores base."""
        game = WebEconomicGame()
        game.current_ipc = Decimal("1.0000")

        costs = game.get_fixed_costs_breakdown()

        assert costs["Alquiler (Recoleta)"] == Decimal("550000.00")
        assert costs["Expensas"] == Decimal("90000.00")
        assert costs["Luz (Edesur)"] == Decimal("45000.00")
        assert costs["Agua (AySA)"] == Decimal("25000.00")
        assert costs["Gas (Metrogas)"] == Decimal("15000.00")
        assert costs["Comida básica indispensable"] == Decimal("120000.00")

        # Suma total base = $845.000,00
        assert game.get_total_fixed_costs() == Decimal("845000.00")

    def test_fixed_costs_indexed_after_inflation(self) -> None:
        """A IPC = 1.1250x (12.5% de inflación acumulada), cada concepto se indexa proporcionalmente."""
        game = WebEconomicGame()
        game.current_ipc = Decimal("1.1250")

        costs = game.get_fixed_costs_breakdown()

        # 550000 * 1.1250 = 618750.00
        assert costs["Alquiler (Recoleta)"] == Decimal("618750.00")
        # 90000 * 1.1250 = 101250.00
        assert costs["Expensas"] == Decimal("101250.00")
        # 45000 * 1.1250 = 50625.00
        assert costs["Luz (Edesur)"] == Decimal("50625.00")
        # 25000 * 1.1250 = 28125.00
        assert costs["Agua (AySA)"] == Decimal("28125.00")
        # 15000 * 1.1250 = 16875.00
        assert costs["Gas (Metrogas)"] == Decimal("16875.00")
        # 120000 * 1.1250 = 135000.00
        assert costs["Comida básica indispensable"] == Decimal("135000.00")

        # Suma total indexada = 845000 * 1.1250 = 950625.00
        assert game.get_total_fixed_costs() == Decimal("950625.00")

    def test_fixed_costs_with_fractional_cents(self) -> None:
        """Verifica el redondeo ROUND_HALF_UP al centavo con un IPC con varios decimales:
        IPC = 1.1837x
        """
        game = WebEconomicGame()
        game.current_ipc = Decimal("1.1837")

        costs = game.get_fixed_costs_breakdown()

        # 45000 * 1.1837 = 53266.50
        assert costs["Luz (Edesur)"] == Decimal("53266.50")
        # 25000 * 1.1837 = 29592.50
        assert costs["Agua (AySA)"] == Decimal("29592.50")
        # 15000 * 1.1837 = 17755.50
        assert costs["Gas (Metrogas)"] == Decimal("17755.50")
        # 90000 * 1.1837 = 106533.00
        assert costs["Expensas"] == Decimal("106533.00")
        # 120000 * 1.1837 = 142044.00
        assert costs["Comida básica indispensable"] == Decimal("142044.00")
        # 550000 * 1.1837 = 651035.00
        assert costs["Alquiler (Recoleta)"] == Decimal("651035.00")
