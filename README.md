# Simulador de Supervivencia Económica (Web & CLI)

Simulador interactivo desarrollado en Python y Flask con interfaz gráfica web (HTML5, CSS3, JavaScript y Chart.js) y versión de terminal (Rich CLI). Modela la toma de decisiones económicas bajo restricción presupuestaria, el **Efecto Sustitución** de la Teoría del Consumidor, shocks macroeconómicos de inflación y dinámica de deuda con costo de oportunidad.

---

## 📌 Mecánicas del Modelo Económico

### 1. Sistema de Trabajo e Ingresos Variables
- **Calendario Mensual**: Cada mes consta de 30 días calendarios (horizonte de 6 meses).
- **Salario Base**: \$1.200.000,00 ARS (\$40.000,00 ARS por día trabajado).
- **Dinámica de Asistencia**:
  - Si el jugador responde el **Mini-Juego Diario (Jornada Laboral)** de economía y finanzas $\implies$ Día trabajado (+salario devengado).
  - Si no trabaja o saltea el día $\implies$ Ausencia (se descuenta proporcionalmente a fin de mes: \$40.000 por falta).
- **Horas Extras Opcionales**:
  - Desafíos matemáticos/financieros que utilizan los **números reales y vigentes** de la partida (calcular TEM desde TNA, variación de servicios por IPC, suma consolidada de tarifas, etc.).
  - Cada fórmula resuelta otorga un bono monetario que se adiciona a la liquidación del mes.

### 2. Clasificación de Gastos y Estilo de Vida
- **Gastos Fijos Obligatorios** (ajustados progresivamente por IPC):
  - Alquiler en Recoleta: \$550.000,00
  - Expensas: \$90.000,00
  - Luz (Edesur): \$45.000,00
  - Agua (AySA): \$25.000,00
  - Gas (Metrogas): \$15.000,00
  - Canasta Básica de Alimentos: \$120.000,00
- **Gastos Discrecionales (Ocio y Estilo de Vida)**:
  - Salidas, restaurantes, delivery, ropa y entretenimiento (Teoría del Consumidor: disyuntiva entre mayor utilidad o mayor ahorro).
- **Eventualidades e Imprevistos**:
  - Eventos emergentes aleatorios (consultas médicas, reparaciones de auto, arreglos del hogar).

### 3. Motor de Inflación Real
- Índice de Precios al Consumidor (IPC) acumulado mes a mes.
- Evento de shock inflacionario aleatorio entre el mes 3 y 4 con impacto directo en precios básicos y tarifas.

### 4. Deuda y Costo de Oportunidad
- Si el saldo final de mes es negativo, se activa un préstamo automático en descubierto con tasa mensual fija ($TNA = 60\% \implies TEM = 5\% \implies TEA \approx 79.59\%$).

---

## 🚀 Cómo Ejecutar la Aplicación Web

Para iniciar el servidor Flask con el Dashboard Gráfico interactivo:

```bash
python app.py
```

Luego abre tu navegador en **http://localhost:5000** o **http://127.0.0.1:5000**.

*(También puedes ejecutar la versión clásica de terminal con `python main.py`).*

---

## 🧪 Suite de Pruebas Automatizadas (Pytest)

Ejecuta los 34 unit tests que verifican los cálculos al centavo (`Decimal`) y los endpoints de la API:

```bash
python -m pytest
```
