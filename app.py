"""Servidor Web Flask y API RESTful para el Simulador Económico.
Provee endpoints para el calendario de 30 días, jornada laboral, horas extras,
gastos fijos/discrecionales y liquidación mensual.
"""

from decimal import Decimal
from pathlib import Path
import sys
from typing import Any

from flask import Flask, jsonify, render_template, request
from flask.json.provider import DefaultJSONProvider

# Añadir src al sys.path
SRC_DIR = str(Path(__file__).resolve().parent / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from simulador.web_game import WebEconomicGame


class CustomJSONProvider(DefaultJSONProvider):
    """Proveedor JSON que serializa Decimal a float para APIs y gráficos."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def create_app(test_config: dict = None) -> Flask:
    """Fábrica de la aplicación Flask."""
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

    # Instancia global del juego
    game = WebEconomicGame()
    app.game = game

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/state", methods=["GET"])
    def get_state():
        return jsonify(app.game.get_state())

    @app.route("/api/work_quiz", methods=["GET"])
    def get_work_quiz():
        quiz = app.game.get_daily_quiz()
        # Ocultar correct_index en el cliente para no spoilear la respuesta
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
        challenge = app.game.request_overtime_challenge()
        sanitized = {
            "title": challenge["title"],
            "statement": challenge["statement"],
            "hint": challenge["hint"],
            "options": challenge["options"],
            "reward_amount": challenge["reward_amount"]
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
            return jsonify({"error": "Parámetros category y option_id requeridos"}), 400

        ok = app.game.set_discretionary_choice(cat, opt_id)
        if not ok:
            return jsonify({"error": "Opción o categoría inválida"}), 400
        return jsonify({"success": True})

    @app.route("/api/end_month", methods=["POST"])
    def end_month():
        try:
            summary = app.game.close_month()
            return jsonify({"success": True, "summary": summary})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/reset", methods=["POST"])
    def reset_game():
        app.game = WebEconomicGame()
        return jsonify({"success": True, "state": app.game.get_state()})

    return app


if __name__ == "__main__":
    app = create_app()
    print("Iniciando Simulador Económico Web en http://localhost:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=True)
