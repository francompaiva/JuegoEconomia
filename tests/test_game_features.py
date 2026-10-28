"""Pruebas adicionales de integracion y modelos matematicos del Life-Sim RPG:
- Arbol de consumo y sub-tarjetas dinamicas (Delivery Pizza/Burger/Ensalada).
- Horas extras condicionales con bloqueo estricto por asistencia.
- Resolucion de tarjetas de crisis (contado vs financiado +15%).
- Precision aritmetica al centavo con ROUND_HALF_UP.
"""

from decimal import Decimal
import pytest

from simulador.web_game import WebEconomicGame, POSSIBLE_UNFORESEEN_EVENTS, create_demo_game_day_28


class TestLifeSimGameMechanics:
    """Valida los pilares de jugabilidad y precision matematica de la aplicacion."""

    def test_overtime_locked_when_unworked(self) -> None:
        """Horas extras deben arrojar ValueError si no se ha trabajado en la jornada."""
        game = WebEconomicGame()
        assert game.can_request_overtime is False

        with pytest.raises(ValueError, match="Acceso denegado"):
            game.request_overtime_challenge()

    def test_overtime_locked_when_skipped_absence(self) -> None:
        """Si el jugador decide no ir a trabajar (ausencia), las horas extras deben quedar bloqueadas."""
        game = WebEconomicGame()
        game.skip_day_unworked()
        assert game.can_request_overtime is False

        with pytest.raises(ValueError, match="Acceso denegado"):
            game.request_overtime_challenge()

    def test_overtime_unlocked_when_worked_and_solved(self) -> None:
        """Al fichar y responder la trivia, las horas extras se desbloquean y se suma el bono si acierta."""
        game = WebEconomicGame()
        game.answer_work_quiz(selected_option_index=1)
        assert game.can_request_overtime is True

        challenge = game.request_overtime_challenge()
        assert "reward_amount" in challenge
        correct_idx = challenge["correct_index"]

        res = game.submit_overtime_answer(correct_idx)
        assert res["is_correct"] is True
        assert game.overtime_bonus_accumulated == Decimal("35000.00")
        assert game.overtime_challenges_completed == 1

    def test_decision_tree_subcards_selection(self) -> None:
        """Verifica que las sub-tarjetas de delivery y movilidad se seleccionen y calculen correctamente."""
        game = WebEconomicGame()
        game.current_ipc = Decimal("1.1000")

        # Seleccionar sub-tarjeta de Pizza
        ok = game.set_discretionary_choice("comida_ocio", "food_delivery_pizza")
        assert ok is True
        assert game.selected_discretionary["comida_ocio"] == "food_delivery_pizza"

        state = game.get_state()
        pizza_info = state["discretionary_choices"]["comida_ocio"]
        # Costo base 180000 * 1.1000 = 198000.00
        assert pizza_info["cost"] == Decimal("198000.00")
        assert pizza_info["utility"] == Decimal("80.0")

        # Seleccionar sub-tarjeta de Hamburguesa
        ok = game.set_discretionary_choice("comida_ocio", "food_delivery_burger")
        assert ok is True
        # Costo base 220000 * 1.1000 = 242000.00
        state = game.get_state()
        burger_info = state["discretionary_choices"]["comida_ocio"]
        assert burger_info["cost"] == Decimal("242000.00")
        assert burger_info["utility"] == Decimal("100.0")

    def test_crisis_resolution_cash_vs_finance(self) -> None:
        """Compara la resolucion de crisis pagada al contado vs financiada (+15%)."""
        # Caso 1: Al contado
        game_cash = WebEconomicGame()
        game_cash.current_ipc = Decimal("1.0000")
        med_event = POSSIBLE_UNFORESEEN_EVENTS[0]  # Base 45000.00, impact -20.0
        game_cash._trigger_crisis_event(med_event)

        initial_cash = game_cash.cash
        res_cash = game_cash.resolve_crisis_decision("cash")
        assert res_cash["amount_paid"] == Decimal("45000.00")
        assert game_cash.cash == initial_cash - Decimal("45000.00")
        assert game_cash.cumulative_utility == Decimal("-20.0")

        # Caso 2: Financiado (+15% de recargo)
        game_fin = WebEconomicGame()
        game_fin.current_ipc = Decimal("1.0000")
        game_fin._trigger_crisis_event(med_event)

        initial_cash_fin = game_fin.cash
        res_fin = game_fin.resolve_crisis_decision("finance")
        # 45000 * 1.15 = 51750.00
        assert res_fin["amount_paid"] == Decimal("51750.00")
        assert game_fin.cash == initial_cash_fin - Decimal("51750.00")
        assert game_fin.cumulative_utility == Decimal("-30.0")  # -20 * 1.5

    def test_ipc_shock_increases_all_card_costs(self) -> None:
        """Verifica que un shock del IPC incremente el costo de todas las tarjetas y opciones."""
        game = WebEconomicGame()
        game.current_ipc = Decimal("1.2500")

        state = game.get_state()
        catalog = state["catalog"]

        # En transporte publico: base 35000 * 1.25 = 43750.00
        trans_pub = next(o for o in catalog["transporte"] if o["id"] == "trans_publico")
        assert trans_pub["cost"] == Decimal("43750.00")

        # En comida cocina: base 95000 * 1.25 = 118750.00
        food_cocina = next(o for o in catalog["comida_ocio"] if o["id"] == "food_cocina")
        assert food_cocina["cost"] == Decimal("118750.00")

    def test_overtime_badge_tracking_in_calendar(self) -> None:
        """Verifica que el casillero de horas extras en el calendario se registre tras completar la actividad."""
        game = WebEconomicGame()
        game.answer_work_quiz(selected_option_index=1)
        assert game.overtime_done_today.get(1) is None

        challenge = game.request_overtime_challenge()
        game.submit_overtime_answer(challenge["correct_index"])
        assert game.overtime_done_today.get(1) is True

        state = game.get_state()
        assert "overtime_calendar" in state
        assert state["overtime_calendar"]["1"] is True
        assert state["overtime_calendar"]["2"] is False

    def test_overtime_reward_by_participation_even_if_incorrect(self) -> None:
        """Verifica que realizar horas extras acredite la bonificacion por participacion aun si la respuesta no es 100% exacta."""
        game = WebEconomicGame()
        game.answer_work_quiz(selected_option_index=1)
        challenge = game.request_overtime_challenge()
        wrong_idx = (challenge["correct_index"] + 1) % 4
        res = game.submit_overtime_answer(wrong_idx)
        assert res["is_correct"] is False
        assert game.overtime_bonus_accumulated == Decimal("35000.00")
        assert game.overtime_done_today.get(1) is True
        assert game.get_state()["overtime_calendar"]["1"] is True

    def test_daily_choice_api_endpoint(self) -> None:
        """Verifica que el endpoint /api/daily_choice actualice las micro-decisiones, descuente dinero en tiempo real y sume utilidad."""
        from app import create_app
        app = create_app({"TESTING": True})
        with app.test_client() as client:
            initial_state = client.get("/api/state").get_json()
            initial_cash = Decimal(str(initial_state["cash"]))

            res = client.post("/api/daily_choice", json={
                "category": "comida_ocio",
                "option_id": "food_delivery_pizza",
                "bonus_utility": 15.0,
                "cost": 5000.0
            })
            assert res.status_code == 200
            data = res.get_json()
            assert data["success"] is True
            assert data["state"]["discretionary_choices"]["comida_ocio"]["id"] == "food_delivery_pizza"
            assert data["state"]["cumulative_utility"] == 15.0
            assert Decimal(str(data["remaining_cash"])) == initial_cash - Decimal("5000.00")

    def test_month_starts_in_march(self) -> None:
        """Verifica que el juego comience explicitamente en el mes de MARZO."""
        game = WebEconomicGame()
        assert game.current_month == 1
        assert game.month_name == "Marzo"
        state = game.get_state()
        assert state["month_name"] == "Marzo"
        assert state["current_month_name"] == "Marzo"

    def test_fixed_costs_capped_at_620k(self) -> None:
        """Verifica que los costos fijos iniciales sumen exactamente $620.000,00 ARS."""
        game = WebEconomicGame()
        game.current_ipc = Decimal("1.0000")
        assert game.get_total_fixed_costs() == Decimal("620000.00")

    def test_home_cooking_dinner_zero_utility(self) -> None:
        """Cocinar en casa por la noche otorga 0 puntos de bienestar (tarea cotidiana)."""
        game = WebEconomicGame()
        food_cocina = next(o for o in game.catalog["comida_ocio"] if o.id == "food_cocina")
        assert food_cocina.utility == Decimal("0.0")

    def test_unforeseen_events_cooldown_no_consecutive_repeats(self) -> None:
        """Verifica que el cooldown impida que un mismo evento imprevisto se repita consecutivamente."""
        game = WebEconomicGame()
        ev1 = game._pick_unforeseen_event()
        ev2 = game._pick_unforeseen_event()
        ev3 = game._pick_unforeseen_event()
        assert ev1.id != ev2.id
        assert ev2.id != ev3.id

    def test_create_demo_game_day_28_initial_state(self) -> None:
        """Verifica que la partida de muestra para el Administrador cargue en el Dia 28 del Mes 6 para el usuario 'prueba'."""
        demo = create_demo_game_day_28(seed=42)
        assert demo.is_demo_mode is True
        assert demo.username == "prueba"
        assert demo.current_month == 6
        assert demo.month_name == "Agosto"
        assert demo.current_day == 28
        assert len(demo.month_history) == 5  # 5 meses previos simulados
        assert demo.cash > Decimal("1000000.00")
        assert demo.cumulative_utility > Decimal("400.0")
        assert demo.overtime_challenges_completed == 3
        assert demo.overtime_bonus_accumulated == Decimal("105000.00")
        assert demo.transit_strike_occurred_this_month is True
        assert demo.current_ipc > Decimal("1.25")

        # Verificar asistencias acumuladas hasta el dia 27 del mes 6
        worked = [d for d, att in demo.attendance.items() if att is True]
        unworked = [d for d, att in demo.attendance.items() if att is False]
        assert len(worked) == 24
        assert len(unworked) == 3
        # El dia 28 debe estar pendiente (no registrado)
        assert 28 not in demo.attendance

        # Horas extras en dias 4, 11, 18
        assert demo.overtime_done_today[4] is True
        assert demo.overtime_done_today[11] is True
        assert demo.overtime_done_today[18] is True

        # Estado serializado para API
        state = demo.get_state()
        assert state["is_demo_mode"] is True
        assert state["game_mode"] == "demo"
        assert state["username"] == "prueba"
        assert state["current_month"] == 6
        assert state["month_name"] == "Agosto"
        assert state["current_day"] == 28
        assert state["attendance_calendar"]["28"] is None
        assert len(state["month_history"]) == 5

    def test_admin_mode_api_isolation(self) -> None:
        """Verifica que cambiar al modo Demo y realizar acciones no altere la partida estandar en curso."""
        from app import create_app

        app = create_app()
        client = app.test_client()

        # Partida estandar inicial en dia 1, mes 1
        res = client.get("/api/state")
        assert res.status_code == 200
        data = res.get_json()
        assert data["current_day"] == 1
        assert data["current_month"] == 1
        assert data["is_demo_mode"] is False
        assert data["username"] == "jugador"
        assert data["discretionary_choices"]["comida_ocio"]["id"] == "food_cocina"

        # Cambiar a modo Demo (Dia 28 del Mes 6)
        res_demo = client.post("/api/admin/set_mode", json={"mode": "demo", "reload": True})
        assert res_demo.status_code == 200
        demo_data = res_demo.get_json()
        assert demo_data["success"] is True
        assert demo_data["active_mode"] == "demo"
        assert demo_data["state"]["current_month"] == 6
        assert demo_data["state"]["month_name"] == "Agosto"
        assert demo_data["state"]["current_day"] == 28
        assert demo_data["state"]["is_demo_mode"] is True
        assert demo_data["state"]["username"] == "prueba"

        # Realizar un gasto en modo demo
        client.post("/api/daily_choice", json={
            "category": "comida_ocio",
            "option_id": "food_delivery_pizza",
            "bonus_utility": 15.0,
            "cost": 10000.0
        })

        # Verificar que el modo demo registro el gasto
        res_demo_state = client.get("/api/state")
        assert res_demo_state.get_json()["current_day"] == 28
        assert res_demo_state.get_json()["current_month"] == 6
        assert res_demo_state.get_json()["discretionary_choices"]["comida_ocio"]["id"] == "food_delivery_pizza"

        # Volver al modo estandar: debe seguir intacto en Mes 1, Dia 1 con opciones base
        res_std = client.post("/api/admin/set_mode", json={"mode": "standard"})
        assert res_std.status_code == 200
        std_data = res_std.get_json()
        assert std_data["active_mode"] == "standard"
        assert std_data["state"]["current_day"] == 1
        assert std_data["state"]["current_month"] == 1
        assert std_data["state"]["is_demo_mode"] is False
        assert std_data["state"]["username"] == "jugador"
        assert std_data["state"]["discretionary_choices"]["comida_ocio"]["id"] == "food_cocina"

    def test_demo_mode_advances_and_closes_month_6_with_final_evaluation(self) -> None:
        """Verifica que el modo demo culmine el Mes 6 y desencadene la evaluacion final consolidada de 6 meses."""
        demo = create_demo_game_day_28(seed=42)
        assert demo.current_month == 6
        assert len(demo.month_history) == 5

        # Dia 28
        demo.answer_work_quiz(0)
        assert demo.attendance[28] is True
        demo.advance_calendar_day()
        assert demo.current_day == 29

        # Dia 29
        demo.answer_work_quiz(0)
        assert demo.attendance[29] is True
        demo.advance_calendar_day()
        assert demo.current_day == 30

        # Dia 30
        demo.answer_work_quiz(0)
        assert demo.attendance[30] is True
        assert demo.current_day == 30

        # Liquidacion del Mes 6
        summary = demo.close_month()
        assert summary["month"] == 6
        assert summary["month_name"] == "Agosto"
        assert summary["worked_days"] == 27  # 24 iniciales + 3 jugados
        assert summary["unworked_days"] == 3
        assert summary["overtime_earned"] == 105000.00
        assert len(demo.month_history) == 6

        # Estado fin del juego (6 meses terminados)
        assert demo.is_game_over is True
        final_eval = demo.get_final_evaluation()
        assert final_eval["total_months"] == 6
        assert final_eval["username"] == "prueba"
        assert final_eval["final_cash"] > 0
        assert final_eval["final_debt"] == Decimal("0.00")
        assert final_eval["status_code"] in ("excelente", "estable")
        assert "tutor_verdict" in final_eval
        assert len(final_eval["months_summary"]) == 6
        assert summary["ending_cash"] > 0



