"""Pruebas unitarias de rigor financiero y matemático para TNA, TEM, TEA e intereses al centavo."""

from decimal import Decimal
import pytest

from simulador.economy import (
    calculate_tea,
    calculate_tem,
    apply_debt_interest,
    round_currency,
)


class TestFinancialMath:
    """Verificación formal de conversiones de tasas y cálculo de intereses."""

    def test_calculate_tem_standard_rate(self) -> None:
        """Verifica la conversión de TNA a TEM con una tasa nominal anual del 60%."""
        tna = Decimal("0.60")
        tem = calculate_tem(tna)
        # TEM = 0.60 / 12 = 0.05 (5% mensual)
        assert tem == Decimal("0.050000")

    def test_calculate_tem_various_rates(self) -> None:
        """Verifica diversas tasas anuales comunes."""
        assert calculate_tem(Decimal("0.36")) == Decimal("0.030000")  # 36% TNA -> 3% mensual
        assert calculate_tem(Decimal("1.20")) == Decimal("0.100000")  # 120% TNA -> 10% mensual
        assert calculate_tem(Decimal("0.00")) == Decimal("0.000000")

    def test_calculate_tem_negative_rate_raises_error(self) -> None:
        """Una tasa negativa debe generar una excepción ValueError."""
        with pytest.raises(ValueError):
            calculate_tem(Decimal("-0.10"))

    def test_calculate_tea_compound_formula(self) -> None:
        """Verifica la capitalización de TEM mensual a TEA anual: TEA = (1 + TEM)^12 - 1."""
        tem = Decimal("0.05")  # 5% mensual
        tea = calculate_tea(tem)
        # 1.05^12 = 1.795856326...
        # TEA = 0.795856 (79.5856%)
        expected_tea = Decimal("0.795856")
        assert tea == expected_tea

    def test_calculate_tea_zero_rate(self) -> None:
        """Con tasa 0%, la TEA resultante debe ser 0%."""
        assert calculate_tea(Decimal("0.00")) == Decimal("0.000000")

    def test_apply_debt_interest_exact_cents(self) -> None:
        """Verifica que el devengamiento de intereses redondee exactamente al centavo con ROUND_HALF_UP."""
        debt = Decimal("100000.00")
        tem = Decimal("0.05")  # 5%
        interest, total_debt = apply_debt_interest(debt, tem)

        assert interest == Decimal("5000.00")
        assert total_debt == Decimal("105000.00")

    def test_apply_debt_interest_with_half_up_rounding(self) -> None:
        """Verifica el redondeo bancario de fracción de centavos:
        123.456,78 * 0.05 = 6172.839 -> redondea a 6172.84
        Deuda total = 123456.78 + 6172.84 = 129629.62
        """
        debt = Decimal("123456.78")
        tem = Decimal("0.05")
        interest, total_debt = apply_debt_interest(debt, tem)

        assert interest == Decimal("6172.84")
        assert total_debt == Decimal("129629.62")

    def test_apply_debt_interest_zero_or_negative(self) -> None:
        """Si no hay deuda (saldo no negativo), los intereses devengados son cero."""
        interest, total_debt = apply_debt_interest(Decimal("0.00"), Decimal("0.05"))
        assert interest == Decimal("0.00")
        assert total_debt == Decimal("0.00")

        interest_neg, total_neg = apply_debt_interest(Decimal("-500.00"), Decimal("0.05"))
        assert interest_neg == Decimal("0.00")
        assert total_neg == Decimal("0.00")
