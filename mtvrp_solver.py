import os
import math
import re
import time
import random

def calculate_distance(node1, node2):
    return math.sqrt((node1[0] - node2[0])**2 + (node1[1] - node2[1])**2)

def parse_instance(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    match_cap = re.search(r'VehCapacity:?\s*(\d+)', content)
    capacity = float(match_cap.group(1)) if match_cap else 0

    demands = {0: 0.0}
    match_demands = re.search(r'ClientDemands:\s*\n([0-9\s]+)\nServiceTimes:', content)
    if match_demands:
        demands_list = [float(x) for x in match_demands.group(1).split()]
        for i, d in enumerate(demands_list):
            demands[i+1] = d

    nodes = {}
    dist_matrix = {}

    if 'CoorX' in content and 'CoorY' in content:
        coor_str = content.split('CoorY')[1].strip()
        lines = [line.strip() for line in coor_str.split('\n') if line.strip()]
        for i, line in enumerate(lines):
            parts = line.split()
            nodes[i] = (float(parts[0]), float(parts[1]))
            
        for i in nodes:
            dist_matrix[i] = {}
            for j in nodes:
                dist_matrix[i][j] = calculate_distance(nodes[i], nodes[j])
                
    elif 'TravelTimes:' in content:
        matrix_str = content.split('TravelTimes:')[1].strip()
        lines = [line.strip() for line in matrix_str.split('\n') if line.strip()]
        for i, line in enumerate(lines):
            parts = line.split()
            dist_matrix[i] = {}
            for j, val in enumerate(parts):
                dist_matrix[i][j] = float(val)
        nodes = {i: (0,0) for i in range(len(lines))}

    return nodes, demands, capacity, float('inf'), dist_matrix

def calculate_latency(routes, dist_matrix):
    """Calcula la latencia total de una solución (suma de tiempos de espera)"""
    total_latency = 0
    global_time = 0
    for route in routes:
        for i in range(len(route) - 1):
            curr_node = route[i]
            next_node = route[i+1]
            dist = dist_matrix[curr_node][next_node]
            global_time += dist
            if next_node != 0:
                total_latency += global_time
    return total_latency

def route_duration(route, dist_matrix):
    d = 0
    for i in range(len(route) - 1):
        d += dist_matrix[route[i]][route[i+1]]
    return d

def reorder_routes(routes, dist_matrix):
    route_info = []
    for r in routes:
        clients_count = len(r) - 2
        if clients_count <= 0:
            continue
        dur = route_duration(r, dist_matrix)
        ratio = dur / clients_count
        route_info.append((ratio, r))
    route_info.sort(key=lambda x: x[0])
    return [r for _, r in route_info]

def grasp_constructive(nodes, demands, capacity, max_time, dist_matrix, alpha=3):
    """Fase 1: Construcción Aleatorizada Golosa"""
    unvisited = set(nodes.keys())
    unvisited.remove(0)
    
    routes = []
    current_route = [0]
    current_load = 0
    current_route_time = 0
    current_node = 0
    
    while unvisited:
        candidates = []
        for candidate in unvisited:
            dist = dist_matrix[current_node][candidate]
            demand_fits = (current_load + demands[candidate]) <= capacity
            time_to_return = dist_matrix[candidate][0]
            time_fits = (current_route_time + dist + time_to_return) <= max_time
            
            if demand_fits and time_fits:
                # Dynamic beta parameter based on load fullness
                beta = (current_load + demands[candidate]) / capacity
                score = dist + beta * time_to_return
                candidates.append((score, candidate))
        
        if candidates:
            # RCL: Tomamos los 'alpha' mejores candidatos y elegimos uno al azar
            candidates.sort(key=lambda x: x[0])
            rcl = candidates[:alpha]
            chosen = random.choice(rcl)
            best_score, best_next_node = chosen
            
            best_dist = dist_matrix[current_node][best_next_node]
            current_route.append(best_next_node)
            unvisited.remove(best_next_node)
            current_load += demands[best_next_node]
            current_route_time += best_dist
            current_node = best_next_node
        else:
            current_route.append(0)
            routes.append(current_route)
            current_route = [0]
            current_load = 0
            current_route_time = 0
            current_node = 0

    if current_route[-1] != 0:
        current_route.append(0)
        routes.append(current_route)
        
    return routes

def local_search(routes, dist_matrix):
    """Fase 2: Búsqueda Local (Mejora intercambiando clientes en la misma ruta en el lugar)"""
    improved = True
    best_routes = [r[:] for r in routes]
    best_latency = calculate_latency(best_routes, dist_matrix)
    
    while improved:
        improved = False
        for r_idx in range(len(best_routes)):
            route = best_routes[r_idx]
            # Intentar intercambiar posiciones de dos clientes (i, j) en el viaje
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
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
                if improved:
                    break
            if improved:
                break
    return best_routes, best_latency

def solve_mtvrp_grasp(nodes, demands, capacity, max_time, dist_matrix, iterations=50, alpha=3):
    """Metodología GRASP Completa"""
    best_overall_routes = None
    best_overall_latency = float('inf')
    
    for _ in range(iterations):
        # 1. Construir
        routes = grasp_constructive(nodes, demands, capacity, max_time, dist_matrix, alpha=alpha)
        # 2. Mejorar
        improved_routes, _ = local_search(routes, dist_matrix)
        # 3. Reordenar rutas para minimizar latencia secuencial
        sorted_routes = reorder_routes(improved_routes, dist_matrix)
        sorted_latency = calculate_latency(sorted_routes, dist_matrix)
        
        # 4. Guardar la mejor
        if sorted_latency < best_overall_latency:
            best_overall_latency = sorted_latency
            best_overall_routes = sorted_routes
            
    return best_overall_routes, best_overall_latency

def main():
    folder_path = "./instancias"
    ALPHA_VALUES    = [1, 2, 3, 5, 7]
    NUM_REPLICATIONS = len(ALPHA_VALUES)   # una réplica por cada valor de alpha

    if not os.path.exists(folder_path):
        print(f"Crea la carpeta '{folder_path}' y coloca las instancias ahí.")
        return

    col_inst     = 22
    col_best_val = 22
    col_avg_val  = 16
    col_worst    = 14
    col_time     = 18
    col_reps     = 20
    col_config   = 20

    header = (
        f"{'Instancia':<{col_inst}} | "
        f"{'Mejor Valor Enc.':<{col_best_val}} | "
        f"{'Valor Promedio':<{col_avg_val}} | "
        f"{'Peor Valor':<{col_worst}} | "
        f"{'Tiempo Promedio (s)':<{col_time}} | "
        f"{'Num. de Replicas':<{col_reps}} | "
        f"{'Mejor Config. (alpha)':<{col_config}}"
    )
    print("\n")
    print(header)
    print("-" * len(header))

    all_best_routes = {}

    for filename in os.listdir(folder_path):
        if filename.endswith(".txt") or filename.endswith(".TXT"):
            filepath = os.path.join(folder_path, filename)
            try:
                nodes, demands, capacity, max_time, dist_matrix = parse_instance(filepath)

                latencies   = []
                times       = []
                best_routes = None
                best_latency = float('inf')
                best_alpha   = None

                for alpha in ALPHA_VALUES:
                    t0 = time.time()
                    routes, latency = solve_mtvrp_grasp(
                        nodes, demands, capacity, max_time, dist_matrix,
                        iterations=50, alpha=alpha
                    )
                    times.append(time.time() - t0)
                    latencies.append(latency)
                    if latency < best_latency:
                        best_latency = latency
                        best_routes  = routes
                        best_alpha   = alpha

                best_val  = min(latencies)
                avg_val   = sum(latencies) / len(latencies)
                worst_val = max(latencies)
                avg_time  = sum(times) / len(times)

                print(
                    f"{filename:<{col_inst}} | "
                    f"{best_val:<{col_best_val}.2f} | "
                    f"{avg_val:<{col_avg_val}.2f} | "
                    f"{worst_val:<{col_worst}.2f} | "
                    f"{avg_time:<{col_time}.4f} | "
                    f"{NUM_REPLICATIONS:<{col_reps}} | "
                    f"{best_alpha:<{col_config}}"
                )
                all_best_routes[filename] = best_routes

            except Exception as e:
                print(f"{filename:<{col_inst}} | ERROR AL LEER: {e}")

    print("\n")
    print("=" * len(header))
    print("DETALLE DE RUTAS POR INSTANCIA (MEJOR SOLUCION)")
    print("=" * len(header))
    for filename, routes in all_best_routes.items():
        print(f"\nInstancia: {filename}")
        for idx, route in enumerate(routes):
            route_str = " -> ".join(str(n) for n in route)
            print(f"  Viaje {idx + 1}: {route_str}")

    print("\n")

if __name__ == "__main__":
    main()