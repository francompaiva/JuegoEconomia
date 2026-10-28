# Simulador de Supervivencia Economica (Web Life-Sim RPG & CLI)

Simulador interactivo desarrollado en Python y Flask con interfaz grafica estilo videojuego de simulacion de vida / RPG (HTML5, CSS3, JavaScript y Chart.js) y version de terminal (Rich CLI). Modela la toma de decisiones economicas bajo restriccion presupuestaria, el **Efecto Sustitucion** de la Teoria del Consumidor, shocks macroeconomicos de inflacion y dinamica de deuda con costo de oportunidad.

**Diseno Estructurado y HUD Gamificado**: Sin emojis. Toda la visualizacion se apoya en barras de estado (HUD), tarjetas interactivas de decision, estantes de sub-tarjetas desplegables, bordes neon y tipografia de videojuego.

---

## [1] Pilares de Jugabilidad y Diseno del HUD

### HUD Gamificado Superior
- **Barra de Presupuesto Disponible / Liquidez**: Monitorea el capital disponible y salud financiera. Si se entra en descubierto bancario, conmuta a alerta visual de deuda con desglose de tasas (`TNA 60%`, `TEM 5.00%`, `TEA 79.59%`).
- **Barra de Nivel de Bienestar / Utilidad**: Medidor de satisfaccion y energia del jugador acumulada a traves de sus elecciones de consumo y resolucion de formulas.
- **Barra de Progreso Mensual (Dias 1 a 30)**: Cronograma del mes con indicador de avance diario y tracking del `IPC Acumulado` e inflacion intermensual.

---

## [2] Mecanicas del Modelo Economico

### 1. Sistema de Trabajo e Ingresos Variables
- **Calendario Mensual**: Cada mes consta de 30 dias calendarios (horizonte de 6 meses).
- **Salario Base**: \$1.200.000,00 ARS (\$40.000,00 ARS por jornada diaria).
- **Dinamica de Asistencia**:
  - **Fichar y Trabajar (Trivia Financiera)**: El jugador responde una pregunta breve de economia/finanzas $\implies$ Dia trabajado (+salario devengado a liquidacion y bono de bienestar).
  - **No Asistir (Registrar Ausencia)**: Ausencia computada (descuento proporcional de \$40.000,00 a fin de mes e inhabilitacion de horas extras).
- **Horas Extras Condicionales**:
  - **Restriccion Estricta**: UNICAMENTE disponibles si el jugador asistio a trabajar ese dia. Si falto o no ficho, la terminal de horas extras permanece bloqueada (`[ACCESO DENEGADO]`).
  - **Mini-Juego Matematico**: Resolver formulas financieras con los numeros reales vigentes de la partida (TEM sobre descubierto, variacion de servicios por IPC, costo consolidado de luz/gas/agua, deduccion por ausencias, expensas indexadas).
  - Cada respuesta correcta acredita un bono salarial monetario para la liquidacion del mes.

### 2. Arbol de Decisiones de Consumo (Tarjetas Dinamicas de Estilo de Vida)
- **Tarjeta de Alimentacion y Gastronomia**:
  - `[COCINAR EN CASA]`: Opcion economica (\$95.000 * IPC, +45 pts Utilidad).
  - `[PEDIR DELIVERY]`: Despliega animadamente un estante de **Sub-Tarjetas de Menu**:
    * *Pizza Portena y Gaseosa* (\$180.000 * IPC, +80 pts Utilidad).
    * *Hamburguesa Artesanal y Cerveza* (\$220.000 * IPC, +100 pts Utilidad).
    * *Ensalada Gourmet y Vianda Fit* (\$150.000 * IPC, +70 pts Utilidad).
- **Tarjeta de Movilidad y Transporte**:
  - `[TRANSPORTE PUBLICO]` (Subte y Colectivo: \$35.000 * IPC) vs `[VIAJES PRIVADOS]` (se despliega en Sub-Tarjetas de *Uber / Cabify* o *Taxi / Remis*).
- **Tarjeta de Cuidado Personal**:
  - `[PELUQUERIA DE BARRIO]` vs `[LA SAGRADA BARBERIA / SALON VIP RECOLETA]`.
- **Tarjeta de Ocio y Salidas**:
  - `[STREAMING EN CASA]` vs `[SALIDAS Y BOLICHE]`.
- **Tarjeta de Mascotas (Perro y Gato)**:
  - `[ALIMENTO ESTANDAR]` vs `[SUPER PREMIUM Y GUARDERIA]`.

### 3. Gastos Fijos Obligatorios (Contratos Inmutables)
Ajustados mes a mes por el IPC:
- Alquiler Departamento (Recoleta): \$550.000,00
- Expensas: \$90.000,00
- Luz (Edesur): \$45.000,00
- Agua (AySA): \$25.000,00
- Gas (Metrogas): \$15.000,00
- Membresia Platino Plus (Megatlon): \$65.000,00
- Canasta Basica de Alimentos Indispensables: \$120.000,00

### 4. Tarjetas de Eventos Imprevistos (Pop-ups de Crisis)
- Aparicion aleatoria de emergencias financieras (consulta medica, arreglo del auto, plomeria urgente, urgencia veterinaria).
- Decisiones tacticas inmediatas:
  - **Pagar al Contado**: Debita el costo exacto indexado, preservando bienestar.
  - **Financiar con Tarjeta**: Aplica recargo financiero del 15% y mayor penalizacion en utilidad por estres financiero.

### 5. Motor de Inflacion Real y Shocks Macroeconomicos
- Indice de Precios al Consumidor (IPC) acumulado mes a mes.
- Shock macroeconomico aleatorio entre el mes 3 y 4 con impacto directo en todas las tarjetas de consumo y servicios basicos.

### 6. Deuda y Costo de Oportunidad
- Si el saldo al cierre del mes es deficitario, se activa automaticamente un prestamo en descubierto con tasa mensual:
  $$TNA = 60\% \implies TEM = 5\% \implies TEA \approx 79.59\%$$

### 7. Modo Administrador / Demostracion Semestral (Usuario "prueba")
- Selector de modo en cabecera (`Partida Estandar` vs `ADMINISTRADOR (prueba)`).
- Precarga historica completa de los primeros 5 meses para el usuario "prueba" (acumulando liquidaciones, gastos, eventos e inflacion por IPC).
- Posiciona la simulacion en el **Dia 28 de Agosto (Mes 6 de 6)** para experimentar los ultimos 2 dias y la evaluacion final consolidada del semestre sin alterar la partida normal en curso.

---

## [3] Como Ejecutar la Aplicacion Web

Para iniciar el servidor Flask con el HUD Gamificado y las Tarjetas Interactivas:

```bash
python app.py
```

Luego abre tu navegador en **http://localhost:5000** o **http://127.0.0.1:5000**.

*(Tambien puedes ejecutar la version clasica de terminal con `python main.py`).*

---

## [4] Suite de Pruebas Automatizadas (Pytest)

Ejecuta los 51 tests automatizados que verifican los calculos al centavo (`Decimal`, `ROUND_HALF_UP`), la liquidacion salarial, el arbol de consumo, el modo administrador semestral y los endpoints REST de la API:

```bash
pytest -v
```
