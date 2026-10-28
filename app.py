"""Servidor Web Flask y API RESTful para el Simulador Economico.
Provee endpoints para el HUD gamificado, tarjetas interactivas de decision,
asistencia laboral diaria, horas extras condicionales y resolucion de eventos imprevistos.
SIN EMOJIS - Diseno estructurado para interfaz estilo videojuego RPG.
"""

from decimal import Decimal
from pathlib import Path
import sys
from typing import Any

from flask import Flask, jsonify, render_template, request
from flask.json.provider import DefaultJSONProvider

# Anadir src al sys.path
SRC_DIR = str(Path(__file__).resolve().parent / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from simulador.web_game import WebEconomicGame, create_demo_game_day_28


class CustomJSONProvider(DefaultJSONProvider):
    """Proveedor JSON que serializa Decimal a float para APIs y componentes UI."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def create_app(test_config: dict = None) -> Flask:
    """Fabrica de la aplicacion Flask."""
    template_dir = Path(__file__).resolve().parent / "src" / "simulador" / "templates"
    static_dir = Path(__file__).resolve().parent / "src" / "simulador" / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir)
    )
    app.json = CustomJSONProvider(app)

    if test_config:
        app.config.update(test_config)

    # Instancias del simulador: Partida estandar y Modo Demo / Administrador
    standard_game = WebEconomicGame()
    app.standard_game = standard_game
    app.demo_game = None
    app.active_mode = "standard"  # "standard" | "demo"

    # app.game apunta a la sesion activa actual
    app.game = standard_game

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/state", methods=["GET"])
    def get_state():
        return jsonify(app.game.get_state())

    @app.route("/api/work_quiz", methods=["GET"])
    def get_work_quiz():
        quiz = app.game.get_daily_quiz()
        sanitized = {
            "id": quiz["id"],
            "topic": quiz["topic"],
            "question": quiz["question"],
            "options": quiz["options"]
        }
        return jsonify(sanitized)

    @app.route("/api/work_quiz", methods=["POST"])
    def answer_work_quiz():
        data = request.get_json() or {}
        if "option_index" not in data:
            return jsonify({"error": "Falta el campo option_index"}), 400
        
        result = app.game.answer_work_quiz(int(data["option_index"]))
        return jsonify(result)

    @app.route("/api/skip_day", methods=["POST"])
    def skip_day():
        result = app.game.skip_day_unworked()
        return jsonify(result)

    @app.route("/api/advance_day", methods=["POST"])
    def advance_day():
        result = app.game.advance_calendar_day()
        return jsonify(result)

    @app.route("/api/overtime_challenge", methods=["GET"])
    def get_overtime_challenge():
        if not app.game.can_request_overtime:
            return jsonify({
                "error": "Acceso denegado: Las horas extras solo estan disponibles si has completado la jornada laboral de hoy.",
                "locked": True
            }), 403

        challenge = app.game.request_overtime_challenge()
        sanitized = {
            "title": challenge["title"],
            "statement": challenge["statement"],
            "hint": challenge["hint"],
            "options": challenge["options"],
            "reward_amount": challenge["reward_amount"],
            "locked": False
        }
        return jsonify(sanitized)

    @app.route("/api/overtime_challenge", methods=["POST"])
    def submit_overtime_challenge():
        data = request.get_json() or {}
        if "option_index" not in data:
            return jsonify({"error": "Falta el campo option_index"}), 400
        
        result = app.game.submit_overtime_answer(int(data["option_index"]))
        return jsonify(result)

    @app.route("/api/decision", methods=["POST"])
    def set_decision():
        data = request.get_json() or {}
        cat = data.get("category")
        opt_id = data.get("option_id")
        if not cat or not opt_id:
            return jsonify({"error": "Parametros category y option_id requeridos"}), 400

        ok = app.game.set_discretionary_choice(cat, opt_id)
        if not ok:
            return jsonify({"error": "Opcion o categoria invalida"}), 400
        return jsonify({"success": True})

    @app.route("/api/daily_choice", methods=["POST"])
    def record_daily_choice():
        data = request.get_json() or {}
        cat = data.get("category")
        opt_id = data.get("option_id")
        bonus_u = Decimal(str(data.get("bonus_utility", "0.0")))
        cost = Decimal(str(data.get("cost", "0.0")))
        res = app.game.record_daily_choice(cat, opt_id, bonus_u, cost)
        return jsonify({
            "success": True,
            "cost_applied": res["cost_applied"],
            "remaining_cash": res["remaining_cash"],
            "current_debt": res["current_debt"],
            "cumulative_utility": res["cumulative_utility"],
            "state": app.game.get_state()
        })

    @app.route("/api/record_transit_strike", methods=["POST"])
    def record_transit_strike():
        app.game.transit_strike_occurred_this_month = True
        return jsonify({"success": True, "transit_strike_occurred": True})

    @app.route("/api/resolve_crisis", methods=["POST"])
    def resolve_crisis():
        data = request.get_json() or {}
        choice = data.get("choice", "cash")
        if choice not in ("cash", "finance"):
            return jsonify({"error": "Opcion de crisis invalida: debe ser 'cash' o 'finance'"}), 400

        result = app.game.resolve_crisis_decision(choice)
        return jsonify(result)

    @app.route("/api/end_month", methods=["POST"])
    def end_month():
        try:
            summary = app.game.close_month()
            is_over = app.game.is_game_over
            evaluation = app.game.get_final_evaluation() if is_over else None
            return jsonify({
                "success": True,
                "summary": summary,
                "is_game_over": is_over,
                "final_evaluation": evaluation,
                "state": app.game.get_state()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/final_evaluation", methods=["GET"])
    def get_final_evaluation():
        if not app.game.is_game_over:
            return jsonify({"error": "La simulacion aun no ha concluido los 6 meses"}), 400
        return jsonify({"success": True, "evaluation": app.game.get_final_evaluation()})

    @app.route("/api/admin/status", methods=["GET"])
    def get_admin_status():
        return jsonify({
            "active_mode": app.active_mode,
            "has_demo_session": app.demo_game is not None
        })

    @app.route("/api/admin/set_mode", methods=["POST"])
    def set_admin_mode():
        data = request.get_json() or {}
        requested_mode = data.get("mode", "demo")
        reload_demo = data.get("reload", False)

        if requested_mode == "demo":
            if app.demo_game is None or reload_demo:
                app.demo_game = create_demo_game_day_28()
            app.active_mode = "demo"
            app.game = app.demo_game
        else:
            app.active_mode = "standard"
            app.game = app.standard_game

        return jsonify({
            "success": True,
            "active_mode": app.active_mode,
            "state": app.game.get_state()
        })

    @app.route("/api/reset", methods=["POST"])
    def reset_game():
        if app.active_mode == "demo":
            app.demo_game = create_demo_game_day_28()
            app.game = app.demo_game
        else:
            app.standard_game = WebEconomicGame()
            app.game = app.standard_game
        return jsonify({"success": True, "state": app.game.get_state()})

    return app


if __name__ == "__main__":
    app = create_app()
    print("Iniciando Simulador Economico Web en http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=True)
