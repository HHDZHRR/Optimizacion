## 1. Cómo funciona el algoritmo

El algoritmo es **GRASP** (*Greedy Randomized Adaptive Search Procedure*), una metaheurística de dos fases que se repite múltiples veces. Para este problema (MTVRP), el objetivo es **minimizar la latencia total** — la suma de los tiempos de llegada a cada cliente desde el inicio de la operación.

El ciclo completo en `solve_mtvrp_grasp` (línea 165) es:

```
Para cada iteración (50 veces):
  1. CONSTRUCCIÓN  → grasp_constructive()   → genera una solución nueva semi-aleatoria
  2. MEJORA        → local_search()          → intenta mejorar esa solución por intercambios
  3. REORDENACIÓN  → reorder_routes()        → reordena los viajes para reducir latencia
  4. COMPARACIÓN   → si es la mejor hasta ahora, guardarla
```

Después de las 50 iteraciones, se devuelve la mejor solución encontrada. Esto se repite **5 veces** (una por cada valor de alpha), y al final se reportan estadísticas comparativas.

---

## 2. Cuántas veces se repite cada parte

La estructura de ejecución completa para **una instancia** es:

```
main()
└── para cada alpha en [1, 2, 3, 5, 7]          → 5 réplicas
    └── solve_mtvrp_grasp(iterations=50)
        └── para cada iteración (50 veces)
            ├── grasp_constructive()             → se ejecuta 50 veces por réplica
            ├── local_search()                   → se ejecuta 50 veces por réplica
            │   └── while improved:             → se repite hasta no mejorar (variable)
            │       └── para cada par (i,j)     → O(n²) evaluaciones por pasada
            └── reorder_routes()                 → se ejecuta 50 veces por réplica
```

**Total de llamadas a `grasp_constructive` por instancia:** 5 alphas × 50 iteraciones = **250 construcciones**

**Total de llamadas a `local_search` por instancia:** 5 × 50 = **250 búsquedas locales**

---

## 3. Parámetros que tú puedes modificar manualmente

Todos están al inicio de `main()` o como argumentos de `solve_mtvrp_grasp`:

| Parámetro | Línea | Qué controla |
|---|---|---|
| `ALPHA_VALUES` | línea 188 | Lista de valores de alpha (tamaño RCL) a probar. Puedes agregar, quitar o cambiar valores: `[1, 3, 5]`, `[2, 4, 6, 8]`, etc. |
| `iterations=50` | línea 234 | Cuántas veces se repite el ciclo Construir+Mejorar dentro de cada réplica. Más = mejor calidad, más tiempo. |
| `folder_path` | línea 187 | Carpeta donde están las instancias. |

Si usas `app.py`, también puedes mover los sliders de la interfaz:
- **Iterations** (slider, línea 229 de app.py) — equivale al `iterations=50`
- **RCL Size (alpha)** (slider, línea 243 de app.py) — solo aplica al modo Single Instance

---

## 4. Parámetros que el código ajusta automáticamente

| Parámetro | Dónde se calcula | Descripción |
|---|---|---|
| `beta` | línea 104 | Se recalcula en cada paso de construcción: `beta = (carga_actual + demanda_candidato) / capacidad`. Penaliza más el tiempo de regreso cuando el vehículo está casi lleno. |
| `score` | línea 105 | Combina distancia y penalización: `score = dist + beta * tiempo_regreso`. El código lo genera dinámicamente para cada candidato en cada paso. |
| `NUM_REPLICATIONS` | línea 189 | Se deriva automáticamente del tamaño de `ALPHA_VALUES`: `len(ALPHA_VALUES)`. Si agregas un alpha, las réplicas suben solas. |
| `best_alpha` | línea 228-241 | Se actualiza automáticamente al final de cada réplica si esa fue la mejor solución. |
| Número de rutas (vehículos) | dentro de `grasp_constructive` | No es un parámetro: el algoritmo abre un nuevo vehículo cuando ningún cliente cabe en el actual (líneas 121-127). |

---

## 5. ¿Usamos alpha o k para la RCL?

El código usa **alpha**. En la literatura GRASP se usan dos convenciones:

- **Enfoque por cardinalidad (el que usamos):** se toman los `alpha` mejores candidatos y se elige uno al azar. `alpha` = número fijo de candidatos en la lista.
- **Enfoque por umbral (parámetro `α` numérico 0-1):** un candidato entra si su costo ≤ c_min + α·(c_max − c_min).

Nuestro código usa **cardinalidad fija**:

```111:112:c:\Users\manum\Documents\College\TSO\optimizacion-pia\mtvrp_solver.py
            rcl = candidates[:alpha]
            chosen = random.choice(rcl)
```

`alpha=1` → totalmente greedy (siempre el mejor). `alpha` grande → más aleatorio. Los valores probados son `[1, 2, 3, 5, 7]`.

---

## 6. El movimiento de la búsqueda local: **swap intra-ruta**

El movimiento se llama **2-opt swap** o **intercambio de posiciones dentro de la misma ruta**. Dado una ruta como:

```
[0, A, B, C, D, E, 0]
```

Se prueban todos los pares de posiciones `(i, j)` con `i < j` (sin tocar el depósito en posición 0 y última):

```
Probar intercambiar A↔C:  [0, C, B, A, D, E, 0]
Probar intercambiar A↔D:  [0, D, B, C, A, E, 0]
Probar intercambiar B↔E:  [0, A, E, C, D, B, 0]
... y así para todos los pares
```

El código hace el swap **en el lugar** (in-place), evalúa la latencia, y si no mejoró, **revierte el swap**:

```148:158:c:\Users\manum\Documents\College\TSO\optimizacion-pia\mtvrp_solver.py
                    # Swap in-place
                    route[i], route[j] = route[j], route[i]
                    
                    new_latency = calculate_latency(best_routes, dist_matrix)
                    if new_latency < best_latency:
                        best_latency = new_latency
                        improved = True
                        break
                    else:
                        # Revert swap in-place
                        route[i], route[j] = route[j], route[i]
```

**Importante:** la estrategia de aceptación es **first improvement** — en cuanto encuentra un swap que mejora, lo acepta inmediatamente y reinicia la búsqueda desde el principio (no sigue probando todos los pares). Esto es más rápido que *best improvement* (probar todos y elegir el mejor), pero puede perderse mejoras mayores.

---

## 7. Cómo se obtienen los vecinos en la búsqueda local

Los vecinos de una solución son **todas las soluciones obtenibles aplicando exactamente un swap intra-ruta**. Para una ruta con `k` clientes (sin contar el depósito), el número de vecinos posibles por ruta es:

\[
\binom{k}{2} = \frac{k(k-1)}{2}
\]

El vecindario total es la unión de los vecinos de todas las rutas. Los vecinos **entre rutas distintas no se exploran** — el código solo hace swaps dentro de la misma ruta (intra-route). No hay movimientos inter-ruta como relocate o cross-exchange.

---

## 8. Cómo se obtiene la primera solución

La primera solución se genera en `grasp_constructive` (línea 83). Es una construcción **greedy aleatorizada**:

**Paso a paso:**

1. Se parte del depósito (nodo 0) con el vehículo vacío.
2. Para cada posición de la ruta se evalúan **todos los clientes no visitados** que:
   - Caben en la capacidad restante del vehículo: `carga_actual + demanda ≤ capacidad`
   - Permiten regresar al depósito a tiempo: `tiempo_ruta + dist + tiempo_regreso ≤ max_time`
3. A cada candidato válido se le calcula un **score dinámico**:
   ```
   beta = (carga_actual + demanda_candidato) / capacidad
   score = distancia_al_candidato + beta × distancia_candidato_al_depósito
   ```
   Esto premia a candidatos cercanos, pero también penaliza rutas que dejarían al vehículo muy lleno lejos del depósito.
4. Se ordenan los candidatos por score (menor = mejor) y se toman los `alpha` mejores → **esa es la RCL**.
5. Se elige **uno al azar** de la RCL. Aquí está la aleatoriedad del GRASP.
6. Si ningún cliente cabe en el vehículo actual, se cierra la ruta (`→ 0`) y se abre un nuevo vehículo.
7. Se repite hasta que todos los clientes estén asignados.

El resultado es una solución **diferente en cada iteración** gracias al paso 5.

---

## 9. Qué es el Tiempo Promedio y qué tiempos se promedian

```231:236:c:\Users\manum\Documents\College\TSO\optimizacion-pia\mtvrp_solver.py
                for alpha in ALPHA_VALUES:
                    t0 = time.time()
                    routes, latency = solve_mtvrp_grasp(
                        nodes, demands, capacity, max_time, dist_matrix,
                        iterations=50, alpha=alpha
                    )
                    times.append(time.time() - t0)
```

Cada elemento de la lista `times` es el **tiempo completo de una llamada a `solve_mtvrp_grasp`**, es decir, el tiempo que tardaron las 50 iteraciones (construcción + búsqueda local + reordenación) para un alpha específico.

El **Tiempo Promedio** es:

\[
\text{Tiempo Promedio} = \frac{t_{\alpha=1} + t_{\alpha=2} + t_{\alpha=3} + t_{\alpha=5} + t_{\alpha=7}}{5}
\]

Son exactamente **5 tiempos** (uno por réplica/alpha) los que se promedian. No es el tiempo por iteración ni por construcción individual.

---

## 10. Qué es el Número de Réplicas

```188:189:c:\Users\manum\Documents\College\TSO\optimizacion-pia\mtvrp_solver.py
    ALPHA_VALUES    = [1, 2, 3, 5, 7]
    NUM_REPLICATIONS = len(ALPHA_VALUES)   # una réplica por cada valor de alpha
```

Una **réplica** es una ejecución completa de `solve_mtvrp_grasp` (50 iteraciones GRASP) con un valor de alpha fijo. Como hay 5 valores de alpha, hay **5 réplicas por instancia**.

El propósito de las réplicas es poder reportar **variabilidad estadística**: si todas las réplicas dan la misma latencia, el algoritmo es estable; si hay mucha diferencia entre Mejor Valor y Peor Valor, es sensible al alpha o a la aleatoriedad.

> En terminología experimental: la réplica es la **unidad de observación** para calcular mejor, promedio y peor.

---

## 11. Datos importantes que un maestro universitario podría preguntar

**Sobre la función objetivo:**
- La función objetivo no es la *distancia total recorrida* sino la **latencia total** (suma de tiempos de llegada a cada cliente). La diferencia conceptual es importante: puedes recorrer más distancia pero atender antes a más clientes, obteniendo menor latencia.
- El reloj `global_time` **no se reinicia entre vehículos** (línea 54). Todos los clientes perciben el tiempo desde el mismo instante, sin importar en qué vehículo viajan. Esto refleja el modelo de latencia verdadero.

**Sobre GRASP:**
- GRASP **no garantiza encontrar el óptimo global**. Es una metaheurística: da buenas soluciones en tiempo razonable, pero no hay prueba de optimalidad.
- El parámetro alpha controla el balance **exploración vs. explotación**: alpha=1 es completamente greedy (explota), alpha grande es casi aleatorio (explora). Probar varios alphas es una forma de calibrar ese balance.

**Sobre la búsqueda local:**
- Solo se hacen movimientos **intra-ruta** (dentro del mismo vehículo). No se exploran movimientos como mover un cliente de un vehículo a otro (*relocate*) o intercambiar clientes entre dos vehículos (*cross-exchange*). Esto limita la calidad del óptimo local alcanzado.
- La estrategia es **first improvement**, no *best improvement*. Ambas convergen a un óptimo local, pero con distinta velocidad y calidad.

**Sobre `reorder_routes`:**
- Después de la búsqueda local se ejecuta `reorder_routes` (línea 71), que ordena los viajes de menor a mayor ratio `duración/clientes`. Esto pone primero los viajes más cortos por cliente, reduciendo la latencia acumulada sin cambiar las rutas en sí. Es una **mejora de post-procesamiento** específica del modelo de latencia (no serviría para minimizar distancia total).

**Sobre complejidad:**
- La fase constructiva es O(n²) por solución (n clientes × evaluar n candidatos en cada paso).
- La búsqueda local es O(n²) por pasada del `while`, y puede haber múltiples pasadas.
- El algoritmo completo es O(iteraciones × n²) por réplica, y O(réplicas × iteraciones × n²) en total.

**Sobre la aleatoriedad:**
- Si corres el programa dos veces seguidas sobre la misma instancia, obtendrás resultados ligeramente diferentes porque `random.choice` es no determinístico. Para reproducibilidad se puede fijar `random.seed(42)` al inicio.