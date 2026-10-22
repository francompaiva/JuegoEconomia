/**
 * Simulador Económico Web - Controlador del Dashboard
 * Maneja la interacción con la API RESTful de Flask, actualización del calendario,
 * modales nativos <dialog> y renderizado del gráfico de gastos con Chart.js.
 */

let expensesChartInstance = null;
let currentGameState = null;

// Formateador de moneda argentina ($ 1.200.000,00)
function formatCurrency(val) {
  if (val === null || val === undefined) return "$0,00";
  const num = typeof val === "number" ? val : parseFloat(val);
  return "$" + num.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Inicialización al cargar el DOM
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  fetchState();
});

function initEventListeners() {
  document.getElementById("btn-reset").addEventListener("click", resetGame);
  document.getElementById("btn-open-work-quiz").addEventListener("click", openWorkQuizModal);
  document.getElementById("btn-skip-day").addEventListener("click", skipDay);
  document.getElementById("btn-advance-day").addEventListener("click", advanceDay);
  document.getElementById("btn-request-overtime").addEventListener("click", requestOvertime);
  document.getElementById("btn-end-month").addEventListener("click", closeAndLiquidateMonth);

  document.getElementById("btn-close-quiz").addEventListener("click", () => {
    const dialog = document.getElementById("modal-work-quiz");
    dialog.close();
    fetchState();
  });

  document.getElementById("btn-acknowledge-month").addEventListener("click", () => {
    const dialog = document.getElementById("modal-end-month");
    dialog.close();
    fetchState();
  });
}

// -----------------------------------------------------------------------------
// Consumo del Estado de la Partida
// -----------------------------------------------------------------------------
async function fetchState() {
  try {
    const res = await fetch("/api/state");
    const data = await res.json();
    currentGameState = data;
    renderDashboard(data);
  } catch (err) {
    console.error("Error al obtener el estado:", err);
  }
}

function renderDashboard(state) {
  // 1. KPIs Superiores
  document.getElementById("badge-month").textContent = `Mes ${state.current_month} de ${state.total_months}`;
  document.getElementById("kpi-cash").textContent = formatCurrency(state.cash);
  document.getElementById("kpi-debt").textContent = formatCurrency(state.debt);
  document.getElementById("kpi-rate").textContent = `TNA ${(state.tna * 100).toFixed(1)}% | TEM ${(state.tem * 100).toFixed(2)}% | TEA ${(state.tea * 100).toFixed(2)}%`;
  document.getElementById("kpi-net-worth").textContent = formatCurrency(state.net_worth);
  document.getElementById("kpi-ipc").textContent = `${state.current_ipc.toFixed(4)}x`;
  document.getElementById("kpi-inflation-badge").textContent = `Inflación acumulada: +${((state.current_ipc - 1) * 100).toFixed(2)}%`;
  document.getElementById("kpi-utility").textContent = `${state.cumulative_utility.toFixed(1)} pts`;

  // 2. Franja Salarial
  document.getElementById("strip-base-salary").textContent = formatCurrency(state.base_salary);
  document.getElementById("strip-worked-days").textContent = `${state.worked_days} / ${state.days_per_month}`;
  document.getElementById("strip-projected-salary").textContent = formatCurrency(state.projected_salary);
  document.getElementById("strip-absence-deduction").textContent = `-${formatCurrency(state.projected_absence_deduction)}`;
  document.getElementById("strip-overtime-bonus").textContent = `+${formatCurrency(state.overtime_bonus_accumulated)}`;

  // 3. Calendario Mensual de 30 Días
  renderCalendar(state);

  // 4. Botones de acción diaria
  const btnWork = document.getElementById("btn-open-work-quiz");
  const btnSkip = document.getElementById("btn-skip-day");
  const btnAdvance = document.getElementById("btn-advance-day");
  const btnEndMonth = document.getElementById("btn-end-month");
  const endMonthHint = document.getElementById("end-month-hint");

  const isDayPending = (state.day_status === "pending");
  btnWork.disabled = !isDayPending;
  btnSkip.disabled = !isDayPending;
  btnAdvance.disabled = isDayPending; // Solo avanzar si ya se jugó o salteó el día

  if (state.current_day === state.days_per_month && !isDayPending) {
    btnEndMonth.disabled = false;
    btnAdvance.disabled = true;
    endMonthHint.textContent = "¡Has completado el día 30! Presiona Cerrar y Liquidar Mes.";
  } else {
    btnEndMonth.disabled = true;
    endMonthHint.textContent = `Día actual: ${state.current_day} de 30. Debes llegar al día 30 para liquidar.`;
  }

  // 5. Gastos Fijos
  renderFixedCosts(state.fixed_costs, state.total_fixed_costs);

  // 6. Selectores de Estilo de Vida
  renderLifestyleSelectors(state.catalog, state.discretionary_choices);

  // 7. Gráfico de Gastos
  renderExpensesChart(state);
}

// -----------------------------------------------------------------------------
// Renderizado del Calendario
// -----------------------------------------------------------------------------
function renderCalendar(state) {
  const container = document.getElementById("calendar-grid");
  container.innerHTML = "";

  for (let day = 1; day <= state.days_per_month; day++) {
    const cell = document.createElement("div");
    cell.className = "cal-day-cell";

    const isCurrent = (day === state.current_day);
    const attended = state.attendance_calendar[day.toString()];

    let statusText = "Pendiente";
    if (attended === true) {
      cell.classList.add("day-worked");
      statusText = "Trabajado";
    } else if (attended === false) {
      cell.classList.add("day-absent");
      statusText = "Falta";
    } else if (isCurrent) {
      cell.classList.add("day-current");
      statusText = "Hoy";
    } else if (day > state.current_day) {
      cell.classList.add("day-future");
      statusText = "Futuro";
    }

    cell.innerHTML = `
      <span class="cal-day-num">Día ${day}</span>
      <span class="cal-status-tag">${statusText}</span>
    `;
    container.appendChild(cell);
  }
}

// -----------------------------------------------------------------------------
// Renderizado de Gastos Fijos y Selectores
// -----------------------------------------------------------------------------
function renderFixedCosts(fixedCosts, totalFixed) {
  const list = document.getElementById("fixed-costs-list");
  list.innerHTML = "";
  document.getElementById("total-fixed-badge").textContent = `Total: ${formatCurrency(totalFixed)}`;

  for (const [name, cost] of Object.entries(fixedCosts)) {
    const li = document.createElement("li");
    li.className = "cost-row";
    li.innerHTML = `
      <span>${name}</span>
      <strong class="text-danger">-${formatCurrency(cost)}</strong>
    `;
    list.appendChild(li);
  }
}

function renderLifestyleSelectors(catalog, selectedChoices) {
  const container = document.getElementById("lifestyle-selectors");
  container.innerHTML = "";

  const categoryNames = {
    transporte: "🚗 Transporte Diario",
    comida_ocio: "🍔 Comida & Delivery",
    ropa_shopping: "👕 Ropa & Shopping",
    cuidado_personal: "💈 Cuidado Personal",
    entretenimiento: "🎭 Entretenimiento & Salidas"
  };

  for (const [categoryKey, options] of Object.entries(catalog)) {
    const item = document.createElement("div");
    item.className = "lifestyle-item";

    const currentSelectedId = selectedChoices[categoryKey]?.id;

    let selectHtml = `<select class="lifestyle-select" onchange="changeLifestyleChoice('${categoryKey}', this.value)">`;
    options.forEach(opt => {
      const isSelected = (opt.id === currentSelectedId) ? "selected" : "";
      selectHtml += `
        <option value="${opt.id}" ${isSelected}>
          ${opt.name} -> ${formatCurrency(opt.cost)} (+${opt.utility.toFixed(0)} utilidad)
        </option>
      `;
    });
    selectHtml += `</select>`;

    item.innerHTML = `
      <div class="lifestyle-header">
        <span>${categoryNames[categoryKey] || categoryKey}</span>
        <span class="text-muted" style="font-size:0.75rem;">${selectedChoices[categoryKey]?.description || ""}</span>
      </div>
      ${selectHtml}
    `;
    container.appendChild(item);
  }
}

async function changeLifestyleChoice(category, optionId) {
  try {
    await fetch("/api/decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category, option_id: optionId })
    });
    fetchState();
  } catch (err) {
    console.error("Error al cambiar elección:", err);
  }
}

// -----------------------------------------------------------------------------
// Gráfico de Gastos (Chart.js)
// -----------------------------------------------------------------------------
function renderExpensesChart(state) {
  const ctx = document.getElementById("expensesChart").getContext("2d");

  // Sumar costos de gastos fijos
  const totalFixed = state.total_fixed_costs;

  // Sumar costos de opciones discrecionales elegidas
  let totalDiscretionary = 0;
  for (const choice of Object.values(state.discretionary_choices)) {
    totalDiscretionary += choice.cost;
  }

  // Sumar eventualidades imprevistas
  let totalUnforeseen = 0;
  for (const ev of state.current_month_unforeseen) {
    totalUnforeseen += ev.cost;
  }

  const dataValues = [totalFixed, totalDiscretionary, totalUnforeseen];
  const labels = ["Gastos Fijos", "Ocio / Estilo de Vida", "Imprevistos"];

  if (expensesChartInstance) {
    expensesChartInstance.data.datasets[0].data = dataValues;
    expensesChartInstance.update();
  } else {
    expensesChartInstance = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: dataValues,
          backgroundColor: ["#ef4444", "#38bdf8", "#f59e0b"],
          borderWidth: 1,
          borderColor: "#121826"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: { color: "#94a3b8", font: { size: 11 } }
          }
        }
      }
    });
  }
}

// -----------------------------------------------------------------------------
// Mini-Juego Diario (Jornada Laboral)
// -----------------------------------------------------------------------------
async function openWorkQuizModal() {
  const dialog = document.getElementById("modal-work-quiz");
  const topicBadge = document.getElementById("quiz-topic");
  const questionEl = document.getElementById("quiz-question");
  const optionsContainer = document.getElementById("quiz-options-container");
  const feedbackEl = document.getElementById("quiz-feedback");
  const btnClose = document.getElementById("btn-close-quiz");

  feedbackEl.className = "quiz-feedback hidden";
  feedbackEl.innerHTML = "";
  btnClose.style.display = "none";
  optionsContainer.innerHTML = "Cargando pregunta...";

  dialog.showModal();

  try {
    const res = await fetch("/api/work_quiz");
    const quiz = await res.json();

    topicBadge.textContent = quiz.topic;
    questionEl.textContent = quiz.question;
    optionsContainer.innerHTML = "";

    quiz.options.forEach((optText, index) => {
      const btn = document.createElement("button");
      btn.className = "option-btn";
      btn.textContent = `${index + 1}. ${optText}`;
      btn.onclick = () => submitWorkQuizAnswer(index);
      optionsContainer.appendChild(btn);
    });
  } catch (err) {
    optionsContainer.textContent = "Error al cargar la pregunta diaria.";
  }
}

async function submitWorkQuizAnswer(optionIndex) {
  const feedbackEl = document.getElementById("quiz-feedback");
  const btnClose = document.getElementById("btn-close-quiz");
  const optionsContainer = document.getElementById("quiz-options-container");

  // Deshabilitar botones de opciones
  Array.from(optionsContainer.children).forEach(b => b.disabled = true);

  try {
    const res = await fetch("/api/work_quiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ option_index: optionIndex })
    });
    const result = await res.json();

    feedbackEl.classList.remove("hidden");
    if (result.is_correct) {
      feedbackEl.className = "quiz-feedback correct";
      feedbackEl.innerHTML = `
        <strong>🎉 ¡Excelente respuesta!</strong>
        <p>${result.explanation}</p>
        <p>💼 <em>Día computado como TRABAJADO (+${formatCurrency(result.daily_salary_earned)} al salario a liquidar).</em></p>
      `;
    } else {
      feedbackEl.className = "quiz-feedback incorrect";
      feedbackEl.innerHTML = `
        <strong>⚠️ Respuesta inexacta.</strong>
        <p>${result.explanation}</p>
        <p>💼 <em>Se computa el día como TRABAJADO por haber completado la jornada laboral (+${formatCurrency(result.daily_salary_earned)}).</em></p>
      `;
    }

    if (result.unforeseen_message) {
      feedbackEl.innerHTML += `<div style="margin-top:0.5rem; color:#f59e0b;">${result.unforeseen_message}</div>`;
    }

    btnClose.style.display = "inline-block";
  } catch (err) {
    console.error("Error al enviar respuesta:", err);
  }
}

// -----------------------------------------------------------------------------
// Saltear Día (Ausencia) y Avanzar Calendario
// -----------------------------------------------------------------------------
async function skipDay() {
  if (!confirm("¿Seguro que no vas a ir a trabajar hoy? Se computará una AUSENCIA y se descontará el día proporcionalmente a fin de mes.")) {
    return;
  }
  try {
    const res = await fetch("/api/skip_day", { method: "POST" });
    const result = await res.json();
    alert(result.message + (result.unforeseen_message ? "\n\n" + result.unforeseen_message : ""));
    fetchState();
  } catch (err) {
    console.error("Error al saltear día:", err);
  }
}

async function advanceDay() {
  try {
    const res = await fetch("/api/advance_day", { method: "POST" });
    const result = await res.json();
    fetchState();
  } catch (err) {
    console.error("Error al avanzar día:", err);
  }
}

// -----------------------------------------------------------------------------
// Horas Extras Opcionales (Fórmulas Financieras)
// -----------------------------------------------------------------------------
async function requestOvertime() {
  const card = document.getElementById("overtime-card");
  const empty = document.getElementById("overtime-empty");
  const title = document.getElementById("overtime-title");
  const statement = document.getElementById("overtime-statement");
  const hint = document.getElementById("overtime-hint");
  const optionsCont = document.getElementById("overtime-options");

  try {
    const res = await fetch("/api/overtime_challenge");
    const data = await res.json();

    empty.classList.add("hidden");
    card.classList.remove("hidden");

    title.textContent = `⏱️ ${data.title} (Recompensa: +${formatCurrency(data.reward_amount)})`;
    statement.textContent = data.statement;
    hint.textContent = data.hint;
    optionsCont.innerHTML = "";

    data.options.forEach((optText, index) => {
      const btn = document.createElement("button");
      btn.className = "option-btn";
      btn.textContent = optText;
      btn.onclick = () => submitOvertimeAnswer(index);
      optionsCont.appendChild(btn);
    });
  } catch (err) {
    console.error("Error al pedir horas extras:", err);
  }
}

async function submitOvertimeAnswer(optionIndex) {
  try {
    const res = await fetch("/api/overtime_challenge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ option_index: optionIndex })
    });
    const result = await res.json();

    alert(result.message);
    document.getElementById("overtime-card").classList.add("hidden");
    document.getElementById("overtime-empty").classList.remove("hidden");
    fetchState();
  } catch (err) {
    console.error("Error al validar horas extras:", err);
  }
}

// -----------------------------------------------------------------------------
// Liquidación de Fin de Mes (Día 30)
// -----------------------------------------------------------------------------
async function closeAndLiquidateMonth() {
  if (!confirm("¿Deseas cerrar el mes 30 y ejecutar la liquidación de salarios, gastos fijos, estilo de vida e intereses?")) {
    return;
  }
  try {
    const res = await fetch("/api/end_month", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      showEndMonthSummaryModal(data.summary);
    } else {
      alert("Error: " + data.error);
    }
  } catch (err) {
    console.error("Error al liquidar mes:", err);
  }
}

function showEndMonthSummaryModal(summary) {
  const dialog = document.getElementById("modal-end-month");
  document.getElementById("modal-month-label").textContent = `Liquidación Mes ${summary.month}`;
  const body = document.getElementById("end-month-summary-body");

  body.innerHTML = `
    <div class="glass-panel" style="padding:1rem;">
      <h4 class="text-success">💼 Ingresos Liquidados</h4>
      <p>• Días trabajados: <strong>${summary.worked_days} / 30</strong></p>
      <p>• Días no trabajados (Ausencias): <strong>${summary.unworked_days}</strong></p>
      <p>• Salario base percibido: <strong>${formatCurrency(summary.base_salary_earned)}</strong></p>
      <p>• Descuento por inasistencias: <strong class="text-danger">-${formatCurrency(summary.absence_deduction)}</strong></p>
      <p>• Horas extras acumuladas: <strong class="text-accent">+${formatCurrency(summary.overtime_earned)}</strong></p>
      <hr style="border:0; border-top:1px solid var(--border-subtle); margin:0.5rem 0;">
      <p>Total sueldo en mano: <strong class="text-success">${formatCurrency(summary.net_salary_liquidated)}</strong></p>
    </div>

    <div class="glass-panel" style="padding:1rem;">
      <h4 class="text-danger">💸 Gastos Totales Debitado</h4>
      <p>• Gastos fijos obligatorios: <strong>${formatCurrency(summary.total_fixed_cost)}</strong></p>
      <p>• Gastos discrecionales (Ocio/Estilo de vida): <strong>${formatCurrency(summary.total_discretionary_cost)}</strong></p>
      <p>• Imprevistos emergentes: <strong>${formatCurrency(summary.total_unforeseen_cost)}</strong></p>
      <p>• Intereses por descubierto previo: <strong class="text-danger">-${formatCurrency(summary.interest_applied)}</strong></p>
      <hr style="border:0; border-top:1px solid var(--border-subtle); margin:0.5rem 0;">
      <p>• Efectivo al cierre: <strong class="text-success">${formatCurrency(summary.ending_cash)}</strong></p>
      <p>• Deuda bancaria resultante: <strong class="text-danger">${formatCurrency(summary.ending_debt)}</strong></p>
      <p>• Próximo IPC estimado: <strong class="text-warning">${summary.next_ipc.toFixed(4)}x</strong></p>
    </div>
  `;

  dialog.showModal();
}

async function resetGame() {
  if (!confirm("¿Deseas reiniciar la partida al Mes 1, Día 1?")) return;
  try {
    await fetch("/api/reset", { method: "POST" });
    fetchState();
  } catch (err) {
    console.error("Error al reiniciar:", err);
  }
}
