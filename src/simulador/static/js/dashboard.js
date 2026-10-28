/**
 * Simulador de Supervivencia Economica - Controlador UI/UX Gamificado
 * Layout en 2 Niveles, Modales Integrados sin alerts nativos, Flujo Diario Completo
 * (tanto en asistencia como en ausencia), Variabilidad de Menu Diario y Horas Extras por Participacion.
 * PROHIBICION TOTAL DE CORCHETES Y EMOJIS.
 */

let expensesChartInstance = null;
let currentGameState = null;

// Formateador de moneda argentina ($ 1.200.000,00)
function formatCurrency(val) {
  if (val === null || val === undefined) return "$0,00";
  const num = typeof val === "number" ? val : parseFloat(val);
  return "$" + num.toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Inicializacion al cargar el DOM
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  fetchState();
});

function initEventListeners() {
  document.getElementById("btn-restart-game").addEventListener("click", () => {
    showConfirmDialog(
      "Reiniciar Partida",
      "¿Deseas reiniciar la simulacion desde el Mes 1, Dia 1? Se borrara el progreso actual.",
      resetGame,
      "Confirmar",
      "Cancelar"
    );
  });

  document.getElementById("btn-action-work").addEventListener("click", startDailyWorkFlow);
  document.getElementById("btn-action-skip").addEventListener("click", confirmSkipDay);
  document.getElementById("btn-action-overtime").addEventListener("click", openOvertimeModal);
  document.getElementById("btn-action-advance").addEventListener("click", advanceDay);
  document.getElementById("btn-end-month-trigger").addEventListener("click", confirmEndMonth);

  // Boton continuar en modal de notificacion
  document.getElementById("btn-close-notif").addEventListener("click", () => {
    document.getElementById("modal-notification").close();
  });

  // Botones en modal de horas extras
  document.getElementById("btn-close-overtime-modal").addEventListener("click", () => {
    document.getElementById("modal-overtime").close();
    fetchState();
  });

  // Botones en crisis pop-up
  document.getElementById("btn-crisis-opt-cash").addEventListener("click", () => resolveCrisis("cash"));
  document.getElementById("btn-crisis-opt-finance").addEventListener("click", () => resolveCrisis("finance"));

  // Boton en resumen de fin de mes
  document.getElementById("btn-advance-month-confirm").addEventListener("click", () => {
    document.getElementById("modal-month-summary").close();
    fetchState();
  });

  // Pestanas y controles de Administrador / Modo Demo
  const tabStandard = document.getElementById("tab-mode-standard");
  if (tabStandard) {
    tabStandard.addEventListener("click", () => switchMode("standard"));
  }

  const tabDemo = document.getElementById("tab-mode-demo");
  if (tabDemo) {
    tabDemo.addEventListener("click", () => {
      const dialog = document.getElementById("modal-admin-demo");
      if (dialog) dialog.showModal();
    });
  }

  const btnAdminCancel = document.getElementById("btn-admin-cancel");
  if (btnAdminCancel) {
    btnAdminCancel.addEventListener("click", () => {
      const dialog = document.getElementById("modal-admin-demo");
      if (dialog) dialog.close();
    });
  }

  const btnAdminLoadDemo = document.getElementById("btn-admin-load-demo");
  if (btnAdminLoadDemo) {
    btnAdminLoadDemo.addEventListener("click", () => {
      const dialog = document.getElementById("modal-admin-demo");
      if (dialog) dialog.close();
      switchMode("demo", true);
    });
  }

  const btnReloadDemo = document.getElementById("btn-reload-demo");
  if (btnReloadDemo) {
    btnReloadDemo.addEventListener("click", () => switchMode("demo", true));
  }

  const btnReturnStandard = document.getElementById("btn-return-standard");
  if (btnReturnStandard) {
    btnReturnStandard.addEventListener("click", () => switchMode("standard"));
  }

  // Boton reiniciar desde el modal final consolidado
  const btnFinalRestart = document.getElementById("btn-final-restart");
  if (btnFinalRestart) {
    btnFinalRestart.addEventListener("click", () => {
      const dialog = document.getElementById("modal-final-summary");
      if (dialog) dialog.close();
      resetGame();
    });
  }
}

// -----------------------------------------------------------------------------
// SISTEMA DE DIALOGOS INTEGRADOS (SIN ALERTS / CONFIRMS NATIVOS)
// -----------------------------------------------------------------------------
function showNotificationDialog(title, message, badgeText = "Informacion") {
  const dialog = document.getElementById("modal-notification");
  document.getElementById("notif-title").textContent = title;
  document.getElementById("notif-message").textContent = message;
  document.getElementById("notif-badge").textContent = badgeText;
  dialog.showModal();
}

function showConfirmDialog(title, message, onConfirm, confirmText = "Confirmar", cancelText = "Cancelar") {
  const dialog = document.getElementById("modal-confirm");
  document.getElementById("confirm-title").textContent = title;
  document.getElementById("confirm-message").textContent = message;

  const btnCancel = document.getElementById("btn-confirm-cancel");
  const btnAccept = document.getElementById("btn-confirm-accept");

  btnCancel.textContent = cancelText;
  btnAccept.textContent = confirmText;

  // Clones para remover listeners previos
  const newBtnCancel = btnCancel.cloneNode(true);
  const newBtnAccept = btnAccept.cloneNode(true);
  btnCancel.parentNode.replaceChild(newBtnCancel, btnCancel);
  btnAccept.parentNode.replaceChild(newBtnAccept, btnAccept);

  newBtnCancel.addEventListener("click", () => dialog.close());
  newBtnAccept.addEventListener("click", () => {
    dialog.close();
    if (typeof onConfirm === "function") {
      onConfirm();
    }
  });

  dialog.showModal();
}

// -----------------------------------------------------------------------------
// CONSUMO DEL ESTADO DEL JUEGO
// -----------------------------------------------------------------------------
async function fetchState() {
  try {
    const res = await fetch("/api/state");
    const data = await res.json();
    currentGameState = data;
    transitStrikeOccurredThisMonth = Boolean(data.transit_strike_occurred);
    renderDashboard(data);
  } catch (err) {
    console.error("Error al obtener estado:", err);
  }
}

function renderDashboard(state) {
  // 1. HUD Superior
  renderTopHUD(state);

  // 2. NIVEL SUPERIOR: Calendario Mensual de 30 Dias con Insignia "Horas extras"
  renderMonthlyCalendar(state);

  // 3. NIVEL SUPERIOR: Panel de Acciones Principales
  renderMainActionPanel(state);

  // 4. NIVEL INFERIOR: Panel Analitico Secundario
  renderAnalyticsPanel(state);

  // 5. Comprobacion de Crisis Activa
  checkActiveCrisis(state);
}

// -----------------------------------------------------------------------------
// 1. HUD SUPERIOR CONDENSADO
// -----------------------------------------------------------------------------
function renderTopHUD(state) {
  const cashValEl = document.getElementById("hud-cash-val");
  const cashBarEl = document.getElementById("hud-cash-bar");
  const debtTextEl = document.getElementById("hud-debt-text");
  const ratesTextEl = document.getElementById("hud-rates-text");

  if (state.debt > 0) {
    cashValEl.textContent = `-${formatCurrency(state.debt)}`;
    cashValEl.className = "gauge-num text-rose";
    cashBarEl.className = "progress-fill fill-mint in-debt";
    cashBarEl.style.width = "100%";
    debtTextEl.textContent = `Descubierto: ${formatCurrency(state.debt)}`;
    debtTextEl.className = "text-rose";
  } else {
    cashValEl.textContent = formatCurrency(state.cash);
    cashValEl.className = "gauge-num text-mint";
    cashBarEl.className = "progress-fill fill-mint";
    const cashPct = Math.min(Math.max((state.cash / state.base_salary) * 100, 5), 100);
    cashBarEl.style.width = `${cashPct.toFixed(1)}%`;
    debtTextEl.textContent = "Descubierto: $0,00";
    debtTextEl.className = "text-muted";
  }
  ratesTextEl.textContent = `TNA ${(state.tna * 100).toFixed(1)}% | TEM ${(state.tem * 100).toFixed(2)}%`;

  // Utilidad / Bienestar
  const utilValEl = document.getElementById("hud-utility-val");
  const utilBarEl = document.getElementById("hud-utility-bar");
  const utilStatusEl = document.getElementById("hud-utility-status");

  utilValEl.textContent = `${state.cumulative_utility.toFixed(1)} PTS`;
  const utilPct = Math.min(Math.max((state.cumulative_utility / 200) * 100, 5), 100);
  utilBarEl.style.width = `${utilPct.toFixed(1)}%`;

  if (state.cumulative_utility < 30) {
    utilStatusEl.textContent = "Privacion Severa";
    utilStatusEl.className = "text-rose";
  } else if (state.cumulative_utility < 90) {
    utilStatusEl.textContent = "Equilibrio Moderado";
    utilStatusEl.className = "text-honey";
  } else {
    utilStatusEl.textContent = "Confort Alto";
    utilStatusEl.className = "text-purple";
  }

  // Progreso Dias
  document.getElementById("hud-day-val").textContent = `Dia ${state.current_day} de ${state.days_per_month}`;
  const dayPct = (state.current_day / state.days_per_month) * 100;
  document.getElementById("hud-day-bar").style.width = `${dayPct.toFixed(1)}%`;

  const currentMonthName = state.month_name || state.current_month_name || "Marzo";
  document.getElementById("hud-month-text").textContent = `${currentMonthName} (Mes ${state.current_month} de ${state.total_months})`;
  const inflPct = ((state.current_ipc - 1) * 100).toFixed(2);
  document.getElementById("hud-ipc-text").textContent = `IPC: ${state.current_ipc.toFixed(4)}x (+${inflPct}%)`;

  // Control visual del Modo Demo / Administrador
  const isDemo = Boolean(state.is_demo_mode);
  const tabStandard = document.getElementById("tab-mode-standard");
  const tabDemo = document.getElementById("tab-mode-demo");
  const demoBar = document.getElementById("demo-mode-indicator-bar");

  if (tabStandard && tabDemo) {
    if (isDemo) {
      tabStandard.classList.remove("active");
      tabDemo.classList.add("active");
    } else {
      tabStandard.classList.add("active");
      tabDemo.classList.remove("active");
    }
  }

  if (demoBar) {
    if (isDemo) {
      demoBar.classList.remove("hidden");
    } else {
      demoBar.classList.add("hidden");
    }
  }
}

// -----------------------------------------------------------------------------
// 2. NIVEL SUPERIOR: CALENDARIO MENSUAL DE 30 DIAS CON INSIGNIA "HORAS EXTRAS"
// -----------------------------------------------------------------------------
function renderMonthlyCalendar(state) {
  const headingEl = document.getElementById("calendar-heading");
  const monthName = state.month_name || state.current_month_name || "Marzo";
  if (headingEl) {
    headingEl.textContent = `Calendario Mensual - ${monthName} (${state.days_per_month} Dias)`;
  }

  const container = document.getElementById("calendar-cells-grid");
  container.innerHTML = "";

  const overtimeCalendar = state.overtime_calendar || {};

  // Calcular dia de la semana para el 1er dia del mes
  // Mes 1 = Marzo 2026 (index 2 en JS Date). Marzo 1, 2026 es Domingo.
  const year = 2026;
  const jsMonth = (state.current_month - 1) + 2;
  const firstDayWeekday = new Date(year, jsMonth, 1).getDay(); // 0 = Domingo
  const offset = (firstDayWeekday + 6) % 7; // Lunes=0, ..., Domingo=6

  // Casilleros vacios para alinear el primer dia del mes con su dia de la semana
  for (let i = 0; i < offset; i++) {
    const emptyTile = document.createElement("div");
    emptyTile.className = "cal-tile is-empty";
    container.appendChild(emptyTile);
  }

  const dayNames = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];

  for (let day = 1; day <= state.days_per_month; day++) {
    const tile = document.createElement("div");
    tile.className = "cal-tile";

    const isCurrent = (day === state.current_day);
    const attended = state.attendance_calendar[day.toString()];
    const hasOvertime = Boolean(overtimeCalendar[day.toString()]);
    const weekdayName = dayNames[(offset + day - 1) % 7];

    let tagText = "Pendiente";

    if (attended === true) {
      tile.classList.add("is-worked");
      tagText = "Trabajado";
    } else if (attended === false) {
      tile.classList.add("is-absent");
      tagText = "Ausente";
    } else if (isCurrent) {
      tile.classList.add("is-current");
      tagText = "Hoy";
    } else if (day > state.current_day) {
      tile.classList.add("is-future");
      tagText = "Futuro";
    }

    // Distintivo de Horas extras (sin corchetes)
    let overtimeBadgeHtml = "";
    if (hasOvertime) {
      tile.classList.add("has-overtime");
      overtimeBadgeHtml = `<span class="badge-overtime">Horas extras</span>`;
    }

    tile.innerHTML = `
      <span class="cal-tile-weekday">${weekdayName}</span>
      <span class="cal-tile-num">Dia ${day}</span>
      <span class="cal-tile-tag">${tagText}</span>
      ${overtimeBadgeHtml}
    `;

    container.appendChild(tile);
  }
}

// -----------------------------------------------------------------------------
// 3. NIVEL SUPERIOR: PANEL DE ACCIONES PRINCIPALES
// -----------------------------------------------------------------------------
function renderMainActionPanel(state) {
  const badgeLabel = document.getElementById("day-badge-label");
  const statusPill = document.getElementById("day-status-pill");
  const accSalary = document.getElementById("card-acc-salary");
  const accOvertime = document.getElementById("card-acc-overtime");

  const btnWork = document.getElementById("btn-action-work");
  const btnSkip = document.getElementById("btn-action-skip");
  const btnOvertime = document.getElementById("btn-action-overtime");
  const btnAdvance = document.getElementById("btn-action-advance");
  const hintText = document.getElementById("action-hint-text");

  badgeLabel.textContent = `Dia ${state.current_day} en Curso`;
  accSalary.textContent = formatCurrency(state.projected_salary);
  accOvertime.textContent = `+${formatCurrency(state.overtime_bonus_accumulated)}`;

  const isPending = (state.day_status === "pending");

  if (isPending) {
    statusPill.textContent = "Pendiente";
    statusPill.className = "status-indicator status-pending";

    btnWork.disabled = false;
    btnSkip.disabled = false;
    btnOvertime.disabled = true; // Bloqueado hasta fichar asistencia
    btnAdvance.disabled = true;

    hintText.textContent = "Selecciona IR A TRABAJAR para iniciar tu jornada o NO IR A TRABAJAR si decides ausentarte hoy.";
  } else if (state.day_status === "worked") {
    statusPill.textContent = "Trabajado";
    statusPill.className = "status-indicator status-worked";

    btnWork.disabled = true;
    btnSkip.disabled = true;

    // Horas extras habilitadas si no se completaron ya hoy
    const alreadyDoneOvertime = Boolean(state.overtime_calendar && state.overtime_calendar[state.current_day.toString()]);
    btnOvertime.disabled = alreadyDoneOvertime;
    if (alreadyDoneOvertime) {
      btnOvertime.textContent = "HORAS EXTRAS REALIZADAS";
    } else {
      btnOvertime.textContent = "HORAS EXTRAS DISPONIBLES";
    }

    btnAdvance.disabled = (state.current_day === state.days_per_month);
    hintText.textContent = alreadyDoneOvertime
      ? "Has completado la jornada y tus horas extras de hoy. Presiona Avanzar al Siguiente Dia para continuar."
      : "Asistencia confirmada. Puedes presionar HORAS EXTRAS para participar en el desafio financiero de la jornada.";
  } else {
    // Ausente
    statusPill.textContent = "Ausencia";
    statusPill.className = "status-indicator status-absent";

    btnWork.disabled = true;
    btnSkip.disabled = true;
    btnOvertime.disabled = true;
    btnOvertime.textContent = "HORAS EXTRAS BLOQUEADAS";

    btnAdvance.disabled = (state.current_day === state.days_per_month);
    hintText.textContent = "Dia registrado como ausencia. Las horas extras permanecen bloqueadas. Presiona Avanzar al Siguiente Dia para continuar.";
  }

  // Control de Fin de Mes (Dia 30)
  const btnEndMonth = document.getElementById("btn-end-month-trigger");
  const endMonthHelper = document.getElementById("end-month-helper");

  if (state.current_day === state.days_per_month && !isPending) {
    btnEndMonth.disabled = false;
    btnAdvance.disabled = true;
    endMonthHelper.textContent = "Has completado el dia 30. Presiona el boton para ejecutar la liquidacion contable mensual.";
  } else {
    btnEndMonth.disabled = true;
    endMonthHelper.textContent = `Dia actual: ${state.current_day} de 30. Completa el ciclo mensual para liquidar haberes.`;
  }
}

// -----------------------------------------------------------------------------
// 4. NIVEL INFERIOR: PANEL ANALITICO SECUNDARIO
// -----------------------------------------------------------------------------
function renderAnalyticsPanel(state) {
  document.getElementById("metric-base-salary").textContent = formatCurrency(state.base_salary);
  document.getElementById("metric-worked-days").textContent = `${state.worked_days} de ${state.days_per_month} dias`;
  document.getElementById("metric-projected-salary").textContent = formatCurrency(state.projected_salary);
  document.getElementById("metric-absence-deduction").textContent = `-${formatCurrency(state.projected_absence_deduction)}`;
  document.getElementById("metric-overtime-bonus").textContent = `+${formatCurrency(state.overtime_bonus_accumulated)}`;

  const fixedList = document.getElementById("fixed-costs-ul");
  fixedList.innerHTML = "";
  document.getElementById("badge-total-fixed").textContent = `Total: ${formatCurrency(state.total_fixed_costs)}`;

  for (const [name, cost] of Object.entries(state.fixed_costs)) {
    const li = document.createElement("li");
    li.className = "fixed-item-row";
    li.innerHTML = `
      <span>${name}</span>
      <strong class="text-rose">-${formatCurrency(cost)}</strong>
    `;
    fixedList.appendChild(li);
  }

  renderExpensesChart(state);
}

function renderExpensesChart(state) {
  const ctx = document.getElementById("expensesChart").getContext("2d");

  const totalFixed = state.total_fixed_costs;
  let totalDiscretionary = 0;
  for (const choice of Object.values(state.discretionary_choices)) {
    totalDiscretionary += choice.cost;
  }
  let totalUnforeseen = 0;
  for (const ev of state.current_month_unforeseen) {
    totalUnforeseen += ev.cost;
  }

  const dataValues = [totalFixed, totalDiscretionary, totalUnforeseen];
  const labels = ["Gastos Fijos", "Estilo de Vida", "Imprevistos"];

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
          backgroundColor: ["#f43f5e", "#0ea5e9", "#f59e0b"],
          borderWidth: 2,
          borderColor: "#131c31"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: {
              color: "#94a3b8",
              font: { family: "system-ui", size: 11 }
            }
          }
        }
      }
    });
  }
}

// -----------------------------------------------------------------------------
// 5. BANCO DINAMICO DE COMIDAS Y OPCIONES COTIDIANAS (VARIABILIDAD POR DIA)
// -----------------------------------------------------------------------------

// Control de Paro de Transporte (Maximo 1 vez por mes)
let transitStrikeOccurredThisMonth = false;

const BREAKFAST_POOLS = [
  {
    casa: { name: "Cafe de filtro casero con tostadas y queso untable", desc: "Preparacion rapida en casa y maximo ahorro.", cost: 500, utility: 6 },
    paso: { name: "Flat white de especialidad con medialunas de manteca", desc: "Cafeteria moderna al paso en Recoleta.", cost: 4600, utility: 22 }
  },
  {
    casa: { name: "Mate cocido con galletitas de agua en casa", desc: "Desayuno clasico economico y rendidor.", cost: 400, utility: 5 },
    paso: { name: "Cafe latte doble con avocado toast", desc: "Desayuno gourmet completo en cafeteria de diseno.", cost: 5200, utility: 25 }
  },
  {
    casa: { name: "Te negro casero con frutas de estacion", desc: "Opcion ligera, nutritiva y economica.", cost: 600, utility: 8 },
    paso: { name: "Capuccino italiano con muffin de arandanos", desc: "Dulce tentacion matutina para arrancar el dia.", cost: 4800, utility: 20 }
  },
  {
    casa: { name: "Cafe instantaneo con leche y pan tostado", desc: "Desayuno veloz antes de arrancar.", cost: 450, utility: 5 },
    paso: { name: "Cold brew con chipa recien horneado", desc: "Cafe frio de especialidad con chipa caliente.", cost: 4900, utility: 24 }
  },
  {
    casa: { name: "Yogur con avena y semillas preparado en casa", desc: "Opcion fit y balanceada hecha en casa.", cost: 700, utility: 10 },
    paso: { name: "Espresso doble con tostado de jamon y queso", desc: "Clasico cafe y tostado en bar tradicional.", cost: 5500, utility: 26 }
  }
];

const LUNCH_POOLS = [
  {
    vianda: { name: "Vianda casera: Milanesa con pure mixto", desc: "Plato casero rendidor traido del hogar.", cost: 1200, utility: 18 },
    ejecutivo: { name: "Menu ejecutivo: Bife de chorizo con guarnicion", desc: "Almuerzo completo de restaurante con cafe y postre.", cost: 14000, utility: 48 },
    rapido: { name: "Sandwich de pollo al paso con gaseosa", desc: "Opcion agil de rotiseria.", cost: 6500, utility: 26 }
  },
  {
    vianda: { name: "Vianda casera: Tarta de espinaca y calabaza", desc: "Comida liviana y saludable casera.", cost: 1100, utility: 15 },
    ejecutivo: { name: "Menu ejecutivo: Pasta fresca casera con salsa bolognesa", desc: "Trattoria de barrio con panera y bebida.", cost: 12500, utility: 42 },
    rapido: { name: "Empanadas al paso (2 unidades) con bebida", desc: "Pausa rapida al paso en panaderia.", cost: 5800, utility: 24 }
  },
  {
    vianda: { name: "Vianda casera: Arroz salteado con vegetales y huevo", desc: "Cocina economica y balanceada.", cost: 1000, utility: 14 },
    ejecutivo: { name: "Restaurante: Salmon grillado con ensalada caesar", desc: "Plato gourmet saludable en salon ejecutivo.", cost: 16500, utility: 52 },
    rapido: { name: "Wrap integral de atun y jugo exprimido", desc: "Opcion fresca al paso en deli bar.", cost: 7200, utility: 28 }
  },
  {
    vianda: { name: "Vianda casera: Guiso de lentejas nutritivo", desc: "Plato de cuchara sustancioso y reconfortante.", cost: 1300, utility: 17 },
    ejecutivo: { name: "Menu ejecutivo: Pechuga a la suiza con papas noisette", desc: "Almuerzo abundante con bebida y postre.", cost: 13500, utility: 45 },
    rapido: { name: "Porcion de tarta y agua mineral en buffet", desc: "Almuerzo express en autoservicio.", cost: 6000, utility: 22 }
  },
  {
    vianda: { name: "Vianda casera: Ensalada completa de pollo y vegetales", desc: "Preparacion fresca y ligera del hogar.", cost: 1250, utility: 16 },
    ejecutivo: { name: "Parrilla: Matambre tiernizado con papas fritas", desc: "Corte tradicional a la parrilla con postre.", cost: 15000, utility: 50 },
    rapido: { name: "Hamburguesa clasica de mostrador al paso", desc: "Comida al paso agil y rapida.", cost: 6800, utility: 27 }
  }
];

// Rebalanceo exigente: Cocinar en casa por la noche otorga 0 puntos de bienestar
const DINNER_POOLS = [
  {
    cocina: { name: "Cocinar en casa: Fideos con salsa fileto casera", optId: "food_cocina", cost: 1800, utility: 0 },
    delivery1: { name: "Delivery: Pizza grande de muzzarella tradicional", optId: "food_delivery_pizza", cost: 12000, utility: 42 },
    delivery2: { name: "Delivery: Hamburguesa doble smash con cheddar y papas", optId: "food_delivery_burger", cost: 15500, utility: 50 }
  },
  {
    cocina: { name: "Cocinar en casa: Omelette de queso con ensalada verde", optId: "food_cocina", cost: 1600, utility: 0 },
    delivery1: { name: "Delivery: Empanadas saltenas al horno (media docena)", optId: "food_delivery_pizza", cost: 11500, utility: 45 },
    delivery2: { name: "Delivery: Sushi combinado clasico (15 piezas)", optId: "food_delivery_burger", cost: 18000, utility: 55 }
  },
  {
    cocina: { name: "Cocinar en casa: Risotto de champinones casero", optId: "food_cocina", cost: 2200, utility: 0 },
    delivery1: { name: "Delivery: Tacos y quesadillas mexicanas", optId: "food_delivery_pizza", cost: 13000, utility: 46 },
    delivery2: { name: "Delivery: Milanesa napolitana XL para compartir", optId: "food_delivery_burger", cost: 16000, utility: 52 }
  },
  {
    cocina: { name: "Cocinar en casa: Sopa crema de calabaza y croutons", optId: "food_cocina", cost: 1400, utility: 0 },
    delivery1: { name: "Delivery: Comida china / Chop suey con arroz frito", optId: "food_delivery_pizza", cost: 11000, utility: 40 },
    delivery2: { name: "Delivery: Sandwich de bondiola braseada con barbacoa", optId: "food_delivery_burger", cost: 14500, utility: 48 }
  },
  {
    cocina: { name: "Cocinar en casa: Pechuga a la plancha con pure de papas", optId: "food_cocina", cost: 2400, utility: 0 },
    delivery1: { name: "Delivery: Pizza napolitana con jamon crudo y rucula", optId: "food_delivery_pizza", cost: 13500, utility: 48 },
    delivery2: { name: "Delivery: Helado artesanal de 1kg y picada nocturna", optId: "food_delivery_burger", cost: 17000, utility: 54 }
  }
];

// Situaciones de transito estructuradas (Paro maximo 1 vez por mes)
const TRANSIT_SITUATIONS = [
  {
    isStrike: true,
    isCongested: true,
    text: "Atencion: ¡Paro sorpresivo de colectivos en la ciudad! El subte viaja colapsado."
  },
  {
    isStrike: false,
    isCongested: true,
    text: "Embotellamiento severo y obras viales en avenidas principales de CABA complican la circulacion."
  },
  {
    isStrike: false,
    isCongested: true,
    text: "Lluvia intensa sobre Buenos Aires complica el transito y congestiona las lineas de transporte."
  },
  {
    isStrike: false,
    isCongested: false,
    text: "El trafico matutino se encuentra despejado hacia el centro de la ciudad."
  }
];

// Opciones adaptadas para dias NO laborables (permanencia y descanso en casa)
const ABSENT_MORNING_POOLS = [
  {
    casa: { name: "Desayuno casero relajado con cafe y tostadas", desc: "Despertar sin apuro en el departamento y mate/cafe tranquilo.", cost: 500, utility: 8 },
    brunch: { name: "Pedir medialunas y cafe de especialidad a domicilio", desc: "Desayuno brunch de cafeteria moderna en la cama.", cost: 4200, utility: 22 }
  },
  {
    casa: { name: "Te de hierbas con tostadas de pan integral casero", desc: "Desayuno liviano y sereno en la tranquilidad del hogar.", cost: 450, utility: 7 },
    brunch: { name: "Pancakes con frutas y jugo de naranja por delivery", desc: "Gusto dulce matutino a domicilio para empezar el dia.", cost: 4600, utility: 24 }
  }
];

const ABSENT_ACTIVITY_POOLS = [
  {
    hogar: { name: "Maraton de series, peliculas y lectura en casa", desc: "Descanso absoluto en el living sin traslados ni apuros laborales.", cost: 0, utility: 16 },
    paseo: { name: "Paseo recreativo por plazas de Recoleta y cafe", desc: "Caminata al aire libre por el barrio y merienda tranquila.", cost: 3800, utility: 26 }
  },
  {
    hogar: { name: "Tarde de musica, videojuegos y siesta reparadora", desc: "Desconexion mental completa en el departamento.", cost: 0, utility: 15 },
    paseo: { name: "Visita barrial a libreria y cafeteria tradicional", desc: "Paseo cultural de relax y compra de cafe al paso.", cost: 4200, utility: 28 }
  }
];

const ABSENT_LUNCH_POOLS = [
  {
    cocina: { name: "Cocinar almuerzo casero con lo que hay en la alacena", desc: "Tortilla de papas o pastas caseras sin apuro en la cocina.", cost: 1200, utility: 12 },
    delivery: { name: "Pedir delivery de empanadas al horno o sandwich gourmet", desc: "Comida caliente, sabrosa y lista a domicilio.", cost: 7200, utility: 28 }
  },
  {
    cocina: { name: "Ensalada fresca completa con vegetales del hogar", desc: "Almuerzo liviano, saludable y economico hecho en casa.", cost: 1400, utility: 14 },
    delivery: { name: "Delivery de tacos mexicanos o sushi express", desc: "Almuerzo especial para disfrutar en el sillon.", cost: 8500, utility: 32 }
  }
];

const ABSENT_DINNER_POOLS = [
  {
    cocina: { name: "Cocinar cena casera ligera y descansar temprano", desc: "Plato sencillo casero (tarea cotidiana, 0 U de bienestar extra).", cost: 1600, utility: 0 },
    delivery: { name: "Delivery nocturno de pizza grande con amigos/pareja", desc: "Cierre de dia libre con comida reconfortante a domicilio.", cost: 14000, utility: 45 }
  },
  {
    cocina: { name: "Sopa crema casera y tostadas con queso", desc: "Cena liviana en el hogar (tarea cotidiana, 0 U de bienestar extra).", cost: 1500, utility: 0 },
    delivery: { name: "Delivery de hamburguesa con papas cheddar", desc: "Noche de peliculas con hamburguesa gourmet a domicilio.", cost: 15000, utility: 48 }
  }
];

// -----------------------------------------------------------------------------
// 6. FLUJO SECUENCIAL DE DECISIONES Y EVENTOS DIARIOS (POP-UPS MODALES)
// -----------------------------------------------------------------------------

let dailyFlowState = {
  isAbsentFlow: false,
  currentStep: 1,
  totalSteps: 5,
  dailyEarned: 0,
  dailyUtilityGained: 0,
  currentDay: 1
};

// Iniciar flujo con asistencia a trabajar
async function startDailyWorkFlow() {
  dailyFlowState = {
    isAbsentFlow: false,
    currentStep: 1,
    totalSteps: 5,
    dailyEarned: 0,
    dailyUtilityGained: 0,
    currentDay: currentGameState?.current_day || 1
  };

  const dialog = document.getElementById("modal-daily-flow");
  dialog.showModal();
  renderFlowStep1Trivia();
}

// Iniciar flujo cuando decide no ir a trabajar (Ausencia)
function startDailyAbsenceFlow(absenceMessage) {
  dailyFlowState = {
    isAbsentFlow: true,
    currentStep: 1,
    totalSteps: 5,
    dailyEarned: 0,
    dailyUtilityGained: 0,
    currentDay: currentGameState?.current_day || 1
  };

  const dialog = document.getElementById("modal-daily-flow");
  dialog.showModal();
  renderFlowStep1AbsenceNotice(absenceMessage);
}

// Paso 1: Trivia Laboral (cuando asiste)
async function renderFlowStep1Trivia() {
  updateFlowHeader("Etapa 1 de 5: Fichaje y Jornada", "Capacitacion y Fichaje Laboral", 20);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.className = "flow-feedback-box hidden";
  feedbackBox.innerHTML = "";
  btnNext.classList.add("hidden");
  container.innerHTML = "<p class='text-muted'>Cargando pregunta laboral de la jornada...</p>";

  try {
    const res = await fetch("/api/work_quiz");
    const quiz = await res.json();

    container.innerHTML = `
      <div class="flow-question-prompt">
        <span class="badge badge-sky" style="margin-bottom:0.5rem; display:inline-block;">${quiz.topic.toUpperCase()}</span>
        <p>${quiz.question}</p>
      </div>
      <div id="trivia-options-stack" class="flow-options-grid"></div>
    `;

    const optionsStack = document.getElementById("trivia-options-stack");
    quiz.options.forEach((optText, index) => {
      const btn = document.createElement("button");
      btn.className = "btn-flow-card-choice";
      btn.innerHTML = `<span class="choice-primary-name">${index + 1}. ${optText}</span>`;
      btn.onclick = () => submitFlowTrivia(index);
      optionsStack.appendChild(btn);
    });
  } catch (err) {
    container.innerHTML = "<p class='text-rose'>Error al cargar la jornada laboral.</p>";
  }
}

async function submitFlowTrivia(optionIndex) {
  const optionsStack = document.getElementById("trivia-options-stack");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  Array.from(optionsStack.children).forEach(b => b.disabled = true);

  try {
    const res = await fetch("/api/work_quiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ option_index: optionIndex })
    });
    const result = await res.json();

    dailyFlowState.dailyEarned += (result.daily_salary_earned || 40000);
    dailyFlowState.dailyUtilityGained += (result.utility_bonus || 10);

    feedbackBox.classList.remove("hidden");
    if (result.is_correct) {
      feedbackBox.className = "flow-feedback-box correct";
      feedbackBox.innerHTML = `
        <strong>Respuesta Correcta</strong>
        <p>${result.explanation}</p>
        <p style="margin-top:0.4rem; font-weight:700;">Jornada computada: +${formatCurrency(result.daily_salary_earned)} devengados y +${result.utility_bonus} pts bienestar.</p>
      `;
    } else {
      feedbackBox.className = "flow-feedback-box incorrect";
      feedbackBox.innerHTML = `
        <strong>Respuesta Inexacta</strong>
        <p>${result.explanation}</p>
        <p style="margin-top:0.4rem;">Jornada computada por asistencia presencial: +${formatCurrency(result.daily_salary_earned)} devengados.</p>
      `;
    }

    btnNext.textContent = "Continuar: Desayuno y Cafe >>";
    btnNext.classList.remove("hidden");
    btnNext.onclick = () => renderFlowStep2Breakfast();
  } catch (err) {
    console.error("Error al registrar trivia:", err);
  }
}

// Paso 1 (Variante Ausencia): Notificacion de inasistencia
function renderFlowStep1AbsenceNotice(absenceMessage) {
  updateFlowHeader("Etapa 1 de 5: Ausencia Laboral", "Jornada de Descanso en el Hogar", 20);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.className = "flow-feedback-box hidden";
  feedbackBox.innerHTML = "";

  container.innerHTML = `
    <div style="background:var(--bg-card); padding:1.2rem; border-radius:12px; border:1px solid var(--border-subtle);">
      <span class="badge badge-rose" style="margin-bottom:0.5rem; display:inline-block;">Inasistencia Registrada</span>
      <p style="font-size:0.95rem; line-height:1.5;">${absenceMessage || "Has decidido no asistir a trabajar en el dia de hoy. Se computara una falta y se descontaran $40.000,00 a fin de mes."}</p>
      <p style="margin-top:0.6rem; color:var(--text-muted); font-size:0.85rem;">
        Las horas extras del dia quedan bloqueadas. Tu jornada continuara con opciones cotidianas adaptadas a un dia de permanencia y descanso en casa.
      </p>
    </div>
  `;

  btnNext.textContent = "Continuar: Desayuno en Casa >>";
  btnNext.classList.remove("hidden");
  btnNext.onclick = () => renderFlowStep2AbsentBreakfast();
}

// Paso 2 (Jornada Laboral): Eleccion Matutina
function renderFlowStep2Breakfast() {
  updateFlowHeader("Etapa 2 de 5: Eleccion Matutina", "Desayuno y Cafe antes de Salir", 40);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.className = "flow-feedback-box hidden";
  feedbackBox.innerHTML = "";
  btnNext.classList.add("hidden");

  const poolIdx = (dailyFlowState.currentDay - 1) % BREAKFAST_POOLS.length;
  const breakfast = BREAKFAST_POOLS[poolIdx];

  container.innerHTML = `
    <div class="flow-question-prompt">
      <p>Son las 7:30 AM antes de salir a la jornada laboral. ¿Te llevas el cafe preparado de tu casa o compras uno al paso por el camino?</p>
    </div>
    <div class="flow-options-grid">
      <button class="btn-flow-card-choice" onclick="selectFlowBreakfast('casa', ${breakfast.casa.cost}, ${breakfast.casa.utility})">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${breakfast.casa.name}</span>
          <span class="choice-sub-desc">${breakfast.casa.desc}</span>
        </div>
        <span class="choice-cost-badge text-mint">-$${breakfast.casa.cost.toLocaleString('es-AR')} (+${breakfast.casa.utility} U)</span>
      </button>

      <button class="btn-flow-card-choice" onclick="selectFlowBreakfast('paso', ${breakfast.paso.cost}, ${breakfast.paso.utility})">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${breakfast.paso.name}</span>
          <span class="choice-sub-desc">${breakfast.paso.desc}</span>
        </div>
        <span class="choice-cost-badge text-honey">-$${breakfast.paso.cost.toLocaleString('es-AR')} (+${breakfast.paso.utility} U)</span>
      </button>
    </div>
  `;
}

async function selectFlowBreakfast(choice, cost, utility) {
  dailyFlowState.dailyUtilityGained += utility;
  const data = await recordMicroChoice(null, null, utility, cost);

  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.classList.remove("hidden");
  feedbackBox.className = "flow-feedback-box";
  const remainingCash = data?.remaining_cash !== undefined ? `Billetera disponible: ${formatCurrency(data.remaining_cash)}.` : "";

  feedbackBox.innerHTML = `
    <strong>Eleccion de Desayuno Registrada</strong>
    <p>${choice === 'casa' ? `Optaste por ahorrar preparando tu desayuno en casa (+${utility} utilidad).` : `Disfrutaste un excelente cafe al paso en la ciudad (+${utility} utilidad).`}</p>
    <p style="margin-top:0.4rem; font-weight:700;">Debitado en tiempo real: <span class="text-rose">-${formatCurrency(cost)}</span>. ${remainingCash}</p>
  `;

  btnNext.textContent = "Continuar: Traslado y Movilidad >>";
  btnNext.classList.remove("hidden");
  btnNext.onclick = () => renderFlowStep3Mobility();
}

// Paso 2 (Variante Ausencia): Desayuno relajado en casa
function renderFlowStep2AbsentBreakfast() {
  updateFlowHeader("Etapa 2 de 5: Desayuno Hogareno", "Desayuno Relajado en el Departamento", 40);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.className = "flow-feedback-box hidden";
  feedbackBox.innerHTML = "";
  btnNext.classList.add("hidden");

  const poolIdx = (dailyFlowState.currentDay - 1) % ABSENT_MORNING_POOLS.length;
  const morning = ABSENT_MORNING_POOLS[poolIdx];

  container.innerHTML = `
    <div class="flow-question-prompt">
      <p>Son las 9:30 AM en tu departamento en tu dia de descanso. ¿Como decides desayunar hoy?</p>
    </div>
    <div class="flow-options-grid">
      <button class="btn-flow-card-choice" onclick="selectFlowAbsentBreakfast('casa', ${morning.casa.cost}, ${morning.casa.utility})">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${morning.casa.name}</span>
          <span class="choice-sub-desc">${morning.casa.desc}</span>
        </div>
        <span class="choice-cost-badge text-mint">-$${morning.casa.cost.toLocaleString('es-AR')} (+${morning.casa.utility} U)</span>
      </button>

      <button class="btn-flow-card-choice" onclick="selectFlowAbsentBreakfast('brunch', ${morning.brunch.cost}, ${morning.brunch.utility})">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${morning.brunch.name}</span>
          <span class="choice-sub-desc">${morning.brunch.desc}</span>
        </div>
        <span class="choice-cost-badge text-honey">-$${morning.brunch.cost.toLocaleString('es-AR')} (+${morning.brunch.utility} U)</span>
      </button>
    </div>
  `;
}

async function selectFlowAbsentBreakfast(choice, cost, utility) {
  dailyFlowState.dailyUtilityGained += utility;
  const data = await recordMicroChoice(null, null, utility, cost);

  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.classList.remove("hidden");
  feedbackBox.className = "flow-feedback-box";
  const remainingCash = data?.remaining_cash !== undefined ? `Billetera disponible: ${formatCurrency(data.remaining_cash)}.` : "";

  feedbackBox.innerHTML = `
    <strong>Desayuno en Casa Registrado</strong>
    <p>${choice === 'casa' ? `Desayunaste tranquilo en tu cocina (+${utility} utilidad).` : `Disfrutaste un brunch a domicilio en el living (+${utility} utilidad).`}</p>
    <p style="margin-top:0.4rem; font-weight:700;">Debitado en tiempo real: <span class="text-rose">-${formatCurrency(cost)}</span>. ${remainingCash}</p>
  `;

  btnNext.textContent = "Continuar: Plan de la Tarde >>";
  btnNext.classList.remove("hidden");
  btnNext.onclick = () => renderFlowStep3AbsentActivity();
}

// Paso 3 (Jornada Laboral): Eleccion de Movilidad / Transito
function renderFlowStep3Mobility() {
  updateFlowHeader("Etapa 3 de 5: Movilidad y Traslado", "Traslado Urbano por la Ciudad", 60);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.className = "flow-feedback-box hidden";
  feedbackBox.innerHTML = "";
  btnNext.classList.add("hidden");

  // Paro de transporte maximo 1 vez por mes
  const availableSituations = transitStrikeOccurredThisMonth
    ? TRANSIT_SITUATIONS.filter(s => !s.isStrike)
    : TRANSIT_SITUATIONS;

  const situation = availableSituations[(dailyFlowState.currentDay - 1) % availableSituations.length];

  if (situation.isStrike && !transitStrikeOccurredThisMonth) {
    transitStrikeOccurredThisMonth = true;
    fetch("/api/record_transit_strike", { method: "POST" }).catch(() => {});
  }

  // En dias de embotellamiento/congestión/paro: colectivo resta 10 puntos de bienestar
  const subteUtility = situation.isCongested ? -10 : 5;
  const subteCost = 850;
  const uberUtility = 25;
  const uberCost = 12000;

  const badgeClass = situation.isCongested ? "text-rose" : "text-mint";
  const badgeLabel = situation.isCongested ? "Subte (-10 U)" : "Subte (+5 U)";
  const subteDesc = situation.isCongested
    ? "Aglomeraciones y demoras pesadas (-10 pts de bienestar)."
    : "Viaje agil, sustentable y economico (+5 pts de bienestar).";

  container.innerHTML = `
    <div class="flow-question-prompt">
      <div class="badge badge-rose" style="margin-bottom:0.5rem; display:inline-block;">Estado del Transito</div>
      <p><strong>${situation.text}</strong></p>
      <p style="font-size:0.9rem; margin-top:0.4rem;" class="text-muted">¿Como decides trasladarte para cumplir con tu jornada laboral?</p>
    </div>
    <div class="flow-options-grid">
      <button class="btn-flow-card-choice" onclick="selectFlowMobility('trans_publico', ${subteUtility}, ${subteCost})">
        <div class="choice-name-desc">
          <span class="choice-primary-name">Transporte Publico (Subte y Colectivo)</span>
          <span class="choice-sub-desc">${subteDesc}</span>
        </div>
        <span class="choice-cost-badge ${badgeClass}">-$${subteCost.toLocaleString('es-AR')} (${badgeLabel})</span>
      </button>

      <button class="btn-flow-card-choice" onclick="selectFlowMobility('trans_uber', ${uberUtility}, ${uberCost})">
        <div class="choice-name-desc">
          <span class="choice-primary-name">Viaje Privado (Uber / Cabify)</span>
          <span class="choice-sub-desc">Traslado comodo directo puerta a puerta evitando el estres vial.</span>
        </div>
        <span class="choice-cost-badge text-honey">-$${uberCost.toLocaleString('es-AR')} (+${uberUtility} U)</span>
      </button>
    </div>
  `;
}

async function selectFlowMobility(optionId, utility, cost) {
  dailyFlowState.dailyUtilityGained += utility;
  const data = await recordMicroChoice("transporte", optionId, utility, cost);

  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.classList.remove("hidden");
  feedbackBox.className = "flow-feedback-box";
  const costNotice = `Debitado en tiempo real: -${formatCurrency(cost)}. `;
  const remainingCash = data?.remaining_cash !== undefined ? `Billetera: ${formatCurrency(data.remaining_cash)}.` : "";
  const utilNotice = utility < 0
    ? `Perdiste ${Math.abs(utility)} pts de bienestar por congestion y demoras.`
    : `Sumaste +${utility} pts de bienestar.`;

  feedbackBox.innerHTML = `
    <strong>Eleccion de Movilidad Aplicada</strong>
    <p>${utilNotice}</p>
    <p style="margin-top:0.4rem; font-weight:700;">${costNotice}${remainingCash}</p>
  `;

  btnNext.textContent = "Continuar: Almuerzo >>";
  btnNext.classList.remove("hidden");
  btnNext.onclick = () => renderFlowStep4Lunch();
}

// Paso 3 (Variante Ausencia): Ocio y Permanencia en el Hogar (SIN traslados laborales)
function renderFlowStep3AbsentActivity() {
  updateFlowHeader("Etapa 3 de 5: Ocio y Descanso", "Actividad del Dia sin Traslados Laborales", 60);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.className = "flow-feedback-box hidden";
  feedbackBox.innerHTML = "";
  btnNext.classList.add("hidden");

  const poolIdx = (dailyFlowState.currentDay - 1) % ABSENT_ACTIVITY_POOLS.length;
  const activity = ABSENT_ACTIVITY_POOLS[poolIdx];

  container.innerHTML = `
    <div class="flow-question-prompt">
      <div class="badge badge-sky" style="margin-bottom:0.5rem; display:inline-block;">Dia de Descanso en Casa</div>
      <p>Estas en tu departamento sin traslados ni obligaciones de oficina. ¿Que decides hacer durante la tarde?</p>
    </div>
    <div class="flow-options-grid">
      <button class="btn-flow-card-choice" onclick="selectFlowAbsentActivity('hogar', ${activity.hogar.cost}, ${activity.hogar.utility})">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${activity.hogar.name}</span>
          <span class="choice-sub-desc">${activity.hogar.desc}</span>
        </div>
        <span class="choice-cost-badge text-mint">Sin costo (+${activity.hogar.utility} U)</span>
      </button>

      <button class="btn-flow-card-choice" onclick="selectFlowAbsentActivity('paseo', ${activity.paseo.cost}, ${activity.paseo.utility})">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${activity.paseo.name}</span>
          <span class="choice-sub-desc">${activity.paseo.desc}</span>
        </div>
        <span class="choice-cost-badge text-honey">-$${activity.paseo.cost.toLocaleString('es-AR')} (+${activity.paseo.utility} U)</span>
      </button>
    </div>
  `;
}

async function selectFlowAbsentActivity(choice, cost, utility) {
  dailyFlowState.dailyUtilityGained += utility;
  const data = await recordMicroChoice("entretenimiento", choice === 'hogar' ? "ocio_hogar" : "ocio_salidas", utility, cost);

  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.classList.remove("hidden");
  feedbackBox.className = "flow-feedback-box";
  const costNotice = cost > 0 ? `Debitado en tiempo real: -${formatCurrency(cost)}. ` : "Sin impacto monetario. ";
  const remainingCash = data?.remaining_cash !== undefined ? `Billetera: ${formatCurrency(data.remaining_cash)}.` : "";

  feedbackBox.innerHTML = `
    <strong>Actividad Registrada</strong>
    <p>${choice === 'hogar' ? `Descanso placentero y cero gasto en casa (+${utility} utilidad).` : `Paseo relajante por el barrio (+${utility} utilidad).`}</p>
    <p style="margin-top:0.4rem; font-weight:700;">${costNotice}${remainingCash}</p>
  `;

  btnNext.textContent = "Continuar: Almuerzo en Casa >>";
  btnNext.classList.remove("hidden");
  btnNext.onclick = () => renderFlowStep4AbsentLunch();
}

// Paso 4 (Jornada Laboral): Almuerzo dinámico
function renderFlowStep4Lunch() {
  updateFlowHeader("Etapa 4 de 5: Pausa de Almuerzo", "Almuerzo en Jornada Laboral", 80);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.className = "flow-feedback-box hidden";
  feedbackBox.innerHTML = "";
  btnNext.classList.add("hidden");

  const poolIdx = (dailyFlowState.currentDay - 1) % LUNCH_POOLS.length;
  const lunch = LUNCH_POOLS[poolIdx];

  container.innerHTML = `
    <div class="flow-question-prompt">
      <p>Es el mediodia y es momento de almorzar durante tu jornada. ¿Que decides comer hoy?</p>
    </div>
    <div class="flow-options-grid">
      <button class="btn-flow-card-choice" onclick="selectFlowLunch('vianda', ${lunch.vianda.utility}, ${lunch.vianda.cost}, '${lunch.vianda.name}')">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${lunch.vianda.name}</span>
          <span class="choice-sub-desc">${lunch.vianda.desc}</span>
        </div>
        <span class="choice-cost-badge text-mint">-$${lunch.vianda.cost.toLocaleString('es-AR')} (+${lunch.vianda.utility} U)</span>
      </button>

      <button class="btn-flow-card-choice" onclick="selectFlowLunch('ejecutivo', ${lunch.ejecutivo.utility}, ${lunch.ejecutivo.cost}, '${lunch.ejecutivo.name}')">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${lunch.ejecutivo.name}</span>
          <span class="choice-sub-desc">${lunch.ejecutivo.desc}</span>
        </div>
        <span class="choice-cost-badge text-purple">-$${lunch.ejecutivo.cost.toLocaleString('es-AR')} (+${lunch.ejecutivo.utility} U)</span>
      </button>

      <button class="btn-flow-card-choice" onclick="selectFlowLunch('rapido', ${lunch.rapido.utility}, ${lunch.rapido.cost}, '${lunch.rapido.name}')">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${lunch.rapido.name}</span>
          <span class="choice-sub-desc">${lunch.rapido.desc}</span>
        </div>
        <span class="choice-cost-badge text-honey">-$${lunch.rapido.cost.toLocaleString('es-AR')} (+${lunch.rapido.utility} U)</span>
      </button>
    </div>
  `;
}

async function selectFlowLunch(type, utility, cost, dishName) {
  dailyFlowState.dailyUtilityGained += utility;
  const data = await recordMicroChoice(null, null, utility, cost);

  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.classList.remove("hidden");
  feedbackBox.className = "flow-feedback-box";
  const remainingCash = data?.remaining_cash !== undefined ? `Billetera disponible: ${formatCurrency(data.remaining_cash)}.` : "";

  feedbackBox.innerHTML = `
    <strong>Almuerzo Completado</strong>
    <p>Has elegido: ${dishName} (+${utility} utilidad).</p>
    <p style="margin-top:0.4rem; font-weight:700;">Debitado en tiempo real: <span class="text-rose">-${formatCurrency(cost)}</span>. ${remainingCash}</p>
  `;

  btnNext.textContent = "Continuar: Hora de Cenar >>";
  btnNext.classList.remove("hidden");
  btnNext.onclick = () => renderFlowStep5Dinner();
}

// Paso 4 (Variante Ausencia): Almuerzo en el Hogar (SIN viandas para la oficina)
function renderFlowStep4AbsentLunch() {
  updateFlowHeader("Etapa 4 de 5: Almuerzo Hogareno", "Almuerzo en el Departamento", 80);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.className = "flow-feedback-box hidden";
  feedbackBox.innerHTML = "";
  btnNext.classList.add("hidden");

  const poolIdx = (dailyFlowState.currentDay - 1) % ABSENT_LUNCH_POOLS.length;
  const lunch = ABSENT_LUNCH_POOLS[poolIdx];

  container.innerHTML = `
    <div class="flow-question-prompt">
      <p>Es mediodia en tu dia libre en casa. ¿Que decides comer sin apuros laborales?</p>
    </div>
    <div class="flow-options-grid">
      <button class="btn-flow-card-choice" onclick="selectFlowAbsentLunch('cocina', ${lunch.cocina.cost}, ${lunch.cocina.utility}, '${lunch.cocina.name}')">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${lunch.cocina.name}</span>
          <span class="choice-sub-desc">${lunch.cocina.desc}</span>
        </div>
        <span class="choice-cost-badge text-mint">-$${lunch.cocina.cost.toLocaleString('es-AR')} (+${lunch.cocina.utility} U)</span>
      </button>

      <button class="btn-flow-card-choice" onclick="selectFlowAbsentLunch('delivery', ${lunch.delivery.cost}, ${lunch.delivery.utility}, '${lunch.delivery.name}')">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${lunch.delivery.name}</span>
          <span class="choice-sub-desc">${lunch.delivery.desc}</span>
        </div>
        <span class="choice-cost-badge text-purple">-$${lunch.delivery.cost.toLocaleString('es-AR')} (+${lunch.delivery.utility} U)</span>
      </button>
    </div>
  `;
}

async function selectFlowAbsentLunch(choice, cost, utility, name) {
  dailyFlowState.dailyUtilityGained += utility;
  const data = await recordMicroChoice("comida_ocio", choice === 'cocina' ? "food_cocina" : "food_delivery", utility, cost);

  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.classList.remove("hidden");
  feedbackBox.className = "flow-feedback-box";
  const remainingCash = data?.remaining_cash !== undefined ? `Billetera disponible: ${formatCurrency(data.remaining_cash)}.` : "";

  feedbackBox.innerHTML = `
    <strong>Almuerzo Hogareno Registrado</strong>
    <p>Has elegido: ${name} (+${utility} utilidad).</p>
    <p style="margin-top:0.4rem; font-weight:700;">Debitado en tiempo real: <span class="text-rose">-${formatCurrency(cost)}</span>. ${remainingCash}</p>
  `;

  btnNext.textContent = "Continuar: Hora de Cenar >>";
  btnNext.classList.remove("hidden");
  btnNext.onclick = () => renderFlowStep5AbsentDinner();
}

// Paso 5 (Jornada Laboral): Eleccion de Cena
function renderFlowStep5Dinner() {
  updateFlowHeader("Etapa 5 de 5: Hora de Cenar", "Cena y Cierre de la Jornada", 100);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.className = "flow-feedback-box hidden";
  feedbackBox.innerHTML = "";
  btnNext.classList.add("hidden");

  const poolIdx = (dailyFlowState.currentDay - 1) % DINNER_POOLS.length;
  const dinner = DINNER_POOLS[poolIdx];

  container.innerHTML = `
    <div class="flow-question-prompt">
      <p>Cae la noche y llega el momento de la cena. ¿Que decides cenar hoy?</p>
    </div>
    <div class="flow-options-grid">
      <button class="btn-flow-card-choice" onclick="selectFlowDinner('${dinner.cocina.optId}', ${dinner.cocina.utility}, ${dinner.cocina.cost}, '${dinner.cocina.name}')">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${dinner.cocina.name}</span>
          <span class="choice-sub-desc">Preparacion casera (tarea cotidiana, 0 U de bienestar extra).</span>
        </div>
        <span class="choice-cost-badge text-mint">-$${dinner.cocina.cost.toLocaleString('es-AR')} (0 U)</span>
      </button>

      <button class="btn-flow-card-choice" onclick="selectFlowDinner('${dinner.delivery1.optId}', ${dinner.delivery1.utility}, ${dinner.delivery1.cost}, '${dinner.delivery1.name}')">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${dinner.delivery1.name}</span>
          <span class="choice-sub-desc">Comida caliente a domicilio y relax nocturno.</span>
        </div>
        <span class="choice-cost-badge text-purple">-$${dinner.delivery1.cost.toLocaleString('es-AR')} (+${dinner.delivery1.utility} U)</span>
      </button>

      <button class="btn-flow-card-choice" onclick="selectFlowDinner('${dinner.delivery2.optId}', ${dinner.delivery2.utility}, ${dinner.delivery2.cost}, '${dinner.delivery2.name}')">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${dinner.delivery2.name}</span>
          <span class="choice-sub-desc">Gusto nocturno especial y comodidad plena.</span>
        </div>
        <span class="choice-cost-badge text-purple">-$${dinner.delivery2.cost.toLocaleString('es-AR')} (+${dinner.delivery2.utility} U)</span>
      </button>
    </div>
  `;
}

async function selectFlowDinner(optionId, utility, cost, dishName) {
  dailyFlowState.dailyUtilityGained += utility;
  const data = await recordMicroChoice("comida_ocio", optionId, utility, cost);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  const summaryHeading = "Jornada Laboral Completada con Exito";
  const remainingCash = data?.remaining_cash !== undefined ? `Billetera actual: ${formatCurrency(data.remaining_cash)}.` : "";

  container.innerHTML = `
    <div style="background:var(--bg-card); padding:1.25rem; border-radius:12px; border:1px solid var(--border-subtle);">
      <h4 class="text-mint" style="margin-bottom:0.65rem; font-size:1.15rem;">${summaryHeading}</h4>
      <p>• Salario de la jornada devengado: <strong class="text-mint">+${formatCurrency(dailyFlowState.dailyEarned)}</strong></p>
      <p>• Puntos de bienestar acumulados en el dia: <strong class="text-purple">+${dailyFlowState.dailyUtilityGained} pts</strong></p>
      <p>• Ultimo debito (cena): <strong class="text-rose">-${formatCurrency(cost)}</strong>. ${remainingCash}</p>
      <p style="margin-top:0.6rem; color:var(--text-muted); font-size:0.85rem;">
        La terminal de <strong>HORAS EXTRAS</strong> se encuentra ahora desbloqueada en tu panel si deseas sumar ingresos adicionales.
      </p>
    </div>
  `;

  feedbackBox.classList.add("hidden");
  btnNext.textContent = "Finalizar Jornada";
  btnNext.classList.remove("hidden");
  btnNext.onclick = () => {
    document.getElementById("modal-daily-flow").close();
    fetchState();
  };
}

// Paso 5 (Variante Ausencia): Cena hogareña de cierre
function renderFlowStep5AbsentDinner() {
  updateFlowHeader("Etapa 5 de 5: Cena de Descanso", "Cena y Cierre del Dia en Casa", 100);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  feedbackBox.className = "flow-feedback-box hidden";
  feedbackBox.innerHTML = "";
  btnNext.classList.add("hidden");

  const poolIdx = (dailyFlowState.currentDay - 1) % ABSENT_DINNER_POOLS.length;
  const dinner = ABSENT_DINNER_POOLS[poolIdx];

  container.innerHTML = `
    <div class="flow-question-prompt">
      <p>Cae la noche en tu dia hogareno. ¿Como decides cenar para cerrar la jornada?</p>
    </div>
    <div class="flow-options-grid">
      <button class="btn-flow-card-choice" onclick="selectFlowAbsentDinner('cocina', ${dinner.cocina.cost}, ${dinner.cocina.utility}, '${dinner.cocina.name}')">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${dinner.cocina.name}</span>
          <span class="choice-sub-desc">${dinner.cocina.desc}</span>
        </div>
        <span class="choice-cost-badge text-mint">-$${dinner.cocina.cost.toLocaleString('es-AR')} (0 U)</span>
      </button>

      <button class="btn-flow-card-choice" onclick="selectFlowAbsentDinner('delivery', ${dinner.delivery.cost}, ${dinner.delivery.utility}, '${dinner.delivery.name}')">
        <div class="choice-name-desc">
          <span class="choice-primary-name">${dinner.delivery.name}</span>
          <span class="choice-sub-desc">${dinner.delivery.desc}</span>
        </div>
        <span class="choice-cost-badge text-purple">-$${dinner.delivery.cost.toLocaleString('es-AR')} (+${dinner.delivery.utility} U)</span>
      </button>
    </div>
  `;
}

async function selectFlowAbsentDinner(choice, cost, utility, dishName) {
  dailyFlowState.dailyUtilityGained += utility;
  const data = await recordMicroChoice("comida_ocio", choice === 'cocina' ? "food_cocina" : "food_delivery_pizza", utility, cost);

  const container = document.getElementById("flow-step-content");
  const feedbackBox = document.getElementById("flow-step-feedback");
  const btnNext = document.getElementById("btn-flow-next");

  const remainingCash = data?.remaining_cash !== undefined ? `Billetera actual: ${formatCurrency(data.remaining_cash)}.` : "";

  container.innerHTML = `
    <div style="background:var(--bg-card); padding:1.25rem; border-radius:12px; border:1px solid var(--border-subtle);">
      <h4 class="text-honey" style="margin-bottom:0.65rem; font-size:1.15rem;">Jornada de Ausencia Finalizada</h4>
      <p>• Salario: <strong class="text-rose">-$40.000,00 descontados a fin de mes por inasistencia</strong></p>
      <p>• Puntos de bienestar acumulados en el dia: <strong class="text-purple">+${dailyFlowState.dailyUtilityGained} pts</strong></p>
      <p>• Ultimo debito (cena): <strong class="text-rose">-${formatCurrency(cost)}</strong>. ${remainingCash}</p>
      <p style="margin-top:0.6rem; color:var(--text-muted); font-size:0.85rem;">
        Las horas extras permanecen bloqueadas hoy por haber registrado ausencia laboral.
      </p>
    </div>
  `;

  feedbackBox.classList.add("hidden");
  btnNext.textContent = "Finalizar Jornada";
  btnNext.classList.remove("hidden");
  btnNext.onclick = () => {
    document.getElementById("modal-daily-flow").close();
    fetchState();
  };
}

function updateFlowHeader(stepTag, title, progressPct) {
  document.getElementById("flow-step-tag").textContent = stepTag;
  document.getElementById("flow-title").textContent = title;
  document.getElementById("flow-progress-fill").style.width = `${progressPct}%`;
}

async function recordMicroChoice(category, optionId, bonusUtility, cost = 0) {
  try {
    const res = await fetch("/api/daily_choice", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        category: category,
        option_id: optionId,
        bonus_utility: bonusUtility,
        cost: cost
      })
    });
    const data = await res.json();
    if (data && data.state) {
      currentGameState = data.state;
      renderTopHUD(data.state);
    }
    return data;
  } catch (err) {
    console.error("Error al registrar micro eleccion:", err);
    return null;
  }
}

// -----------------------------------------------------------------------------
// 7. ACCION DE NO IR A TRABAJAR (AUSENCIA CON FLUJO DIARIO COMPLETO)
// -----------------------------------------------------------------------------
function confirmSkipDay() {
  showConfirmDialog(
    "Registrar Ausencia Laboral",
    "¿Estas seguro de no ir a trabajar hoy? Se computara una falta y se descontaran $40.000,00 de tu liquidacion mensual. Sin embargo, tu dia continuara con las decisiones cotidianas habituales.",
    async () => {
      try {
        const res = await fetch("/api/skip_day", { method: "POST" });
        const result = await res.json();
        // Iniciar el flujo diario completo aun en ausencia
        startDailyAbsenceFlow(result.message);
      } catch (err) {
        console.error("Error al saltear dia:", err);
      }
    },
    "Confirmar Falta",
    "Cancelar y Volver"
  );
}

// -----------------------------------------------------------------------------
// 8. HORAS EXTRAS CONDICIONALES (POR PARTICIPACION)
// -----------------------------------------------------------------------------
async function openOvertimeModal() {
  if (!currentGameState?.can_request_overtime) {
    showNotificationDialog(
      "Acceso Restringido",
      "Las horas extras estan unicamente habilitadas para empleados con asistencia presencial confirmada en el dia de hoy.",
      "Bloqueado"
    );
    return;
  }

  const dialog = document.getElementById("modal-overtime");
  const statementEl = document.getElementById("overtime-modal-statement");
  const optionsEl = document.getElementById("overtime-modal-options");
  const hintEl = document.getElementById("overtime-modal-hint");
  const feedbackEl = document.getElementById("overtime-modal-feedback");
  const btnClose = document.getElementById("btn-close-overtime-modal");

  feedbackEl.className = "flow-feedback-box hidden";
  feedbackEl.innerHTML = "";
  btnClose.classList.add("hidden");
  optionsEl.innerHTML = "<p class='text-muted'>Generando calculo en tiempo real...</p>";

  dialog.showModal();

  try {
    const res = await fetch("/api/overtime_challenge");
    if (res.status === 403) {
      dialog.close();
      showNotificationDialog(
        "Acceso Denegado",
        "No puedes acceder a horas extras sin haber asistido a trabajar hoy.",
        "Bloqueado"
      );
      return;
    }

    const data = await res.json();
    statementEl.textContent = data.statement;
    hintEl.textContent = data.hint;
    optionsEl.innerHTML = "";

    data.options.forEach((optText, index) => {
      const btn = document.createElement("button");
      btn.className = "btn-overtime-select";
      btn.textContent = `${index + 1}. ${optText}`;
      btn.onclick = () => submitOvertimeModalAnswer(index);
      optionsEl.appendChild(btn);
    });
  } catch (err) {
    optionsEl.textContent = "Error al solicitar desafio financiero.";
  }
}

async function submitOvertimeModalAnswer(optionIndex) {
  const optionsEl = document.getElementById("overtime-modal-options");
  const feedbackEl = document.getElementById("overtime-modal-feedback");
  const btnClose = document.getElementById("btn-close-overtime-modal");

  Array.from(optionsEl.children).forEach(b => b.disabled = true);

  try {
    const res = await fetch("/api/overtime_challenge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ option_index: optionIndex })
    });
    const result = await res.json();

    feedbackEl.classList.remove("hidden");
    if (result.is_correct) {
      feedbackEl.className = "flow-feedback-box correct";
      feedbackEl.innerHTML = `
        <strong>Calculo Financiero Exacto</strong>
        <p>${result.message}</p>
        <p style="margin-top:0.4rem; font-weight:700;">Se ha anadido la insignia de 'Horas extras' en el casillero de hoy del calendario.</p>
      `;
    } else {
      feedbackEl.className = "flow-feedback-box";
      feedbackEl.innerHTML = `
        <strong>Actividad Completada por Participacion</strong>
        <p>${result.message}</p>
        <p style="margin-top:0.4rem; font-weight:700;">Bono de horas extras acreditado al sueldo por participacion. Se anadio la insignia en el calendario.</p>
      `;
    }

    btnClose.classList.remove("hidden");
  } catch (err) {
    console.error("Error al validar horas extras:", err);
  }
}

// -----------------------------------------------------------------------------
// 9. AVANZAR AL SIGUIENTE DIA
// -----------------------------------------------------------------------------
async function advanceDay() {
  try {
    const res = await fetch("/api/advance_day", { method: "POST" });
    await res.json();
    fetchState();
  } catch (err) {
    console.error("Error al avanzar dia:", err);
  }
}

// -----------------------------------------------------------------------------
// 10. EVENTOS IMPREVISTOS / CRISIS POP-UP
// -----------------------------------------------------------------------------
function checkActiveCrisis(state) {
  const dialog = document.getElementById("modal-crisis-popup");
  if (state.active_crisis) {
    const crisis = state.active_crisis;
    document.getElementById("crisis-popup-title").textContent = crisis.title;
    document.getElementById("crisis-popup-desc").textContent = crisis.description;
    document.getElementById("crisis-popup-amount").textContent = formatCurrency(crisis.cost);

    document.getElementById("crisis-cash-sub").textContent =
      `Debita ${formatCurrency(crisis.cost)} inmediatamente. Menor perdida de bienestar (${crisis.impact_utility} pts).`;
    document.getElementById("crisis-finance-sub").textContent =
      `Debita ${formatCurrency(crisis.finance_cost)} financiado (+15% de recargo). Mayor costo de oportunidad.`;

    if (!dialog.open) {
      dialog.showModal();
    }
  } else {
    if (dialog.open) {
      dialog.close();
    }
  }
}

async function resolveCrisis(choice) {
  try {
    const res = await fetch("/api/resolve_crisis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ choice })
    });
    const data = await res.json();
    if (data.success) {
      document.getElementById("modal-crisis-popup").close();
      showNotificationDialog(
        "Emergencia Resuelta",
        `Se liquidaron ${formatCurrency(data.amount_paid)} (${choice === 'cash' ? 'al contado' : 'financiado con recargo del 15%'}).`,
        "Crisis Resuelta"
      );
      fetchState();
    }
  } catch (err) {
    console.error("Error al resolver crisis:", err);
  }
}

// -----------------------------------------------------------------------------
// 11. LIQUIDACION DE FIN DE MES (DIA 30)
// -----------------------------------------------------------------------------
function confirmEndMonth() {
  showConfirmDialog(
    "Liquidar Mes",
    "¿Deseas cerrar el dia 30 y ejecutar el balance de sueldos devengados, gastos fijos e intereses por descubierto?",
    async () => {
      try {
        const res = await fetch("/api/end_month", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          showMonthSummaryModal(data.summary, data.is_game_over, data.final_evaluation);
        } else {
          showNotificationDialog("Error", data.error, "Error");
        }
      } catch (err) {
        console.error("Error al liquidar mes:", err);
      }
    },
    "Liquidar Mes",
    "Cancelar"
  );
}

function showMonthSummaryModal(summary, isGameOver = false, finalEvaluation = null) {
  const dialog = document.getElementById("modal-month-summary");
  const monthName = summary.month_name || `Mes ${summary.month}`;
  document.getElementById("summary-month-heading").textContent = `Balance de Cierre - Mes ${summary.month} (${monthName})`;
  const container = document.getElementById("summary-breakdown-container");

  container.innerHTML = `
    <div class="summary-column-box">
      <h4 class="text-mint">Ingresos Devengados</h4>
      <p>• Dias trabajados: <strong>${summary.worked_days} de 30</strong></p>
      <p>• Inasistencias: <strong>${summary.unworked_days}</strong></p>
      <p>• Sueldo base percibido: <strong>${formatCurrency(summary.base_salary_earned)}</strong></p>
      <p>• Descuento por faltas: <strong class="text-rose">-${formatCurrency(summary.absence_deduction)}</strong></p>
      <p>• Bonificacion horas extras: <strong class="text-sky">+${formatCurrency(summary.overtime_earned)}</strong></p>
      <hr style="border:0; border-top:1px solid var(--border-subtle); margin:0.35rem 0;">
      <p>Total sueldo en mano: <strong class="text-mint">${formatCurrency(summary.net_salary_liquidated)}</strong></p>
    </div>

    <div class="summary-column-box">
      <h4 class="text-rose">Gastos y Balance Resultante</h4>
      <p>• Costos fijos indexados: <strong>${formatCurrency(summary.total_fixed_cost)}</strong></p>
      <p>• Estilo de vida y ocio: <strong>${formatCurrency(summary.total_discretionary_cost)}</strong></p>
      <p>• Contingencias e imprevistos: <strong>${formatCurrency(summary.total_unforeseen_cost)}</strong></p>
      <p>• Intereses bancarios (TEM): <strong class="text-rose">-${formatCurrency(summary.interest_applied)}</strong></p>
      <hr style="border:0; border-top:1px solid var(--border-subtle); margin:0.35rem 0;">
      <p>• Efectivo al cierre: <strong class="text-mint">${formatCurrency(summary.ending_cash)}</strong></p>
      <p>• Deuda bancaria resultante: <strong class="text-rose">${formatCurrency(summary.ending_debt)}</strong></p>
      <p>• Proximo IPC estimado: <strong class="text-honey">${summary.next_ipc.toFixed(4)}x</strong></p>
    </div>
  `;

  const btnConfirm = document.getElementById("btn-advance-month-confirm");
  const newBtnConfirm = btnConfirm.cloneNode(true);
  btnConfirm.parentNode.replaceChild(newBtnConfirm, btnConfirm);

  if (isGameOver && finalEvaluation) {
    newBtnConfirm.textContent = "Ver Evaluacion Final del Semestre (6 Meses) >>";
    newBtnConfirm.className = "btn btn-warning btn-block";
    newBtnConfirm.addEventListener("click", () => {
      dialog.close();
      showFinalEvaluationModal(finalEvaluation);
    });
  } else {
    newBtnConfirm.textContent = "Avanzar al Proximo Mes >>";
    newBtnConfirm.className = "btn btn-mint btn-block";
    newBtnConfirm.addEventListener("click", () => {
      dialog.close();
      fetchState();
    });
  }

  dialog.showModal();
}

function showFinalEvaluationModal(evaluation) {
  const dialog = document.getElementById("modal-final-summary");
  if (!dialog) return;

  const userBadge = document.getElementById("final-user-badge");
  if (userBadge) {
    userBadge.textContent = `Usuario: ${evaluation.username || 'prueba'}`;
  }

  // Banner de diagnostico
  const banner = document.getElementById("final-status-banner");
  let bannerClass = "final-status-banner";
  if (evaluation.status_code === "vulnerable") bannerClass += " is-vulnerable";
  if (evaluation.status_code === "critica") bannerClass += " is-critical";
  banner.className = bannerClass;

  banner.innerHTML = `
    <div>
      <div class="final-status-title">${evaluation.status_title}</div>
      <div class="final-status-sub">Simulacion semestral concluida (${evaluation.total_months} meses finalizados).</div>
    </div>
    <span class="badge ${evaluation.status_badge_class || 'badge-mint'}">${(evaluation.status_code || 'completado').toUpperCase()}</span>
  `;

  // Grilla de metricas acumuladas
  const metricsGrid = document.getElementById("final-metrics-grid");
  const netSavings = evaluation.final_cash - (evaluation.final_debt || 0);
  const netSavingsClass = netSavings >= 0 ? "text-mint" : "text-rose";

  metricsGrid.innerHTML = `
    <div class="final-metric-card">
      <span class="fmc-label">Efectivo Final</span>
      <strong class="fmc-val text-mint">${formatCurrency(evaluation.final_cash)}</strong>
      <span class="fmc-sub">Liquidez al cierre de mes 6</span>
    </div>
    <div class="final-metric-card">
      <span class="fmc-label">Deuda Bancaria</span>
      <strong class="fmc-val ${evaluation.final_debt > 0 ? 'text-rose' : 'text-muted'}">${formatCurrency(evaluation.final_debt)}</strong>
      <span class="fmc-sub">${evaluation.final_debt > 0 ? 'Descubierto pendiente' : 'Sin deuda bancaria'}</span>
    </div>
    <div class="final-metric-card">
      <span class="fmc-label">Patrimonio Neto</span>
      <strong class="fmc-val ${netSavingsClass}">${formatCurrency(netSavings)}</strong>
      <span class="fmc-sub">Ahorro neto acumulado</span>
    </div>
    <div class="final-metric-card">
      <span class="fmc-label">Bienestar Global</span>
      <strong class="fmc-val text-purple">${evaluation.final_utility.toFixed(1)} PTS</strong>
      <span class="fmc-sub">Utilidad acumulada total</span>
    </div>
    <div class="final-metric-card">
      <span class="fmc-label">Sueldos Percibidos</span>
      <strong class="fmc-val text-mint">${formatCurrency(evaluation.total_salary_earned)}</strong>
      <span class="fmc-sub">${evaluation.total_worked_days} dias trabajados</span>
    </div>
    <div class="final-metric-card">
      <span class="fmc-label">Costos Fijos Indexados</span>
      <strong class="fmc-val text-rose">${formatCurrency(evaluation.total_fixed_costs)}</strong>
      <span class="fmc-sub">Total 6 meses en Recoleta</span>
    </div>
    <div class="final-metric-card">
      <span class="fmc-label">Consumo y Estilo de Vida</span>
      <strong class="fmc-val text-honey">${formatCurrency(evaluation.total_discretionary_costs)}</strong>
      <span class="fmc-sub">Gastos cotidianos y ocio</span>
    </div>
    <div class="final-metric-card">
      <span class="fmc-label">Inflacion Acumulada</span>
      <strong class="fmc-val text-honey">${evaluation.final_ipc.toFixed(4)}x</strong>
      <span class="fmc-sub">+${evaluation.ipc_inflation_pct}% acumulado</span>
    </div>
  `;

  // Dictamen pedagogico
  document.getElementById("final-verdict-text").textContent = evaluation.tutor_verdict;

  // Tabla historica semestral
  const tableContainer = document.getElementById("final-history-table-container");
  const months = evaluation.months_summary || [];

  let tableHtml = `
    <table class="final-history-table">
      <thead>
        <tr>
          <th>Mes</th>
          <th>Nombre</th>
          <th>IPC</th>
          <th>Asistencia</th>
          <th>Horas Extras</th>
          <th>Sueldo Devengado</th>
          <th>Costos Fijos</th>
          <th>Consumo</th>
          <th>Saldo Cierre</th>
        </tr>
      </thead>
      <tbody>
  `;

  months.forEach(m => {
    tableHtml += `
      <tr>
        <td>Mes ${m.month}</td>
        <td>${m.month_name || ''}</td>
        <td>${m.ipc_month ? m.ipc_month.toFixed(4) + 'x' : '1.0000x'}</td>
        <td>${m.worked_days}/30</td>
        <td class="text-sky">+${formatCurrency(m.overtime_earned)}</td>
        <td class="text-mint">${formatCurrency(m.net_salary_liquidated)}</td>
        <td class="text-rose">${formatCurrency(m.total_fixed_cost)}</td>
        <td>${formatCurrency(m.total_discretionary_cost)}</td>
        <td class="text-mint"><strong>${formatCurrency(m.ending_cash)}</strong></td>
      </tr>
    `;
  });

  tableHtml += `
      </tbody>
    </table>
  `;

  tableContainer.innerHTML = tableHtml;

  const btnRestart = document.getElementById("btn-final-restart");
  if (btnRestart) {
    btnRestart.onclick = () => {
      dialog.close();
      resetGame();
    };
  }

  dialog.showModal();
}

async function resetGame() {
  try {
    transitStrikeOccurredThisMonth = false;
    await fetch("/api/reset", { method: "POST" });
    fetchState();
  } catch (err) {
    console.error("Error al reiniciar:", err);
  }
}

// -----------------------------------------------------------------------------
// 12. CAMBIO DE MODO: ESTANDAR VS ADMINISTRADOR (MODO DEMO DIA 28)
// -----------------------------------------------------------------------------
async function switchMode(targetMode, reload = false) {
  try {
    const res = await fetch("/api/admin/set_mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: targetMode, reload: Boolean(reload) })
    });
    const data = await res.json();
    if (data.success) {
      currentGameState = data.state;
      transitStrikeOccurredThisMonth = Boolean(data.state.transit_strike_occurred);
      renderDashboard(data.state);
      if (targetMode === "demo" && reload) {
        showNotificationDialog(
          "Modo Administrador Activado (prueba)",
          "Se ha cargado la simulacion en el Dia 28 de Agosto (Mes 6 de 6) para el usuario 'prueba'. Los primeros 5 meses se encuentran historizados. Tu partida estandar sigue intacta en memoria.",
          "Administrador"
        );
      }
    } else {
      showNotificationDialog("Error", data.error || "No se pudo cambiar de modo.", "Error");
    }
  } catch (err) {
    console.error("Error al cambiar de modo:", err);
  }
}
