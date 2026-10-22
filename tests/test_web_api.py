"""Pruebas de integración para la API RESTful de Flask del Simulador Económico."""

import pytest
from app import create_app


@pytest.fixture
def client():
    """Cliente de pruebas de Flask."""
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


class TestFlaskWebAPI:
    """Valida los endpoints y contratos JSON de la API."""

    def test_index_route(self, client) -> None:
        """La ruta principal GET / debe retornar el HTML del dashboard con status 200."""
        res = client.get("/")
        assert res.status_code == 200
        assert b"Simulador Econ\xc3\xb3mico Web" in res.data or b"Simulador" in res.data
        assert b"calendar-grid" in res.data

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

        # 3. Verificar estado actualizado
        state_res = client.get("/api/state")
        state = state_res.get_json()
        assert state["worked_days"] == 1
        assert state["day_status"] == "worked"

    def test_skip_and_advance_day(self, client) -> None:
        """Salteo de jornada laboral y avance en el calendario."""
        # Saltear día 1
        skip_res = client.post("/api/skip_day")
        assert skip_res.status_code == 200
        assert skip_res.get_json()["worked"] is False

        # Avanzar día
        adv_res = client.post("/api/advance_day")
        assert adv_res.status_code == 200
        assert adv_res.get_json()["current_day"] == 2

        state = client.get("/api/state").get_json()
        assert state["current_day"] == 2
        assert state["unworked_days"] == 1

    def test_overtime_challenge_flow(self, client) -> None:
        """Flujo completo de horas extras con fórmulas matemáticas."""
        get_res = client.get("/api/overtime_challenge")
        assert get_res.status_code == 200
        challenge = get_res.get_json()
        assert "title" in challenge
        assert "statement" in challenge
        assert len(challenge["options"]) == 4

        # Enviar respuesta
        submit_res = client.post("/api/overtime_challenge", json={"option_index": 0})
        assert submit_res.status_code == 200
        res = submit_res.get_json()
        assert "is_correct" in res
        assert "total_overtime_accumulated" in res

    def test_set_decision_endpoint(self, client) -> None:
        """POST /api/decision para cambiar una opción de estilo de vida."""
        res = client.post("/api/decision", json={
            "category": "transporte",
            "option_id": "trans_uber"
        })
        assert res.status_code == 200
        assert res.get_json()["success"] is True

        state = client.get("/api/state").get_json()
        assert state["discretionary_choices"]["transporte"]["id"] == "trans_uber"

    def test_end_month_and_reset(self, client) -> None:
        """Cierre de mes y reinicio de la partida."""
        end_res = client.post("/api/end_month")
        assert end_res.status_code == 200
        summary = end_res.get_json()["summary"]
        assert summary["month"] == 1
        assert "net_salary_liquidated" in summary
        assert "total_fixed_cost" in summary

        # Estado tras cerrar mes: pasó a mes 2
        state = client.get("/api/state").get_json()
        assert state["current_month"] == 2
        assert state["current_day"] == 1

        # Reiniciar partida
        reset_res = client.post("/api/reset")
        assert reset_res.status_code == 200
        reset_state = reset_res.get_json()["state"]
        assert reset_state["current_month"] == 1
        assert reset_state["current_day"] == 1
