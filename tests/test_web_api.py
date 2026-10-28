"""Pruebas de integracion para la API RESTful de Flask del Simulador Economico."""

from decimal import Decimal
import pytest
from app import create_app


@pytest.fixture
def client():
    """Cliente de pruebas de Flask."""
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


class TestFlaskWebAPI:
    """Valida los endpoints y contratos JSON de la API con HUD gamificado y tarjetas."""

    def test_index_route(self, client) -> None:
        """La ruta principal GET / debe retornar el HTML del videojuego con status 200 y botones limpios."""
        res = client.get("/")
        assert res.status_code == 200
        html = res.data.decode("utf-8")
        assert "Simulador" in html
        assert "Partida" in html
        assert "Prueba" in html
        assert "Nivel 1: Juego Activo" not in html
        assert "Recoleta // 6 Turnos Mensuales" not in html
        assert "modal-final-summary" in html
        assert "modal-final-fullscreen" in html

    def test_get_state_endpoint(self, client) -> None:
        """GET /api/state retorna el estado completo del juego."""
        res = client.get("/api/state")
        assert res.status_code == 200
        data = res.get_json()

        assert data["current_month"] == 1
        assert data["current_day"] == 1
        assert data["days_per_month"] == 30
        assert data["worked_days"] == 0
        assert data["unworked_days"] == 0
        assert "cash" in data
        assert "fixed_costs" in data
        assert "discretionary_choices" in data
        assert "can_request_overtime" in data
        assert data["can_request_overtime"] is False  # Apenas inicia el dia 1 sin fichar

    def test_work_quiz_endpoints(self, client) -> None:
        """GET y POST /api/work_quiz para responder la jornada laboral."""
        # 1. Obtener pregunta
        quiz_res = client.get("/api/work_quiz")
        assert quiz_res.status_code == 200
        quiz = quiz_res.get_json()
        assert "question" in quiz
        assert len(quiz["options"]) == 4

        # 2. Responder pregunta
        answer_res = client.post("/api/work_quiz", json={"option_index": 1})
        assert answer_res.status_code == 200
        result = answer_res.get_json()
        assert result["worked"] is True
        assert "daily_salary_earned" in result
        assert result["can_request_overtime"] is True

        # 3. Verificar estado actualizado
        state_res = client.get("/api/state")
        state = state_res.get_json()
        assert state["worked_days"] == 1
        assert state["day_status"] == "worked"
        assert state["can_request_overtime"] is True

    def test_skip_and_advance_day(self, client) -> None:
        """Salteo de jornada laboral y avance en el calendario."""
        # Saltear dia 1
        skip_res = client.post("/api/skip_day")
        assert skip_res.status_code == 200
        assert skip_res.get_json()["worked"] is False
        assert skip_res.get_json()["can_request_overtime"] is False

        # Avanzar dia
        adv_res = client.post("/api/advance_day")
        assert adv_res.status_code == 200
        assert adv_res.get_json()["current_day"] == 2

        state = client.get("/api/state").get_json()
        assert state["current_day"] == 2
        assert state["unworked_days"] == 1

    def test_overtime_conditional_access(self, client) -> None:
        """Horas extras condicionales:
        Bloqueadas si no se ha trabajado en el dia. Desbloqueadas al fichar asistencia.
        """
        # En dia 1 sin fichar asistencia, debe retornar 403
        locked_res = client.get("/api/overtime_challenge")
        assert locked_res.status_code == 403
        assert locked_res.get_json()["locked"] is True

        # El jugador asiste a trabajar hoy respondiendo la trivia
        work_res = client.post("/api/work_quiz", json={"option_index": 1})
        assert work_res.status_code == 200

        # Ahora las horas extras estan DESBLOQUEADAS
        get_res = client.get("/api/overtime_challenge")
        assert get_res.status_code == 200
        challenge = get_res.get_json()
        assert "title" in challenge
        assert "statement" in challenge
        assert len(challenge["options"]) == 4

        # Enviar respuesta al desafio
        submit_res = client.post("/api/overtime_challenge", json={"option_index": 0})
        assert submit_res.status_code == 200
        res = submit_res.get_json()
        assert "is_correct" in res
        assert "total_overtime_accumulated" in res

    def test_decision_tree_subcards(self, client) -> None:
        """POST /api/decision para cambiar opciones simples y sub-tarjetas (arbol de consumo)."""
        # Sub-tarjeta de comida: Pizza
        res_pizza = client.post("/api/decision", json={
            "category": "comida_ocio",
            "option_id": "food_delivery_pizza"
        })
        assert res_pizza.status_code == 200

        # Mascota premium
        res_pet = client.post("/api/decision", json={
            "category": "mascotas",
            "option_id": "pet_premium"
        })
        assert res_pet.status_code == 200

        state = client.get("/api/state").get_json()
        assert state["discretionary_choices"]["comida_ocio"]["id"] == "food_delivery_pizza"
        assert state["discretionary_choices"]["mascotas"]["id"] == "pet_premium"

    def test_resolve_crisis_endpoint(self, client) -> None:
        """Prueba de resolucion de eventos imprevistos de crisis."""
        # Configurar manualmente una crisis activa en el backend
        from simulador.web_game import POSSIBLE_UNFORESEEN_EVENTS
        client.application.game._trigger_crisis_event(POSSIBLE_UNFORESEEN_EVENTS[0])

        state_before = client.get("/api/state").get_json()
        assert state_before["active_crisis"] is not None

        # Resolver pagando al contado
        res = client.post("/api/resolve_crisis", json={"choice": "cash"})
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        assert data["choice"] == "cash"

        state_after = client.get("/api/state").get_json()
        assert state_after["active_crisis"] is None

    def test_end_month_and_reset(self, client) -> None:
        """Cierre de mes y reinicio de la partida."""
        end_res = client.post("/api/end_month")
        assert end_res.status_code == 200
        summary = end_res.get_json()["summary"]
        assert summary["month"] == 1
        assert "net_salary_liquidated" in summary
        assert "total_fixed_cost" in summary

        # Estado tras cerrar mes: paso a mes 2
        state = client.get("/api/state").get_json()
        assert state["current_month"] == 2
        assert state["current_day"] == 1

        # Reiniciar partida
        reset_res = client.post("/api/reset")
        assert reset_res.status_code == 200
        reset_state = reset_res.get_json()["state"]
        assert reset_state["current_month"] == 1
        assert reset_state["current_day"] == 1
