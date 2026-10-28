"""Pruebas unitarias para el ajuste progresivo por inflacion sobre gastos fijos y canasta basica."""

from decimal import Decimal
import pytest

from simulador.economy import apply_inflation
from simulador.web_game import WebEconomicGame


class TestWebFixedCostsInflation:
    """Verifica el calculo de inflacion e indexacion de gastos fijos al centavo."""

    def test_base_fixed_costs_at_ipc_one(self) -> None:
        """A IPC = 1.0000x (mes inicial), los costos fijos coinciden exactamente con el tope de $620.000,00 ARS."""
        game = WebEconomicGame()
        game.current_ipc = Decimal("1.0000")

        costs = game.get_fixed_costs_breakdown()

        assert costs["Alquiler (Recoleta)"] == Decimal("370000.00")
        assert costs["Expensas"] == Decimal("60000.00")
        assert costs["Luz (Edesur)"] == Decimal("30000.00")
        assert costs["Agua (AySA)"] == Decimal("20000.00")
        assert costs["Gas (Metrogas)"] == Decimal("10000.00")
        assert costs["Gimnasio (Megatlon Platino Plus)"] == Decimal("50000.00")
        assert costs["Comida basica indispensable"] == Decimal("80000.00")

        # Suma total base = $620.000,00 exactos
        assert game.get_total_fixed_costs() == Decimal("620000.00")

    def test_fixed_costs_indexed_after_inflation(self) -> None:
        """A IPC = 1.1250x (12.5% de inflacion acumulada), cada concepto se indexa proporcionalmente."""
        game = WebEconomicGame()
        game.current_ipc = Decimal("1.1250")

        costs = game.get_fixed_costs_breakdown()

        # 370000 * 1.1250 = 416250.00
        assert costs["Alquiler (Recoleta)"] == Decimal("416250.00")
        # 60000 * 1.1250 = 67500.00
        assert costs["Expensas"] == Decimal("67500.00")
        # 30000 * 1.1250 = 33750.00
        assert costs["Luz (Edesur)"] == Decimal("33750.00")
        # 20000 * 1.1250 = 22500.00
        assert costs["Agua (AySA)"] == Decimal("22500.00")
        # 10000 * 1.1250 = 11250.00
        assert costs["Gas (Metrogas)"] == Decimal("11250.00")
        # 50000 * 1.1250 = 56250.00
        assert costs["Gimnasio (Megatlon Platino Plus)"] == Decimal("56250.00")
        # 80000 * 1.1250 = 90000.00
        assert costs["Comida basica indispensable"] == Decimal("90000.00")

        # Suma total indexada = 620000 * 1.1250 = 697500.00
        assert game.get_total_fixed_costs() == Decimal("697500.00")

    def test_fixed_costs_with_fractional_cents(self) -> None:
        """Verifica el redondeo ROUND_HALF_UP al centavo con un IPC con varios decimales:
        IPC = 1.1837x
        """
        game = WebEconomicGame()
        game.current_ipc = Decimal("1.1837")

        costs = game.get_fixed_costs_breakdown()

        # 370000 * 1.1837 = 437969.00
        assert costs["Alquiler (Recoleta)"] == Decimal("437969.00")
        # 60000 * 1.1837 = 71022.00
        assert costs["Expensas"] == Decimal("71022.00")
        # 30000 * 1.1837 = 35511.00
        assert costs["Luz (Edesur)"] == Decimal("35511.00")
        # 20000 * 1.1837 = 23674.00
        assert costs["Agua (AySA)"] == Decimal("23674.00")
        # 10000 * 1.1837 = 11837.00
        assert costs["Gas (Metrogas)"] == Decimal("11837.00")
        # 50000 * 1.1837 = 59185.00
        assert costs["Gimnasio (Megatlon Platino Plus)"] == Decimal("59185.00")
        # 80000 * 1.1837 = 94696.00
        assert costs["Comida basica indispensable"] == Decimal("94696.00")

        # Suma esperada = 437969 + 71022 + 35511 + 23674 + 11837 + 59185 + 94696 = 733894.00
        assert game.get_total_fixed_costs() == Decimal("733894.00")
