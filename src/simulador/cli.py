"""Interfaz de Terminal (CLI) con formato visual avanzado utilizando Rich.
Presenta paneles económicos, alertas de inflación, selección de alternativas
de consumo y reportes mensuales con pedagogía económica.
"""

from decimal import Decimal
from pathlib import Path
import sys
from typing import List, Optional

# Garantizar que el paquete simulador sea accesible al ejecutar el script directamente
SRC_DIR = str(Path(__file__).resolve().parent.parent)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.text import Text

from simulador.game import EconomicSurvivalGame
from simulador.models import Category, ConsumptionChoice, MonthTurnResult


def format_currency(val: Decimal) -> str:
    """Formatea un Decimal como moneda en ARS con separador de miles y centavos."""
    # Formato argentino: $ 1.200.000,00
    parts = f"{val:,.2f}".split(".")
    integer_part = parts[0].replace(",", ".")
    decimal_part = parts[1]
    return f"${integer_part},{decimal_part}"


class EconomicCliApp:
    """Aplicación CLI interactiva para el Simulador Económico."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console(legacy_windows=False)
        self.game = EconomicSurvivalGame()

    def print_welcome(self) -> None:
        """Imprime la pantalla de bienvenida y contexto económico."""
        welcome_text = Text()
        welcome_text.append("¡Bienvenido al Simulador de Supervivencia Económica!\n", style="bold yellow")
        welcome_text.append(
            "Durante 6 meses deberás administrar tu presupuesto en la Ciudad de Buenos Aires (Recoleta).\n"
            "Aplicarás Teoría del Consumidor, evaluarás el Efecto Sustitución y navegarás shocks macroeconómicos.\n\n",
            style="white"
        )
        welcome_text.append("• Restricción Presupuestaria: ", style="bold cyan")
        welcome_text.append(f"Salario inicial de {format_currency(self.game.initial_salary)} al inicio de cada mes.\n")
        welcome_text.append("• Costos Fijos Obligatorios: ", style="bold cyan")
        welcome_text.append("Alquiler en Recoleta, Edesur + AySA, Membresía Platino Plus en Megatlon.\n")
        welcome_text.append("• Tasa de Deuda Financiera: ", style="bold cyan")
        welcome_text.append(
            f"TNA {self.game.tna * 100:.1f}% | TEM {self.game.tem * 100:.2f}% | TEA {self.game.tea * 100:.2f}%\n"
        )
        welcome_text.append("• Objetivo: ", style="bold green")
        welcome_text.append("Maximizar tu Bienestar/Utilidad total sin caer en insolvencia irreversible.\n")

        self.console.print(Panel(welcome_text, title=" SIMULADOR ECONÓMICO CLI", border_style="bright_blue"))

    def render_dashboard(self) -> None:
        """Renderiza el tablero de control del estado actual."""
        state = self.game.state
        table = Table(title=f" TABLERO DE CONTROL - MES {state.month} DE 6", expand=True)
        table.add_column("Salario Mensual", style="bold green", justify="center")
        table.add_column("Ahorros Previos", style="green", justify="center")
        table.add_column("Deuda Bancaria", style="red", justify="center")
        table.add_column("IPC Acumulado", style="yellow", justify="center")
        table.add_column("Utilidad Acumulada", style="magenta", justify="center")

        debt_style = "bold red" if state.debt > Decimal("0.00") else "dim white"
        table.add_row(
            format_currency(state.monthly_salary),
            format_currency(state.cash),
            f"[{debt_style}]{format_currency(state.debt)}[/{debt_style}]",
            f"{state.ipc_index:.4f}x",
            f"{state.cumulative_utility:.1f} pts"
        )
        self.console.print(table)

    def prompt_user_choices(self) -> List[ConsumptionChoice]:
        """Solicita interactivamente al usuario sus decisiones de consumo para cada categoría."""
        selected_choices: List[ConsumptionChoice] = []
        ipc = self.game.state.ipc_index

        for category, options in self.game.catalog.items():
            self.console.print(f"\n[bold underline]{category.value}[/bold underline]:")
            for idx, opt in enumerate(options, 1):
                effective_cost = opt.calculate_cost(ipc)
                self.console.print(
                    f"  [bold cyan]({idx})[/bold cyan] {opt.name} "
                    f"-> [bold green]{format_currency(effective_cost)}[/bold green] "
                    f"(Utilidad: [magenta]+{opt.utility:.0f}[/magenta])"
                )
                self.console.print(f"      [dim]{opt.description}[/dim]")

            while True:
                choice_str = Prompt.ask(
                    f"  Selecciona opción para {category.value}",
                    choices=["1", "2"],
                    default="1"
                )
                if choice_str in ("1", "2"):
                    selected = options[int(choice_str) - 1]
                    selected_choices.append(selected)
                    break

        return selected_choices

    def render_turn_result(self, result: MonthTurnResult) -> None:
        """Muestra el balance detallado del mes finalizado."""
        # Alerta de shock inflacionario si ocurrió este mes
        if result.inflation_rate_turn > self.game.macro_engine.base_monthly_inflation:
            shock_pct = result.inflation_rate_turn * 100
            self.console.print(Panel(
                f" [bold red]¡SHOCK MACROECONÓMICO DETECTADO![/bold red]\n"
                f"El IPC sufrió un salto del [bold yellow]{shock_pct:.2f}%[/bold yellow] este mes.\n"
                f"Los precios de la canasta básica, servicios y gimnasio aumentaron inmediatamente.",
                title=" ALERTA DE INFLACIÓN (IPC)",
                border_style="red"
            ))

        # Alerta de intereses si hubo deuda
        if result.interest_applied > Decimal("0.00"):
            self.console.print(Panel(
                f" [bold red]COSTO FINANCIERO DE LA DEUDA:[/bold red]\n"
                f"Se debitaron [bold yellow]{format_currency(result.interest_applied)}[/bold yellow] de intereses "
                f"(TEM: {self.game.tem * 100:.2f}%, TNA: {self.game.tna * 100:.1f}%, TEA: {self.game.tea * 100:.2f}%).",
                title=" LIQUIDACIÓN BANCARIA",
                border_style="dark_orange"
            ))

        # Alerta de evento imprevisto
        if result.unforeseen_event:
            self.console.print(Panel(
                f" [bold yellow]{result.unforeseen_event.title}[/bold yellow]\n"
                f"{result.unforeseen_event.description}\n"
                f"Costo abonado: [bold red]{format_currency(result.unforeseen_cost)}[/bold red]",
                title=" GASTO IMPREVISTO (MASCOTAS)",
                border_style="yellow"
            ))

        # Tabla de resumen financiero del mes
        table = Table(title=f" LIQUIDACIÓN MENSUAL - CIERRE MES {result.month}", expand=True)
        table.add_column("Concepto", style="cyan")
        table.add_column("Monto / Detalle", justify="right")

        table.add_row("Salario Percibido", f"[green]+{format_currency(result.salary_received)}[/green]")
        table.add_row("Total Costos Fijos (Recoleta, Servicios, Megatlon)", f"[red]-{format_currency(result.total_fixed_cost)}[/red]")
        table.add_row("Total Costos Variables Elegidos", f"[red]-{format_currency(result.total_variable_cost)}[/red]")
        if result.unforeseen_cost > Decimal("0.00"):
            table.add_row("Gasto Imprevisto Mascotas", f"[red]-{format_currency(result.unforeseen_cost)}[/red]")
        if result.interest_applied > Decimal("0.00"):
            table.add_row("Intereses por Deuda (TEM)", f"[red]-{format_currency(result.interest_applied)}[/red]")

        table.add_section()
        table.add_row("Efectivo Final al Cierre", f"[bold green]{format_currency(result.ending_cash)}[/bold green]")
        table.add_row("Deuda Remanente / Préstamo Activo", f"[bold red]{format_currency(result.new_debt)}[/bold red]")
        table.add_row("Utilidad Obtenida en el Turno", f"[magenta]+{result.utility_gained:.1f} pts[/magenta]")
        table.add_row("Utilidad Acumulada", f"[bold magenta]{result.cumulative_utility:.1f} pts[/bold magenta]")

        self.console.print(table)

    def render_final_game_summary(self) -> None:
        """Genera el informe final del tutor de economía y evaluación de resultados."""
        final_state = self.game.state
        summary = Text()
        summary.append(" EVALUACIÓN FINAL DEL TUTOR DE ECONOMÍA\n\n", style="bold yellow")

        if final_state.debt == Decimal("0.00") and final_state.cash >= Decimal("0.00"):
            summary.append("¡SUPERVIVENCIA EXITOSA!\n", style="bold green")
            summary.append(
                "Has logrado sortear los 6 meses sin quebrar ni acumular deuda bancaria impaga.\n",
                style="white"
            )
        else:
            summary.append("ADVERTENCIA DE VULNERABILIDAD FINANCIERA:\n", style="bold red")
            summary.append(
                f"Finalizaste el semestre con una deuda bancaria de {format_currency(final_state.debt)}.\n"
                "La tasa de interés (TEA ~79.6%) generó un costo de oportunidad severo sobre tu renta futura.\n",
                style="yellow"
            )

        summary.append(f"\n• Efectivo Final: {format_currency(final_state.cash)}\n")
        summary.append(f"• Deuda Final: {format_currency(final_state.debt)}\n")
        summary.append(f"• Patrimonio Neto Final: {format_currency(final_state.net_worth)}\n")
        summary.append(f"• Utilidad Total Acumulada: {final_state.cumulative_utility:.1f} puntos de bienestar\n")
        summary.append(f"• IPC Final tras 6 meses: {final_state.ipc_index:.4f}x\n")

        self.console.print(Panel(summary, title=" FIN DE LA SIMULACIÓN DE 6 MESES", border_style="bright_magenta"))

    def run(self) -> None:
        """Bucle principal de ejecución de los 6 meses."""
        self.print_welcome()

        for month in range(1, EconomicSurvivalGame.TOTAL_MONTHS + 1):
            self.console.rule(f"[bold blue]INICIO DEL MES {month} DE {EconomicSurvivalGame.TOTAL_MONTHS}[/bold blue]")
            self.render_dashboard()
            chosen_choices = self.prompt_user_choices()
            turn_result = self.game.execute_turn(chosen_choices)
            self.render_turn_result(turn_result)

            if month < EconomicSurvivalGame.TOTAL_MONTHS:
                Prompt.ask("\nPresiona [bold cyan]Enter[/bold cyan] para avanzar al siguiente mes...")

        self.render_final_game_summary()


def main() -> None:
    """Punto de entrada de la CLI."""
    app = EconomicCliApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n\nSimulación cancelada por el usuario.")
        sys.exit(0)


if __name__ == "__main__":
    main()
