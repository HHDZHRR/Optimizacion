"""
MHOAR Solutions - MTVRP Latency Solver
Desktop GUI Application (tkinter + matplotlib)
"""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from mtvrp_solver import parse_instance, solve_mtvrp_grasp, route_duration

# ─── Color Palette ────────────────────────────────────────────────────────────
BG_DARK       = "#090d16"  # Slightly darker for higher contrast
BG_CARD       = "#111622"  # Deep dark navy-blue card background
BG_SIDEBAR    = "#0c0f17"  # Dark sidebar background
BG_INPUT      = "#1b2234"
FG_PRIMARY    = "#ffffff"
FG_SECONDARY  = "#8e9bb0"  # Slightly brighter secondary text
ACCENT_BLUE   = "#00c6ff"
ACCENT_PINK   = "#f093fb"
ACCENT_ORANGE = "#fda085"
ACCENT_GREEN  = "#38ef7d"
BORDER_COLOR  = "#1f2a45"  # Slightly brighter border for crisp cards
HEADER_GRAD1  = "#112755"  # Sleek dark blue
HEADER_GRAD2  = "#075487"  # Glowing blue
NEON_COLORS   = ['#38ef7d', '#00c6ff', '#f093fb', '#ff9f43', '#ff6b6b',
                 '#10ac84', '#00d2d3', '#a55eea', '#ff78cb', '#48dbfb']


class GradientCanvas(tk.Canvas):
    """Custom Canvas to render a smooth horizontal linear gradient."""
    def __init__(self, parent, color1, color2, **kwargs):
        super().__init__(parent, highlightthickness=0, **kwargs)
        self.color1 = color1
        self.color2 = color2
        self.bind("<Configure>", self.draw_gradient)

    def draw_gradient(self, event=None):
        self.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 0 or height <= 0:
            return

        r1, g1, b1 = self.winfo_rgb(self.color1)
        r2, g2, b2 = self.winfo_rgb(self.color2)
        r1, g1, b1 = r1 >> 8, g1 >> 8, b1 >> 8
        r2, g2, b2 = r2 >> 8, g2 >> 8, b2 >> 8

        # Draw columns
        step = 4
        for x in range(0, width, step):
            t = x / width
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            color = f"#{r:02x}{g:02x}{b:02x}"
            self.create_rectangle(x, 0, x + step, height, fill=color, outline="", tags="gradient")
        self.tag_lower("gradient")


class MTVRPDesktopApp(tk.Tk):
    """Main desktop application window."""

    def __init__(self):
        super().__init__()

        self.title("MHOAR Solutions — MTVRP Latency Solver")
        self.configure(bg=BG_DARK)
        self.minsize(1150, 720)
        self.state("zoomed")  # Start maximised on Windows

        # ── Style ─────────────────────────────────────────────────────────
        self.style = ttk.Style(self)
        self._configure_styles()

        # ── Layout: sidebar + main ────────────────────────────────────────
        self.sidebar = tk.Frame(self, bg=BG_SIDEBAR, width=300)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        self.main_area = tk.Frame(self, bg=BG_DARK)
        self.main_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_sidebar()
        self._build_main_area()

    # ══════════════════════════════════════════════════════════════════════
    #  STYLES & HOVER INTERACTIONS
    # ══════════════════════════════════════════════════════════════════════
    def _configure_styles(self):
        self.style.theme_use("clam")

        # TCombobox
        self.style.configure("Dark.TCombobox",
                             fieldbackground=BG_INPUT, background=BG_INPUT,
                             foreground=FG_PRIMARY, selectbackground=ACCENT_BLUE,
                             selectforeground=BG_DARK, borderwidth=0,
                             arrowcolor=ACCENT_BLUE)
        self.style.map("Dark.TCombobox",
                       fieldbackground=[("readonly", BG_INPUT)],
                       foreground=[("readonly", FG_PRIMARY)])

        # Horizontal TScale
        self.style.configure("Dark.Horizontal.TScale",
                             troughcolor=BG_INPUT, background=ACCENT_BLUE,
                             borderwidth=0)

        # TProgressbar
        self.style.configure("Neon.Horizontal.TProgressbar",
                             troughcolor=BG_INPUT, background=ACCENT_BLUE,
                             borderwidth=0, thickness=8)

    def _make_hover_button(self, parent, text, bg, fg, hover_bg, hover_fg, command, font=("Segoe UI", 11, "bold"), **pack_opts):
        """Creates a flat button with custom hover state and active effects."""
        btn = tk.Button(parent, text=text, font=font, bg=bg, fg=fg,
                        activebackground=hover_bg, activeforeground=hover_fg,
                        relief="flat", cursor="hand2", command=command, bd=0)
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg, fg=hover_fg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg, fg=fg))
        if pack_opts:
            btn.pack(**pack_opts)
        return btn

    def _bind_hover_card(self, widget, base_bg=BG_CARD, hover_bg="#161c2b", base_border=BORDER_COLOR, hover_border=ACCENT_BLUE):
        """Binds recursion hover events to highlight custom container cards."""
        def on_enter(e):
            widget.config(bg=hover_bg, highlightbackground=hover_border)
            # Apply to direct children
            for child in widget.winfo_children():
                if isinstance(child, tk.Label) and child.cget("bg") == base_bg:
                    child.config(bg=hover_bg)
                elif isinstance(child, tk.Frame) and child.cget("bg") == base_bg:
                    child.config(bg=hover_bg)

        def on_leave(e):
            widget.config(bg=base_bg, highlightbackground=base_border)
            for child in widget.winfo_children():
                if isinstance(child, tk.Label) and child.cget("bg") == hover_bg:
                    child.config(bg=base_bg)
                elif isinstance(child, tk.Frame) and child.cget("bg") == hover_bg:
                    child.config(bg=base_bg)

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    # ══════════════════════════════════════════════════════════════════════
    #  SIDEBAR
    # ══════════════════════════════════════════════════════════════════════
    def _build_sidebar(self):
        pad = {"padx": 16, "pady": (6, 2)}

        # ── Logo area: Gradient canvas with transparent text overlay ──────
        self.logo_canvas = GradientCanvas(self.sidebar, HEADER_GRAD1, BG_SIDEBAR, height=90)
        self.logo_canvas.pack(fill=tk.X, pady=(0, 10))

        # Add text overlay to logo canvas
        self.logo_canvas.create_text(16, 22, text="🚀 GRASP METAHEURISTIC", font=("Segoe UI", 9, "bold"), fill=ACCENT_BLUE, anchor="w")
        self.logo_canvas.create_text(16, 44, text="MHOAR Solutions", font=("Segoe UI", 18, "bold"), fill=FG_PRIMARY, anchor="w")
        self.logo_canvas.create_text(16, 68, text="MTVRP Latency Solver", font=("Segoe UI", 10), fill=FG_SECONDARY, anchor="w")

        # ── Separator ────────────────────────────────────────────────────
        tk.Frame(self.sidebar, bg=BORDER_COLOR, height=1).pack(fill=tk.X)

        # ── Configuration header ──────────────────────────────────────────
        tk.Label(self.sidebar, text="⚙️  Solver Configuration",
                 font=("Segoe UI", 11, "bold"), bg=BG_SIDEBAR,
                 fg=FG_PRIMARY).pack(anchor="w", padx=16, pady=(14, 8))

        # ── Execution Mode ────────────────────────────────────────────────
        tk.Label(self.sidebar, text="EXECUTION MODE", font=("Segoe UI", 9, "bold"),
                 bg=BG_SIDEBAR, fg=FG_SECONDARY).pack(anchor="w", **pad)

        self.mode_var = tk.StringVar(value="single")

        mode_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR)
        mode_frame.pack(fill=tk.X, padx=16, pady=4)

        self.rb_single = tk.Radiobutton(mode_frame, text="Single Instance",
                                        variable=self.mode_var, value="single",
                                        bg=BG_SIDEBAR, fg=FG_PRIMARY,
                                        selectcolor=BG_INPUT, activebackground=BG_SIDEBAR,
                                        activeforeground=FG_PRIMARY, font=("Segoe UI", 10),
                                        command=self._on_mode_change)
        self.rb_single.pack(anchor="w")

        self.rb_batch = tk.Radiobutton(mode_frame, text="Batch (All Instances)",
                                       variable=self.mode_var, value="batch",
                                       bg=BG_SIDEBAR, fg=FG_PRIMARY,
                                       selectcolor=BG_INPUT, activebackground=BG_SIDEBAR,
                                       activeforeground=FG_PRIMARY, font=("Segoe UI", 10),
                                       command=self._on_mode_change)
        self.rb_batch.pack(anchor="w")

        # ── Instance selector ─────────────────────────────────────────────
        self.instance_label = tk.Label(self.sidebar, text="SELECT INSTANCE",
                                       font=("Segoe UI", 9, "bold"),
                                       bg=BG_SIDEBAR, fg=FG_SECONDARY)
        self.instance_label.pack(anchor="w", padx=16, pady=(10, 2))

        self.folder_path = os.path.join(".", "instancias")
        self.instance_files = self._load_instance_files()

        self.instance_var = tk.StringVar()
        self.instance_combo = ttk.Combobox(self.sidebar, textvariable=self.instance_var,
                                           values=self.instance_files, state="readonly",
                                           style="Dark.TCombobox", font=("Segoe UI", 10))
        self.instance_combo.pack(fill=tk.X, padx=16, pady=4)
        if self.instance_files:
            self.instance_combo.current(0)

        # ── GRASP Parameters ─────────────────────────────────────────────
        tk.Frame(self.sidebar, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=12)
        tk.Label(self.sidebar, text="GRASP PARAMETERS",
                 font=("Segoe UI", 9, "bold"), bg=BG_SIDEBAR,
                 fg=FG_SECONDARY).pack(anchor="w", **pad)

        # Iterations
        self.iter_var = tk.IntVar(value=100)
        tk.Label(self.sidebar, text="Iterations", font=("Segoe UI", 10),
                 bg=BG_SIDEBAR, fg=FG_PRIMARY).pack(anchor="w", padx=16, pady=(6, 0))

        iter_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR)
        iter_frame.pack(fill=tk.X, padx=16, pady=2)
        self.iter_scale = tk.Scale(iter_frame, from_=10, to=200, resolution=10,
                                   orient=tk.HORIZONTAL, variable=self.iter_var,
                                   bg=BG_SIDEBAR, fg=FG_PRIMARY, troughcolor=BG_INPUT,
                                   highlightthickness=0, bd=0, activebackground=ACCENT_BLUE,
                                   font=("Segoe UI", 9), length=230)
        self.iter_scale.pack(fill=tk.X)

        # Alpha
        self.alpha_var = tk.IntVar(value=3)
        tk.Label(self.sidebar, text="RCL Size (alpha)", font=("Segoe UI", 10),
                 bg=BG_SIDEBAR, fg=FG_PRIMARY).pack(anchor="w", padx=16, pady=(6, 0))

        alpha_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR)
        alpha_frame.pack(fill=tk.X, padx=16, pady=2)
        self.alpha_scale = tk.Scale(alpha_frame, from_=1, to=5, resolution=1,
                                    orient=tk.HORIZONTAL, variable=self.alpha_var,
                                    bg=BG_SIDEBAR, fg=FG_PRIMARY, troughcolor=BG_INPUT,
                                    highlightthickness=0, bd=0, activebackground=ACCENT_BLUE,
                                    font=("Segoe UI", 9), length=230)
        self.alpha_scale.pack(fill=tk.X)

        # ── Start button ─────────────────────────────────────────────────
        tk.Frame(self.sidebar, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=12)

        self.start_btn = self._make_hover_button(
            self.sidebar, text="🚀  Start Optimization",
            bg=ACCENT_BLUE, fg=BG_DARK,
            hover_bg="#00e5ff", hover_fg=BG_DARK,
            command=self._on_start,
            fill=tk.X, padx=16, pady=8, ipady=8
        )

        # Progress bar (hidden initially)
        self.progress = ttk.Progressbar(self.sidebar, mode="determinate",
                                        style="Neon.Horizontal.TProgressbar")
        self.progress.pack(fill=tk.X, padx=16, pady=(0, 4))
        self.progress.pack_forget()

        self.status_label = tk.Label(self.sidebar, text="", font=("Segoe UI", 9),
                                     bg=BG_SIDEBAR, fg=ACCENT_GREEN, wraplength=260,
                                     justify="left")
        self.status_label.pack(anchor="w", padx=16, pady=4)

    # ══════════════════════════════════════════════════════════════════════
    #  MAIN AREA
    # ══════════════════════════════════════════════════════════════════════
    def _build_main_area(self):
        # Header banner (Real gradient banner canvas)
        self.header_canvas = GradientCanvas(self.main_area, HEADER_GRAD1, HEADER_GRAD2, height=90)
        self.header_canvas.pack(fill=tk.X)

        # Text items — will be repositioned on resize
        self._header_title = self.header_canvas.create_text(
            24, 30, text="MHOAR Solutions Dashboard",
            font=("Segoe UI", 22, "bold"), fill=FG_PRIMARY, anchor="w")
        self._header_sub = self.header_canvas.create_text(
            24, 62, text="Multi-Trip Vehicle Routing Problem · Minimum Latency Optimization Engine",
            font=("Segoe UI", 10), fill=FG_SECONDARY, anchor="w")

        # Keep text above gradient and centered vertically on resize
        def _reposition_header(event=None):
            h = self.header_canvas.winfo_height()
            self.header_canvas.coords(self._header_title, 24, h * 0.38)
            self.header_canvas.coords(self._header_sub, 24, h * 0.70)
            self.header_canvas.tag_raise(self._header_title)
            self.header_canvas.tag_raise(self._header_sub)

        self.header_canvas.bind("<Configure>", lambda e: (
            self.header_canvas.draw_gradient(e), _reposition_header(e)))

        # Scrollable content frame
        self.content_canvas = tk.Canvas(self.main_area, bg=BG_DARK, highlightthickness=0)
        self.content_scrollbar = tk.Scrollbar(self.main_area, orient=tk.VERTICAL,
                                              command=self.content_canvas.yview)
        self.content_frame = tk.Frame(self.content_canvas, bg=BG_DARK)

        self.content_frame.bind("<Configure>",
                                lambda e: self.content_canvas.configure(
                                    scrollregion=self.content_canvas.bbox("all")))

        self.canvas_window = self.content_canvas.create_window((0, 0),
                                                                window=self.content_frame,
                                                                anchor="nw")
        self.content_canvas.configure(yscrollcommand=self.content_scrollbar.set)

        self.content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind canvas resize to stretch content_frame width
        self.content_canvas.bind("<Configure>", self._on_canvas_configure)

        # Bind mouse-wheel scrolling
        self.content_canvas.bind_all("<MouseWheel>",
                                     lambda e: self.content_canvas.yview_scroll(
                                         int(-1 * (e.delta / 120)), "units"))

        # Welcome message
        self._show_welcome()

    def _on_canvas_configure(self, event):
        self.content_canvas.itemconfig(self.canvas_window, width=event.width)

    def _show_welcome(self):
        self._clear_content()

        # Premium center welcome card
        welcome_card = tk.Frame(self.content_frame, bg=BG_CARD,
                                highlightbackground=BORDER_COLOR, highlightthickness=1,
                                padx=40, pady=40)
        welcome_card.pack(anchor="center", pady=100)

        # Glowing truck icon
        tk.Label(welcome_card, text="🚚", font=("Segoe UI", 64), bg=BG_CARD).pack(pady=(0, 10))

        tk.Label(welcome_card, text="Optimization Engine", font=("Segoe UI", 18, "bold"),
                 bg=BG_CARD, fg=FG_PRIMARY).pack(pady=(0, 4))
                 
        tk.Label(welcome_card, text="Multi-Trip Vehicle Routing Problem with Minimum Latency", font=("Segoe UI", 10),
                 bg=BG_CARD, fg=FG_SECONDARY).pack(pady=(0, 20))

        # Divider line
        tk.Frame(welcome_card, bg=BORDER_COLOR, height=1, width=280).pack(pady=10)

        tk.Label(welcome_card,
                 text="👈  Configure solver settings on the sidebar\nand click \"Start Optimization\" to execute.",
                 font=("Segoe UI", 11), bg=BG_CARD, fg=FG_SECONDARY, justify="center").pack(pady=10)

    # ══════════════════════════════════════════════════════════════════════
    #  HELPERS
    # ══════════════════════════════════════════════════════════════════════
    def _load_instance_files(self):
        if not os.path.exists(self.folder_path):
            return []
        files = [f for f in os.listdir(self.folder_path)
                 if f.lower().endswith(".txt")]
        files.sort()
        return files

    def _on_mode_change(self):
        if self.mode_var.get() == "batch":
            self.instance_label.pack_forget()
            self.instance_combo.pack_forget()
        else:
            # Re-pack after the mode radio buttons
            self.instance_label.pack(anchor="w", padx=16, pady=(10, 2),
                                     after=self.rb_batch.master)
            self.instance_combo.pack(fill=tk.X, padx=16, pady=4,
                                     after=self.instance_label)

    def _clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _make_metric_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg=BG_CARD, highlightbackground=BORDER_COLOR,
                        highlightthickness=1, padx=20, pady=16)
        tk.Label(card, text=title.upper(), font=("Segoe UI", 9, "bold"),
                 bg=BG_CARD, fg=FG_SECONDARY).pack(anchor="w")
        tk.Label(card, text=value, font=("Segoe UI", 28, "bold"),
                 bg=BG_CARD, fg=color).pack(anchor="w", pady=(4, 0))
        self._bind_hover_card(card)
        return card

    # ══════════════════════════════════════════════════════════════════════
    #  SOLVER EXECUTION
    # ══════════════════════════════════════════════════════════════════════
    def _on_start(self):
        if not self.instance_files:
            messagebox.showerror("Error", "No instance files found in ./instancias")
            return

        self.start_btn.config(state=tk.DISABLED, text="⏳  Optimizing…")
        self.status_label.config(text="")

        if self.mode_var.get() == "single":
            threading.Thread(target=self._run_single, daemon=True).start()
        else:
            threading.Thread(target=self._run_batch, daemon=True).start()

    # ── Single Instance ───────────────────────────────────────────────────
    def _run_single(self):
        filename   = self.instance_var.get()
        filepath   = os.path.join(self.folder_path, filename)
        iterations = self.iter_var.get()
        alpha      = self.alpha_var.get()

        self.after(0, lambda: self.status_label.config(
            text=f"Optimizing {filename}…", fg=ACCENT_BLUE))

        start = time.time()
        nodes, demands, capacity, max_time, dist_matrix = parse_instance(filepath)
        routes, latency = solve_mtvrp_grasp(nodes, demands, capacity, max_time,
                                            dist_matrix, iterations=iterations, alpha=alpha)
        exec_time = time.time() - start

        self.after(0, lambda: self._display_single_results(
            filename, nodes, demands, capacity, dist_matrix, routes, latency, exec_time, alpha))

    def _display_single_results(self, filename, nodes, demands, capacity,
                                dist_matrix, routes, latency, exec_time, alpha=3):
        self._clear_content()

        # ── Status ────────────────────────────────────────────────────────
        self.status_label.config(text=f"✅ {filename} solved!", fg=ACCENT_GREEN)
        self.start_btn.config(state=tk.NORMAL, text="🚀  Start Optimization")

        # ── Metric cards ──────────────────────────────────────────────────
        metrics_row = tk.Frame(self.content_frame, bg=BG_DARK)
        metrics_row.pack(fill=tk.X, padx=20, pady=(20, 10))

        c1 = self._make_metric_card(metrics_row, "Mejor Valor Encontrado",
                                    f"{latency:.2f}", ACCENT_BLUE)
        c1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        c2 = self._make_metric_card(metrics_row, "Tiempo de Ejecución",
                                    f"{exec_time:.4f} s", ACCENT_PINK)
        c2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        c3 = self._make_metric_card(metrics_row, "Viajes Requeridos",
                                    str(len(routes)), ACCENT_ORANGE)
        c3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        c4 = self._make_metric_card(metrics_row, "Config. Usada (alpha)",
                                    str(alpha), ACCENT_GREEN)
        c4.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))

        # ── Body: chart + trip details ────────────────────────────────────
        body = tk.Frame(self.content_frame, bg=BG_DARK)
        body.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Left: matplotlib chart
        has_coords = any(c != (0, 0) for i, c in nodes.items() if i != 0)

        chart_frame = tk.Frame(body, bg=BG_CARD, highlightbackground=BORDER_COLOR,
                               highlightthickness=1)
        chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self._bind_hover_card(chart_frame)

        if has_coords:
            tk.Label(chart_frame, text="🗺️  Route Map Visualization",
                     font=("Segoe UI", 13, "bold"), bg=BG_CARD,
                     fg=FG_PRIMARY).pack(anchor="w", padx=14, pady=(12, 4))

            fig = Figure(figsize=(7, 5.5), dpi=100)
            fig.patch.set_facecolor(BG_CARD)  # Seamless integration
            ax = fig.add_subplot(111)
            ax.set_facecolor("#0b0f19")

            # Depot
            dx, dy = nodes[0]
            ax.scatter(dx, dy, color='#ffd700', marker='*', s=400,
                       edgecolor='#ffffff', linewidth=1.5, label='Depot (0)', zorder=6)
            ax.annotate("DEPOT", (dx, dy), textcoords="offset points",
                        xytext=(0, -18), ha='center', fontweight='bold',
                        color='#ffd700', fontsize=9)

            # Clients
            cx = [nodes[i][0] for i in nodes if i != 0]
            cy = [nodes[i][1] for i in nodes if i != 0]
            ax.scatter(cx, cy, color=ACCENT_BLUE, marker='o', s=110,
                       edgecolor='#ffffff', linewidth=0.7, alpha=0.9,
                       label='Clients', zorder=3)

            for nid, (x, y) in nodes.items():
                if nid != 0:
                    ax.annotate(str(nid), (x, y), textcoords="offset points",
                                xytext=(0, 6), ha='center', fontsize=8,
                                color='#ffffff', fontweight='semibold')

            # Routes
            for idx, route in enumerate(routes):
                color = NEON_COLORS[idx % len(NEON_COLORS)]
                xs = [nodes[n][0] for n in route]
                ys = [nodes[n][1] for n in route]
                ax.plot(xs, ys, color=color, linewidth=2.5, alpha=0.85,
                        label=f'Trip {idx + 1}', zorder=2)
                for i in range(len(route) - 1):
                    s = nodes[route[i]]
                    e = nodes[route[i + 1]]
                    ax.annotate('', xy=e, xytext=s,
                                arrowprops=dict(arrowstyle="-|>", color=color,
                                                lw=1.8, mutation_scale=11),
                                zorder=2)

            ax.set_xlabel("X", color=FG_SECONDARY, fontsize=9)
            ax.set_ylabel("Y", color=FG_SECONDARY, fontsize=9)
            ax.tick_params(colors=FG_SECONDARY, labelsize=8)
            ax.grid(True, linestyle='--', alpha=0.1, color='#ffffff')

            # Clean borders (spines) for matplotlib chart
            for spine in ax.spines.values():
                spine.set_color(BORDER_COLOR)

            legend = ax.legend(loc='upper left', framealpha=0.15,
                               facecolor=BG_DARK, edgecolor=BORDER_COLOR,
                               fontsize=8)
            for t in legend.get_texts():
                t.set_color("white")

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))
        else:
            tk.Label(chart_frame,
                     text="⚠️ This instance uses a travel-time matrix.\nNo 2-D coordinates available for plotting.",
                     font=("Segoe UI", 12), bg=BG_CARD, fg=FG_SECONDARY,
                     justify="center").pack(expand=True, pady=60)

        # Right: trip breakdown (scrollable)
        right_frame = tk.Frame(body, bg=BG_CARD, highlightbackground=BORDER_COLOR,
                               highlightthickness=1, width=360)
        right_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)
        self._bind_hover_card(right_frame)

        tk.Label(right_frame, text="📋  Detailed Trip Breakdown",
                 font=("Segoe UI", 13, "bold"), bg=BG_CARD,
                 fg=FG_PRIMARY).pack(anchor="w", padx=14, pady=(12, 8))

        trips_canvas = tk.Canvas(right_frame, bg=BG_CARD, highlightthickness=0)
        trips_sb = tk.Scrollbar(right_frame, orient=tk.VERTICAL,
                                command=trips_canvas.yview)
        trips_inner = tk.Frame(trips_canvas, bg=BG_CARD)

        trips_inner.bind("<Configure>",
                         lambda e: trips_canvas.configure(
                             scrollregion=trips_canvas.bbox("all")))

        trips_win = trips_canvas.create_window((0, 0), window=trips_inner, anchor="nw")
        trips_canvas.configure(yscrollcommand=trips_sb.set)

        trips_canvas.bind("<Configure>",
                          lambda e: trips_canvas.itemconfig(trips_win, width=e.width))

        # Scroll inside trips panel only
        def _on_trips_wheel(event):
            trips_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        trips_canvas.bind("<Enter>",
                          lambda e: self.content_canvas.unbind_all("<MouseWheel>"))
        trips_canvas.bind("<Leave>",
                          lambda e: self.content_canvas.bind_all(
                              "<MouseWheel>",
                              lambda ev: self.content_canvas.yview_scroll(
                                  int(-1 * (ev.delta / 120)), "units")))
        trips_canvas.bind_all("<MouseWheel>", _on_trips_wheel)

        trips_sb.pack(side=tk.RIGHT, fill=tk.Y)
        trips_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for idx, route in enumerate(routes):
            color = NEON_COLORS[idx % len(NEON_COLORS)]
            trip_load = sum(demands.get(n, 0) for n in route)
            load_pct = trip_load / capacity if capacity else 0
            dur = route_duration(route, dist_matrix)
            route_str = " ➔ ".join(str(n) for n in route)

            card = tk.Frame(trips_inner, bg="#182030",
                            highlightbackground=color, highlightthickness=0)
            card.pack(fill=tk.X, padx=10, pady=4)

            # Colored left bar (simulate border-left)
            bar = tk.Frame(card, bg=color, width=4)
            bar.pack(side=tk.LEFT, fill=tk.Y)

            inner = tk.Frame(card, bg="#182030", padx=10, pady=8)
            inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            tk.Label(inner, text=f"Trip {idx + 1}", font=("Segoe UI", 12, "bold"),
                     bg="#182030", fg=color).pack(anchor="w")

            tk.Label(inner, text=route_str, font=("Consolas", 9),
                     bg="#0e131d", fg=FG_PRIMARY, wraplength=280, justify="left",
                     padx=6, pady=4).pack(fill=tk.X, pady=(4, 6))

            info_frame = tk.Frame(inner, bg="#182030")
            info_frame.pack(fill=tk.X)
            tk.Label(info_frame, text=f"⏱ {dur:.2f}", font=("Segoe UI", 9),
                     bg="#182030", fg=FG_SECONDARY).pack(side=tk.LEFT)
            tk.Label(info_frame,
                     text=f"⚖ {trip_load:.0f}/{capacity:.0f} ({load_pct*100:.0f}%)",
                     font=("Segoe UI", 9), bg="#182030",
                     fg=FG_SECONDARY).pack(side=tk.RIGHT)

            # Capacity bar
            bar_bg = tk.Frame(inner, bg=BG_INPUT, height=6)
            bar_bg.pack(fill=tk.X, pady=(6, 0))
            bar_bg.update_idletasks()
            bar_fill_width = max(int(bar_bg.winfo_width() * min(load_pct, 1.0)), 1)
            bar_fill = tk.Frame(bar_bg, bg=color, height=6, width=bar_fill_width)
            bar_fill.place(x=0, y=0, relwidth=min(load_pct, 1.0), relheight=1.0)

    # ── Batch Mode ────────────────────────────────────────────────────────
    def _run_batch(self):
        ALPHA_VALUES = [1, 2, 3, 5, 7]
        iterations   = self.iter_var.get()
        files        = self.instance_files
        total        = len(files)
        results      = []

        self.after(0, self._show_progress)

        for index, filename in enumerate(files):
            self.after(0, lambda fn=filename, i=index: self.status_label.config(
                text=f"Solving ({i + 1}/{total}): {fn}…", fg=ACCENT_BLUE))

            filepath = os.path.join(self.folder_path, filename)
            nodes, demands, capacity, max_time, dist_matrix = parse_instance(filepath)

            latencies    = []
            times        = []
            best_latency = float('inf')
            best_alpha   = None

            for alpha in ALPHA_VALUES:
                t0 = time.time()
                _, latency = solve_mtvrp_grasp(nodes, demands, capacity, max_time,
                                               dist_matrix, iterations=iterations, alpha=alpha)
                times.append(time.time() - t0)
                latencies.append(latency)
                if latency < best_latency:
                    best_latency = latency
                    best_alpha   = alpha

            results.append({
                "Instancia": filename,
                "Mejor Valor Enc.": round(min(latencies), 2),
                "Valor Promedio": round(sum(latencies) / len(latencies), 2),
                "Peor Valor": round(max(latencies), 2),
                "Tiempo Prom. (s)": round(sum(times) / len(times), 4),
                "Num. Replicas": len(ALPHA_VALUES),
                "Mejor Config. (alpha)": best_alpha,
            })

            pct = int((index + 1) / total * 100)
            self.after(0, lambda p=pct: self.progress.configure(value=p))

        self.after(0, lambda: self._display_batch_results(results))

    def _show_progress(self):
        self.progress.configure(value=0, maximum=100)
        self.progress.pack(fill=tk.X, padx=16, pady=(0, 4))

    def _display_batch_results(self, results):
        self._clear_content()
        self.progress.pack_forget()
        self.status_label.config(text="✅ All instances solved!", fg=ACCENT_GREEN)
        self.start_btn.config(state=tk.NORMAL, text="🚀  Start Optimization")

        tk.Label(self.content_frame, text="📊  General Results Table",
                 font=("Segoe UI", 16, "bold"), bg=BG_DARK,
                 fg=FG_PRIMARY).pack(anchor="w", padx=20, pady=(20, 10))

        # ── Configure Treeview dark theme ─────────────────────────────────
        self.style.configure("Results.Treeview",
                             background=BG_CARD,
                             foreground=FG_PRIMARY,
                             fieldbackground=BG_CARD,
                             borderwidth=0,
                             font=("Segoe UI", 10),
                             rowheight=36)
        self.style.configure("Results.Treeview.Heading",
                             background=HEADER_GRAD1,
                             foreground=FG_PRIMARY,
                             font=("Segoe UI", 10, "bold"),
                             borderwidth=0,
                             relief="flat",
                             padding=(14, 10))
        self.style.map("Results.Treeview.Heading",
                       background=[("active", HEADER_GRAD2)])
        self.style.map("Results.Treeview",
                       background=[("selected", "#1f2a45")],
                       foreground=[("selected", ACCENT_BLUE)])
        self.style.layout("Results.Treeview", [
            ("Results.Treeview.treearea", {"sticky": "nsew"})
        ])

        # ── Table container ───────────────────────────────────────────────
        table_container = tk.Frame(self.content_frame, bg=BORDER_COLOR,
                                   highlightbackground=BORDER_COLOR,
                                   highlightthickness=1)
        table_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        cols = list(results[0].keys())
        all_cols = ["#"] + cols
        col_ids = [f"col{j}" for j in range(len(all_cols))]

        tree = ttk.Treeview(table_container, columns=col_ids, show="headings",
                            style="Results.Treeview", selectmode="browse")

        # Scrollbar
        tree_scroll = tk.Scrollbar(table_container, orient=tk.VERTICAL,
                                   command=tree.yview)
        tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)

        # Configure headings and column widths
        col_widths = {
            "#": 50,
            "Instancia": 200,
            "Mejor Valor Enc.": 150,
            "Valor Promedio": 130,
            "Peor Valor": 110,
            "Tiempo Prom. (s)": 140,
            "Num. Replicas": 120,
            "Mejor Config. (alpha)": 160,
        }
        for j, (col_id, col_name) in enumerate(zip(col_ids, all_cols)):
            w = col_widths.get(col_name, 140)
            anchor = "w" if col_name == "Instance" else "center"
            header_text = f"  {col_name}" if col_name == "Instance" else col_name
            tree.heading(col_id, text=header_text, anchor=anchor)
            tree.column(col_id, anchor=anchor, width=w, minwidth=40 if col_name == "#" else 80, stretch=col_name != "#")

        # Alternating row tags
        tree.tag_configure("even", background=BG_CARD, foreground=FG_PRIMARY)
        tree.tag_configure("odd", background="#161c28", foreground=FG_PRIMARY)

        # Insert rows
        for i, row in enumerate(results):
            tag = "even" if i % 2 == 0 else "odd"
            
            padded_row = []
            for col in cols:
                val = row[col]
                if col == "Instance":
                    val = f"  {val}"
                padded_row.append(val)
                
            values = [i + 1] + padded_row
            tree.insert("", tk.END, values=values, tags=(tag,))

        # Export button
        def export_csv():
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile="resultados_mtvrp_grasp.csv")
            if not path:
                return
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=cols)
                writer.writeheader()
                writer.writerows(results)
            messagebox.showinfo("Export", f"Results saved to:\n{path}")

        self._make_hover_button(
            self.content_frame, text="📥  Export Results as CSV",
            bg=ACCENT_GREEN, fg=BG_DARK,
            hover_bg="#2ed573", hover_fg=BG_DARK,
            command=export_csv,
            anchor="w", padx=20, pady=(10, 20), ipady=6, ipadx=16
        )


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = MTVRPDesktopApp()
    app.mainloop()
