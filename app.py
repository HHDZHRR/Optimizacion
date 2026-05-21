import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import os
import time


# Import optimized solver functions
from mtvrp_solver import parse_instance, solve_mtvrp_grasp, route_duration

# Premium page config
st.set_page_config(
    page_title="MHOAR Solutions - MTVRP Latency Solver",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Style Sheet
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .header-container {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 35px;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        margin-bottom: 30px;
        border: 1px solid rgba(255,255,255,0.1);
        position: relative;
        overflow: hidden;
    }
    
    .header-badge {
        background: rgba(255,255,255,0.15);
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1.5px;
        display: inline-block;
        margin-bottom: 12px;
        text-transform: uppercase;
    }
    
    .header-title {
        font-size: 40px;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
        line-height: 1.1;
    }
    
    .header-subtitle {
        font-size: 17px;
        font-weight: 300;
        color: #d1d8e0;
        margin-top: 6px;
    }
    
    .metric-card {
        background: rgba(30, 33, 48, 0.5);
        backdrop-filter: blur(12px);
        padding: 24px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
        transition: transform 0.3s ease, border-color 0.3s ease;
        margin-bottom: 15px;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: rgba(0, 210, 255, 0.5);
    }
    
    .metric-title {
        font-size: 12px;
        font-weight: 600;
        color: #a5b1c2;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }
    
    .metric-value {
        font-size: 36px;
        font-weight: 800;
    }
    
    .value-latency {
        background: linear-gradient(120deg, #00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .value-time {
        background: linear-gradient(120deg, #f093fb, #f5576c);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .value-trips {
        background: linear-gradient(120deg, #f6d365, #fda085);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .trip-card {
        background: rgba(45, 52, 82, 0.3);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 5px;
        border-left: 5px solid #00d2ff;
        border-top: 1px solid rgba(255,255,255,0.05);
        border-right: 1px solid rgba(255,255,255,0.05);
        border-bottom: 1px solid rgba(255,255,255,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Main Banner Header
st.markdown("""
<div class="header-container">
    <div class="header-badge">🚀 GRASP METAHEURISTIC</div>
    <div class="header-title">MHOAR Solutions Dashboard</div>
    <div class="header-subtitle">Multi-Trip Vehicle Routing Problem with Minimum Latency Optimization</div>
</div>
""", unsafe_allow_html=True)

# Sidebar configurations
st.sidebar.header("⚙️ Solver Configuration")

folder_path = "./instancias"
if not os.path.exists(folder_path):
    st.sidebar.error(f"Folder '{folder_path}' not found.")
    st.stop()

# Get available instance files
files = [f for f in os.listdir(folder_path) if f.endswith(".txt") or f.endswith(".TXT")]
files.sort()

if not files:
    st.sidebar.error("No .txt files found in folder 'instancias'")
    st.stop()

# Selection mode
mode = st.sidebar.radio("Execution Mode", ["Single Instance", "Batch (All Instances)"])

selected_file = None
if mode == "Single Instance":
    selected_file = st.sidebar.selectbox("Select an Instance", files)

# Solver Hyperparameters
st.sidebar.subheader("GRASP Parameters")
iterations = st.sidebar.slider("Number of Iterations", min_value=10, max_value=200, value=100, step=10)
alpha = st.sidebar.slider("RCL Size (alpha)", min_value=1, max_value=5, value=3, step=1)

# Start button
start_button = st.sidebar.button("🚀 Start Optimization", use_container_width=True)

# Main container
if start_button:
    if mode == "Single Instance" and selected_file:
        filepath = os.path.join(folder_path, selected_file)
        
        with st.spinner(f"Optimizing {selected_file}..."):
            start_time = time.time()
            nodes, demands, capacity, max_time, dist_matrix = parse_instance(filepath)
            routes, latency = solve_mtvrp_grasp(nodes, demands, capacity, max_time, dist_matrix, iterations=iterations)
            exec_time = time.time() - start_time
            
        st.success(f"Optimization of {selected_file} successfully completed!")
        
        # Dashboard columns with custom glass cards
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Best Total Latency</div>
                <div class="metric-value value-latency">{latency:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Execution Time</div>
                <div class="metric-value value-time">{exec_time:.4f} s</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Trips Required</div>
                <div class="metric-value value-trips">{len(routes)}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Side-by-Side Layout
        col_left, col_right = st.columns([3, 2])
        
        with col_left:
            # Check if there are valid coordinates to plot
            has_coordinates = any(coord != (0,0) for coord in list(nodes.values())[1:])
            
            if has_coordinates:
                st.subheader("🗺️ Route Map Visualization")
                
                # Matplotlib visualization with premium styling
                fig, ax = plt.subplots(figsize=(10, 7.5))
                fig.patch.set_facecolor('#0e1117')
                ax.set_facecolor('#1a1c24')
                
                # Plot Depot (Large golden glowing star)
                depot_x, depot_y = nodes[0]
                ax.scatter(depot_x, depot_y, color='#ffd700', marker='*', s=450, edgecolor='#ffffff', linewidth=1.5, label='Depot (0)', zorder=6)
                
                # Plot Clients (Neon blue circles with white border)
                client_x = [nodes[i][0] for i in nodes if i != 0]
                client_y = [nodes[i][1] for i in nodes if i != 0]
                ax.scatter(client_x, client_y, color='#00d2ff', marker='o', s=130, edgecolor='#ffffff', linewidth=0.8, alpha=0.9, label='Clients', zorder=3)
                
                # Text labels for coordinates
                for node_id, (x, y) in nodes.items():
                    if node_id == 0:
                        ax.annotate("DEPOT", (x, y), textcoords="offset points", xytext=(0,-18), ha='center', fontweight='bold', color='#ffd700', fontsize=10)
                    else:
                        ax.annotate(str(node_id), (x, y), textcoords="offset points", xytext=(0,6), ha='center', fontsize=9, color='#ffffff', fontweight='semibold')
                
                # Distinct palette for routes (Neon brights)
                colors = ['#38ef7d', '#00c6ff', '#f093fb', '#ff9f43', '#ff6b6b', '#10ac84', '#00d2d3', '#a55eea', '#ff78cb', '#48dbfb']
                
                for idx, route in enumerate(routes):
                    color = colors[idx % len(colors)]
                    xs = [nodes[n][0] for n in route]
                    ys = [nodes[n][1] for n in route]
                    
                    # Plot path with smooth linewidth and slight transparency
                    ax.plot(xs, ys, color=color, linestyle='-', linewidth=2.8, alpha=0.85, label=f'Trip {idx+1}', zorder=2)
                    
                    # Add arrow directions
                    for i in range(len(route) - 1):
                        start = nodes[route[i]]
                        end = nodes[route[i+1]]
                        ax.annotate('', xy=end, xytext=start,
                                    arrowprops=dict(arrowstyle="-|>", color=color, lw=2.0, ls='-', mutation_scale=12),
                                    zorder=2)
                
                # Styling plot axes
                ax.set_xlabel("X Coordinate", color='#a5b1c2', fontsize=10)
                ax.set_ylabel("Y Coordinate", color='#a5b1c2', fontsize=10)
                ax.tick_params(colors='#a5b1c2', labelsize=9)
                ax.grid(True, linestyle='--', alpha=0.2, color='#ffffff')
                
                # Legend placement and background
                legend = ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', framealpha=0.1, facecolor='#0e1117', edgecolor='#ffffff')
                for text in legend.get_texts():
                    text.set_color("white")
                    text.set_fontsize(9)
                
                st.pyplot(fig)
            else:
                st.warning("⚠️ This instance is based on travel time matrices and does not contain 2D coordinates for routing plot.")
                
        with col_right:
            st.subheader("📋 Detailed Trip Breakdown")
            
            for idx, route in enumerate(routes):
                trip_load = sum(demands[node] for node in route)
                load_pct = trip_load / capacity
                dur = route_duration(route, dist_matrix)
                route_str = " ➔ ".join(str(n) for n in route)
                
                # Neon colored indicators per trip card
                trip_colors = ['#38ef7d', '#00c6ff', '#f093fb', '#ff9f43', '#ff6b6b']
                border_color = trip_colors[idx % len(trip_colors)]
                
                st.markdown(f"""
                <div class="trip-card" style="border-left-color: {border_color}; margin-top: 10px;">
                    <div style="font-weight: bold; font-size: 16px; color: {border_color}; margin-bottom: 6px;">Trip {idx+1}</div>
                    <div style="font-family: monospace; font-size: 13px; color: #ffffff; background-color: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px; margin-bottom: 12px;">{route_str}</div>
                    <div style="display: flex; justify-content: space-between; font-size: 13px; color: #a5b1c2; margin-bottom: 4px;">
                        <span>⏱️ Duration: <b>{dur:.2f}</b></span>
                        <span>⚖️ Load: <b>{trip_load:.1f} / {capacity:.1f}</b> ({load_pct*100:.0f}%)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                # Render Streamlit progress bar to match the capacity percentage
                st.progress(min(load_pct, 1.0))
            
    elif mode == "Batch (All Instances)":
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for index, filename in enumerate(files):
            status_text.text(f"Solving ({index+1}/{len(files)}): {filename}...")
            filepath = os.path.join(folder_path, filename)
            
            start_time = time.time()
            nodes, demands, capacity, max_time, dist_matrix = parse_instance(filepath)
            num_clients = len(nodes) - 1
            
            routes, latency = solve_mtvrp_grasp(nodes, demands, capacity, max_time, dist_matrix, iterations=iterations)
            exec_time = time.time() - start_time
            
            results.append({
                "Instance": filename,
                "Number of clients": num_clients,
                "Vehicle capacity": capacity,
                "Best Latency": round(latency, 2),
                "Execution time (s)": round(exec_time, 4)
            })
            progress_bar.progress((index + 1) / len(files))
            
        status_text.text("All instances successfully solved!")
        
        # Display summary table
        df_results = pd.DataFrame(results)
        df_results.index = df_results.index + 1
        st.subheader("General Results Table")
        st.dataframe(df_results, use_container_width=True)
        
        # Download buttons
        csv = df_results.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name="resultados_mtvrp_grasp.csv",
            mime="text/csv",
            use_container_width=True
        )
else:
    st.info("👈 Adjust the parameters in the left sidebar and click **Start Optimization** to begin.")
