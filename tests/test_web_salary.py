"""Pruebas unitarias para el cálculo exacto del salario mensual,
asistencia diaria, descuentos por ausencias y horas extras por fórmulas financieras.
"""

from decimal import Decimal
import pytest

from simulador.web_game import WebEconomicGame


class TestWebSalaryCalculation:
    """Valida la liquidación salarial con precisión estricta en Decimal."""

    def test_full_attendance_salary(self) -> None:
        """30 días trabajados = 100% del salario base ($1.200.000,00) y cero descuento."""
        game = WebEconomicGame(base_salary=Decimal("1200000.00"))

        # Marcar los 30 días como trabajados
        for day in range(1, 31):
            game.attendance[day] = True

        assert game.worked_days_count == 30
        assert game.unworked_days_count == 0
        assert game.projected_salary == Decimal("1200000.00")
        assert game.projected_absence_deduction == Decimal("0.00")

    def test_partial_absence_salary_deduction(self) -> None:
        """20 días trabajados y 10 días ausentes:
        Salario base devengado = 20 * $40.000,00 = $800.000,00
        Descuento por ausencias = 10 * $40.000,00 = $400.000,00
        """
        game = WebEconomicGame(base_salary=Decimal("1200000.00"))

        for day in range(1, 21):
            game.attendance[day] = True
        for day in range(21, 31):
            game.attendance[day] = False

        assert game.worked_days_count == 20
        assert game.unworked_days_count == 10
        assert game.projected_salary == Decimal("800000.00")
        assert game.projected_absence_deduction == Decimal("400000.00")

    def test_zero_attendance_salary(self) -> None:
        """0 días trabajados = $0 de salario ganado y $1.200.000,00 descontados."""
        game = WebEconomicGame(base_salary=Decimal("1200000.00"))

        for day in range(1, 31):
            game.attendance[day] = False

        assert game.worked_days_count == 0
        assert game.unworked_days_count == 30
        assert game.projected_salary == Decimal("0.00")
        assert game.projected_absence_deduction == Decimal("1200000.00")

    def test_overtime_bonus_addition_to_payroll(self) -> None:
        """Las horas extras resueltas con fórmulas se adicionan al sueldo neto liquidado."""
        game = WebEconomicGame(base_salary=Decimal("1200000.00"))

        # 25 días trabajados, 5 ausentes
        for day in range(1, 26):
            game.attendance[day] = True
        for day in range(26, 31):
            game.attendance[day] = False

        # Agregar 2 bonos de horas extras de $35.000 cada uno
        game.overtime_bonus_accumulated = Decimal("70000.00")
        game.overtime_challenges_completed = 2

        summary = game.close_month()

        # Salario base devengado = 25 * $40.000 = $1.000.000,00
        assert summary["base_salary_earned"] == Decimal("1000000.00")
        assert summary["absence_deduction"] == Decimal("200000.00")
        assert summary["overtime_earned"] == Decimal("70000.00")
        # Sueldo en mano neto = $1.000.000 + $70.000 = $1.070.000,00
        assert summary["net_salary_liquidated"] == Decimal("1070000.00")

    def test_daily_work_quiz_attendance_recording(self) -> None:
        """Responder el cuestionario diario registra el día como trabajado."""
        game = WebEconomicGame()
        assert game.current_day == 1
        assert 1 not in game.attendance

        # Responder el quiz del día 1
        res = game.answer_work_quiz(selected_option_index=1)
        assert res["worked"] is True
        assert game.attendance[1] is True
        assert game.worked_days_count == 1

    def test_skip_day_attendance_recording(self) -> None:
        """Saltear la jornada laboral sin trabajar registra una falta."""
        game = WebEconomicGame()
        assert 1 not in game.attendance

        res = game.skip_day_unworked()
        assert res["worked"] is False
        assert game.attendance[1] is False
        assert game.unworked_days_count == 1
