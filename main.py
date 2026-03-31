import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import os
import segyio

try:
    from tkinterdnd2 import COPY, DND_FILES, TkinterDnD
except ImportError:
    COPY = None
    DND_FILES = None
    TkinterDnD = None

ANALYSIS_METHODS = (
    ("interp", "Интерполяция данных", "Интерполяция\nданных"),
    ("denoise", "Подавление шумов", "Подавление\nшумов"),
    ("spectrum", "Расширение амплитудного спектра", "Расширение\nамплитудного\nспектра"),
    ("resolution", "Повышение разрешающей способности", "Повышение\nразрешающей\nспособности"),
)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        if TkinterDnD is not None:
            TkinterDnD._require(self)

        self.title("Seismic Data Suite")
        self.geometry("1100x800")

        self.current_state = {
            "tab": "Файл",
            "theme": "System",
            "scale": "100%"
        }
        self.history = [self.current_state.copy()]
        self.history_index = 0
        self.is_navigating = False
        self._dnd_leave_timer = None
        self.analysis_pipeline = []
        self._pipe_drag = None

        self.top_container = ctk.CTkFrame(self, fg_color="transparent")
        self.top_container.pack(fill="x", padx=15, pady=(10, 0))

        self.logo_label = ctk.CTkLabel(self.top_container, text="SEIS",
                                         font=("Arial", 24, "bold"), text_color="#3b8ed0")
        self.logo_label.pack(side="left", padx=(0, 15))

        self.nav_frame = ctk.CTkFrame(self.top_container, fg_color="transparent")
        self.nav_frame.pack(side="left")

        self.btn_back = ctk.CTkButton(self.nav_frame, text="←", width=35, height=35, fg_color="gray30",
                                     command=self.go_back)
        self.btn_back.pack(side="left", padx=1)
        self.btn_forward = ctk.CTkButton(self.nav_frame, text="→", width=35, height=35, fg_color="gray30",
                                         command=self.go_forward)
        self.btn_forward.pack(side="left", padx=1)

        self.tab_buttons = {}
        self.tabs_list = ["Файл", "Главная", "Данные", "Анализ", "Вид"]
        for name in self.tabs_list:
            btn = ctk.CTkButton(self.top_container, text=name, width=85, height=35,
                                fg_color="transparent", text_color=("gray10", "gray80"),
                                command=lambda n=name: self.save_state(tab=n))
            btn.pack(side="left", padx=1)
            self.tab_buttons[name] = btn

        self.ribbon = ctk.CTkFrame(self, height=112, corner_radius=0,
                                  border_width=1, border_color=("gray70", "gray30"))
        self.ribbon.pack(fill="x", padx=0, pady=(5, 0))
        self.ribbon.pack_propagate(False)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=20)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for name in self.tabs_list:
            frame = ctk.CTkFrame(self.container, fg_color="transparent")
            self.frames[name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.setup_file_page()
        self.setup_ribbon_tools()
        self.setup_analysis_page()
        self.setup_view_settings()

        ctk.CTkLabel(self.frames["Главная"], text="Рабочая область: ГЛАВНАЯ", font=("Arial", 16, "italic")).pack(
            pady=50)
        ctk.CTkLabel(self.frames["Данные"], text="Когда-нибудь тут будут данные", font=("Arial", 24)).pack(pady=100)

        self.apply_state(self.current_state)

    def setup_ribbon_tools(self):
        self.home_tools = ctk.CTkFrame(self.ribbon, fg_color="transparent")

        def add_tool(icon, text, cmd):
            btn = ctk.CTkButton(self.home_tools,
                                text=f"{icon}\n{text}",
                                fg_color=("#eeeeee", "#333333"),
                                text_color=("#1a1a1a", "#ffffff"),
                                hover_color=("#dddddd", "#444444"),
                                border_width=1,
                                border_color=("#cccccc", "#444444"),
                                corner_radius=8,
                                width=100,
                                height=80,
                                font=("Arial", 12, "bold"),
                                command=cmd)
            btn.pack(side="left", padx=4, pady=10)

        add_tool("⚙️", "Настройки", lambda: print("Настройки"))
        add_tool("⏳", "Фильтр", lambda: print("Фильтр"))
        add_tool("📈", "Амплитуда", lambda: print("Амплитуда"))

        self.analysis_tools = ctk.CTkFrame(self.ribbon, fg_color="transparent")
        self.analysis_method_indicators = {}
        _ind = 12
        _row_h = 22
        ctk.CTkLabel(
            self.analysis_tools,
            text="Методы обработки",
            font=("Arial", 12, "bold"),
            anchor="w",
            text_color=("gray15", "gray80"),
        ).pack(anchor="w", padx=(4, 12), pady=(0, 1))
        for mid, full, _short in ANALYSIS_METHODS:
            row = ctk.CTkFrame(
                self.analysis_tools,
                fg_color="transparent",
                cursor="hand2",
                height=_row_h,
            )
            row.pack(fill="x", anchor="w", padx=(2, 12), pady=0)
            row.pack_propagate(False)
            square = ctk.CTkFrame(
                row,
                width=_ind,
                height=_ind,
                corner_radius=2,
                border_width=1,
                border_color=("#9aa5b1", "#6b6b6b"),
                fg_color="transparent",
            )
            square.pack(side="left", padx=(2, 7), pady=0)
            square.pack_propagate(False)
            title = ctk.CTkLabel(
                row,
                text=full,
                font=("Arial", 11),
                anchor="w",
                text_color=("gray10", "gray85"),
            )
            title.pack(side="left", fill="x", expand=True, padx=(0, 4), pady=0)
            pick = lambda e, m=mid: self.toggle_analysis_method(m)
            row.bind("<Button-1>", pick)
            square.bind("<Button-1>", pick)
            title.bind("<Button-1>", pick)
            self.analysis_method_indicators[mid] = square

    def setup_analysis_page(self):
        f = self.frames["Анализ"]
        self.analysis_body = ctk.CTkFrame(f, fg_color="transparent")
        self.analysis_body.pack(fill="both", expand=True)

        # Левая колонка без распорок — «Цепочка» сразу под полосой «Методы обработки», вверху слева
        left_col = ctk.CTkFrame(self.analysis_body, fg_color="transparent", width=300)
        left_col.pack(side="left", fill="y", anchor="nw")
        left_col.pack_propagate(False)

        self.analysis_pipeline_outer = ctk.CTkFrame(
            left_col,
            fg_color=("#f4f7fb", "#2c2c2c"),
            corner_radius=12,
            border_width=1,
            border_color=("gray62", "gray36"),
            width=272,
        )
        self.analysis_pipeline_outer.pack(side="top", anchor="nw", padx=0, pady=0)
        self.analysis_pipeline_outer.pack_propagate(False)

        ctk.CTkLabel(
            self.analysis_pipeline_outer,
            text="Цепочка обработки",
            font=("Arial", 16, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            self.analysis_pipeline_outer,
            text="Отметьте методы в списке выше. Перетащите строки ниже,\nчтобы изменить порядок. Клик по строке в цепочке — убрать.",
            font=("Arial", 11),
            text_color=("gray35", "gray65"),
            justify="left",
        ).pack(anchor="w", padx=14, pady=(0, 8))

        self.analysis_pipeline_scroll = ctk.CTkScrollableFrame(
            self.analysis_pipeline_outer,
            fg_color="transparent",
            height=320,
        )
        self.analysis_pipeline_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        self.analysis_workspace = ctk.CTkFrame(self.analysis_body, fg_color="transparent")
        self.analysis_workspace.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=0)
        ctk.CTkLabel(
            self.analysis_workspace,
            text="Рабочая область анализа",
            font=("Arial", 16, "italic"),
            text_color=("gray50", "gray55"),
        ).pack(expand=True)

        self._refresh_analysis_ui()

    def _analysis_label(self, mid: str) -> str:
        for m, full, _ in ANALYSIS_METHODS:
            if m == mid:
                return full
        return mid

    def toggle_analysis_method(self, mid: str):
        if mid in self.analysis_pipeline:
            self.analysis_pipeline.remove(mid)
        else:
            self.analysis_pipeline.append(mid)
        self._refresh_analysis_ui()

    def _refresh_analysis_ui(self):
        on_color = "#3b8ed0"
        off_border = ("#9aa5b1", "#6b6b6b")
        on_border = ("#2e86c1", "#5dade2")
        for mid, box in self.analysis_method_indicators.items():
            if mid in self.analysis_pipeline:
                box.configure(fg_color=on_color, border_color=on_border)
            else:
                box.configure(fg_color="transparent", border_color=off_border)
        self._rebuild_pipeline_list()

    def _pipeline_scroll_rows(self):
        return [c for c in self.analysis_pipeline_scroll.winfo_children() if isinstance(c, ctk.CTkFrame)]

    def _pipeline_row_idle_style(self, row):
        if not row.winfo_exists():
            return
        row.configure(fg_color=("gray88", "#3d3d3d"), border_width=0, cursor="hand2")

    def _pipeline_row_slot_style(self, row, title_lbl):
        if row.winfo_exists():
            row.configure(
                fg_color=("gray94", "#2a2a2a"),
                border_width=1,
                border_color=("gray80", "#555"),
                cursor="none",
            )
        if title_lbl.winfo_exists():
            title_lbl.configure(text="")

    def _make_drag_ghost(self, mid: str, width_px: int):
        g = ctk.CTkToplevel(self)
        g.overrideredirect(True)
        try:
            g.attributes("-topmost", True)
        except tk.TclError:
            pass
        try:
            g.attributes("-alpha", 0.9)
        except tk.TclError:
            pass
        fr = ctk.CTkFrame(
            g,
            fg_color=("gray90", "#3a3a3a"),
            border_width=2,
            border_color="#3b8ed0",
            corner_radius=5,
            height=30,
        )
        fr.pack(fill="both", expand=True)
        ctk.CTkLabel(fr, text="☰", width=28, font=("Segoe UI", 14), text_color=("gray40", "gray65")).pack(
            side="left", padx=(4, 2)
        )
        ctk.CTkLabel(fr, text=self._analysis_label(mid), font=("Arial", 10), anchor="w").pack(
            side="left", fill="x", expand=True, padx=(4, 8)
        )
        w = max(160, int(width_px))
        g.geometry(f"{w}x32+{-1000}+{-1000}")
        return g

    def _rebuild_pipeline_list(self):
        for w in self.analysis_pipeline_scroll.winfo_children():
            w.destroy()
        if not self.analysis_pipeline:
            ctk.CTkLabel(
                self.analysis_pipeline_scroll,
                text="Методы не выбраны",
                font=("Arial", 13),
                text_color="gray55",
            ).pack(pady=24)
            return
        _h = 30
        for i, mid in enumerate(self.analysis_pipeline):
            row = ctk.CTkFrame(
                self.analysis_pipeline_scroll,
                fg_color=("gray88", "#3d3d3d"),
                height=_h,
                corner_radius=8,
                cursor="hand2",
            )
            row.pack(fill="x", pady=3, padx=2)
            row.pack_propagate(False)
            grip = ctk.CTkLabel(row, text="☰", width=28, font=("Segoe UI", 14), text_color=("gray40", "gray65"))
            grip.pack(side="left", padx=(6, 2))
            title = ctk.CTkLabel(row, text=self._analysis_label(mid), font=("Arial", 10), anchor="w")
            title.pack(side="left", fill="x", expand=True, padx=(4, 8))
            for w in (row, grip, title):
                w.bind(
                    "<Button-1>",
                    lambda e, idx=i, r=row, t=title, m=mid: self._pipeline_press(e, idx, r, t, m),
                )

    def _pipeline_press(self, event, idx: int, row, title_lbl, mid: str):
        gx = event.x_root - row.winfo_rootx()
        gy = event.y_root - row.winfo_rooty()
        self._pipe_drag = {
            "i": idx,
            "mid": mid,
            "x0": event.x_root,
            "y0": event.y_root,
            "moved": False,
            "row": row,
            "title_lbl": title_lbl,
            "visual_on": False,
            "hl_row": None,
            "ghost": None,
            "goffs": (gx, gy),
            "ghost_w": 180,
        }
        self.bind_all("<B1-Motion>", self._pipeline_motion_all)
        self.bind_all("<ButtonRelease-1>", self._pipeline_release_all)

    def _pipeline_motion_all(self, event):
        self._pipeline_motion_core(event.x_root, event.y_root)

    def _pipeline_motion_core(self, x_root, y_root):
        d = self._pipe_drag
        if not d:
            return
        if abs(x_root - d["x0"]) + abs(y_root - d["y0"]) > 6:
            if not d["visual_on"]:
                d["visual_on"] = True
                self.update_idletasks()
                row = d["row"]
                rw = max(150, row.winfo_width())
                d["ghost_w"] = rw
                d["ghost"] = self._make_drag_ghost(d["mid"], rw)
                gx = x_root - d["goffs"][0]
                gy = y_root - d["goffs"][1]
                d["ghost"].geometry(f"{rw}x32+{gx}+{gy}")
                self._pipeline_row_slot_style(row, d["title_lbl"])
                try:
                    self.configure(cursor="fleur")
                except tk.TclError:
                    pass
            d["moved"] = True
            gh = d.get("ghost")
            if gh is not None:
                try:
                    rw = d["ghost_w"]
                    ox, oy = d["goffs"]
                    gh.geometry(f"{rw}x32+{x_root - ox}+{y_root - oy}")
                except tk.TclError:
                    pass
            self._pipeline_update_drop_preview(y_root)

    def _pipeline_update_drop_preview(self, y_root: int):
        d = self._pipe_drag
        if not d or not d.get("visual_on"):
            return
        drag_row = d["row"]
        rows = self._pipeline_scroll_rows()
        target_idx = self._pipeline_row_index_at_y(y_root)
        prev = d.get("hl_row")
        if prev is not None and prev.winfo_exists() and prev is not drag_row:
            self._pipeline_row_idle_style(prev)
        d["hl_row"] = None
        if target_idx is None or not (0 <= target_idx < len(rows)):
            return
        target = rows[target_idx]
        if target is drag_row:
            return
        target.configure(
            fg_color=("gray88", "#3d3d3d"),
            border_width=2,
            border_color="#5dade2",
            cursor="hand2",
        )
        d["hl_row"] = target

    def _pipeline_release_all(self, event):
        d = self._pipe_drag
        if d is None:
            return
        self.unbind_all("<B1-Motion>")
        self.unbind_all("<ButtonRelease-1>")
        idx0 = d["i"]
        mid = d["mid"]
        title_lbl = d["title_lbl"]
        drag_row = d["row"]
        moved = d["moved"]
        hl = d.get("hl_row")
        ghost = d.get("ghost")
        self._pipe_drag = None
        try:
            self.configure(cursor="")
        except tk.TclError:
            pass
        if ghost is not None:
            try:
                ghost.destroy()
            except tk.TclError:
                pass
        if moved:
            to = self._pipeline_row_index_at_y(event.y_root)
            if to is not None and to != idx0:
                self._reorder_pipeline(idx0, to)
                self._refresh_analysis_ui()
            else:
                if drag_row and drag_row.winfo_exists():
                    self._pipeline_row_idle_style(drag_row)
                    if title_lbl.winfo_exists():
                        title_lbl.configure(text=self._analysis_label(mid))
                if hl and hl.winfo_exists() and hl is not drag_row:
                    self._pipeline_row_idle_style(hl)
        else:
            if 0 <= idx0 < len(self.analysis_pipeline):
                self.analysis_pipeline.pop(idx0)
                self._refresh_analysis_ui()

    def _pipeline_row_index_at_y(self, y_root: int):
        rows = self._pipeline_scroll_rows()
        for i, c in enumerate(rows):
            try:
                top = c.winfo_rooty()
                bot = top + c.winfo_height()
                if top <= y_root < bot:
                    return i
            except tk.TclError:
                continue
        return None

    def _reorder_pipeline(self, from_i: int, to_i: int):
        seq = self.analysis_pipeline
        if not (0 <= from_i < len(seq) and 0 <= to_i < len(seq)):
            return
        item = seq.pop(from_i)
        seq.insert(to_i, item)

    def setup_file_page(self):
        self._upload_border_idle = ("gray62", "gray36")
        self._upload_fg_idle = ("#f4f7fb", "#2c2c2c")
        self._upload_dnd_hint_idle = (
            "Перетащите файл сюда из проводника\nили нажмите кнопку ниже",
            ("gray40", "gray60"),
        )

        self.upload_box = ctk.CTkFrame(
            self.frames["Файл"],
            border_width=2,
            border_color=self._upload_border_idle,
            fg_color=self._upload_fg_idle,
            corner_radius=14,
            width=700,
            height=450,
        )
        self.upload_box.place(relx=0.5, rely=0.5, anchor="center")
        self.upload_box.pack_propagate(False)

        self.upload_glyph = ctk.CTkLabel(
            self.upload_box,
            text="⬇",
            font=("Segoe UI Symbol", 44),
            text_color=("#3b8ed0", "#5dade2"),
        )
        self.upload_glyph.pack(pady=(36, 0))

        self.upload_title = ctk.CTkLabel(self.upload_box, text="Область загрузки", font=("Arial", 26, "bold"))
        self.upload_title.pack(pady=(4, 6))
        self.upload_formats = ctk.CTkLabel(
            self.upload_box,
            text="Доступные форматы: .sgy, .segy",
            font=("Arial", 14),
            text_color="#3b8ed0",
        )
        self.upload_formats.pack(pady=(0, 8))

        self.upload_dnd_hint = ctk.CTkLabel(
            self.upload_box,
            text=self._upload_dnd_hint_idle[0],
            font=("Arial", 15),
            text_color=self._upload_dnd_hint_idle[1],
            justify="center",
        )
        self.upload_dnd_hint.pack(pady=(0, 14))

        self.btn_select = ctk.CTkButton(
            self.upload_box,
            text="Выбрать файл",
            width=200,
            height=50,
            font=("Arial", 16),
            command=self.open_file_dialog,
        )
        self.btn_select.pack(pady=10)

        self.file_status = ctk.CTkLabel(
            self.upload_box,
            text="Файл не выбран",
            font=("Arial", 14),
            text_color="gray",
        )
        self.file_status.pack(pady=(10, 36))

        self._register_file_drop_targets()

    def _register_file_drop_targets(self):
        if DND_FILES is None:
            return
        for w in (
            self.upload_box,
            self.upload_glyph,
            self.upload_title,
            self.upload_formats,
            self.upload_dnd_hint,
            self.btn_select,
            self.file_status,
        ):
            w.drop_target_register(DND_FILES)
            w.dnd_bind("<<Drop>>", self._on_file_drop)
            w.dnd_bind("<<DropEnter>>", self._on_drop_enter)
            w.dnd_bind("<<DropLeave>>", self._on_drop_leave)

    def _cancel_scheduled_drop_unhighlight(self):
        if self._dnd_leave_timer is not None:
            self.after_cancel(self._dnd_leave_timer)
            self._dnd_leave_timer = None

    def _on_drop_enter(self, event):
        if DND_FILES is None:
            return
        self._cancel_scheduled_drop_unhighlight()
        self._set_drop_zone_highlight(True)
        return COPY

    def _on_drop_leave(self, event):
        if DND_FILES is None:
            return

        def _unhighlight():
            self._dnd_leave_timer = None
            self._set_drop_zone_highlight(False)

        self._cancel_scheduled_drop_unhighlight()
        self._dnd_leave_timer = self.after(45, _unhighlight)

    def _set_drop_zone_highlight(self, active: bool):
        if active:
            self.upload_box.configure(
                border_width=3,
                border_color="#3b8ed0",
                fg_color=("#ddeefb", "#1f3344"),
            )
            self.upload_dnd_hint.configure(
                text="Отпустите файл здесь — он будет загружен",
                text_color="#3b8ed0",
            )
            self.upload_glyph.configure(text="📥", text_color=("#2980b9", "#85c1e9"))
        else:
            self.upload_box.configure(
                border_width=2,
                border_color=self._upload_border_idle,
                fg_color=self._upload_fg_idle,
            )
            self.upload_dnd_hint.configure(
                text=self._upload_dnd_hint_idle[0],
                text_color=self._upload_dnd_hint_idle[1],
            )
            self.upload_glyph.configure(
                text="⬇",
                text_color=("#3b8ed0", "#5dade2"),
            )

    def _on_file_drop(self, event):
        if DND_FILES is None:
            return
        self._cancel_scheduled_drop_unhighlight()
        self._set_drop_zone_highlight(False)
        for raw in self.tk.splitlist(event.data):
            path = raw.strip("{}")
            if self.load_seismic_file(path):
                break

    def load_seismic_file(self, path: str) -> bool:
        path = os.path.abspath(os.path.normpath(path))
        if not os.path.isfile(path):
            return False
        ext = os.path.splitext(path)[1].lower()
        if ext not in (".sgy", ".segy"):
            self.file_status.configure(
                text="Перетащите файл .sgy или .segy",
                text_color="#e67e22",
            )
            return False
        name = os.path.basename(path)
        self.file_status.configure(text=f"Успешно загружен: {name}", text_color="#2ecc71")
            # Открываем файл для чтения количества трасс
        with segyio.open(path, "r", ignore_geometry=True) as f:
            count = f.tracecount

            self.file_status.configure(text=f"Успешно загружен: {name}\nКоличество трасс: {count}", 
                text_color="#2ecc71")
            return True
        
        

    def open_file_dialog(self):
        path = filedialog.askopenfilename(filetypes=[("Seismic data", "*.sgy *.segy")])
        if path:
            self.load_seismic_file(path)

    def setup_view_settings(self):
        f = self.frames["Вид"]
        ctk.CTkLabel(f, text="Настройки интерфейса", font=("Arial", 24, "bold")).pack(pady=40)
        container = ctk.CTkFrame(f, fg_color="transparent")
        container.pack()
        for lbl, vals, opt in [("Тема приложения:", ["System", "Dark", "Light"], "theme"),
                               ("Масштаб:", ["80%", "100%", "120%"], "scale")]:
            r = ctk.CTkFrame(container, fg_color="transparent")
            r.pack(pady=10)
            ctk.CTkLabel(r, text=lbl, width=150, anchor="w", font=("Arial", 14)).pack(side="left")
            menu = ctk.CTkOptionMenu(r, values=vals, command=lambda v, o=opt: self.save_state(**{o: v}))
            menu.pack(side="left")
            if opt == "theme":
                self.theme_menu = menu
            else:
                self.scale_menu = menu

    def save_state(self, tab=None, theme=None, scale=None):
        if self.is_navigating:
            return
        if tab:
            self.current_state["tab"] = tab
        if theme:
            self.current_state["theme"] = theme
        if scale:
            self.current_state["scale"] = scale
        if self.current_state == self.history[self.history_index]:
            return
        self.history = self.history[: self.history_index + 1]
        self.history.append(self.current_state.copy())
        self.history_index += 1
        self.apply_state(self.current_state)

    def apply_state(self, state):
        self.is_navigating = True
        name = state["tab"]
        self.frames[name].tkraise()
        for t_name, btn in self.tab_buttons.items():
            btn.configure(
                fg_color="#3b8ed0" if t_name == name else "transparent",
                text_color="white" if t_name == name else ("gray10", "gray80"),
            )
        if name == "Главная":
            self.home_tools.pack(side="left", padx=15)
            self.analysis_tools.pack_forget()
            self.ribbon.configure(height=112, fg_color=("#f9f9f9", "#2b2b2b"))
        elif name == "Анализ":
            self.home_tools.pack_forget()
            # 5 px от верхней границы полосы, снизу компактно — как на «Главная» (высота 112)
            # Без отступа сверху — блок «Методы обработки» вплотную к верхней границе полосы
            self.analysis_tools.pack(side="left", padx=(1, 15), pady=(0, 3))
            # Чуть выше стандартной 112, чтобы поместились крупнее шрифты
            self.ribbon.configure(height=124, fg_color=("#f9f9f9", "#2b2b2b"))
        else:
            self.home_tools.pack_forget()
            self.analysis_tools.pack_forget()
            self.ribbon.configure(height=112, fg_color="transparent")
        ctk.set_appearance_mode(state["theme"])
        self.theme_menu.set(state["theme"])
        ctk.set_widget_scaling(int(state["scale"].replace("%", "")) / 100)
        self.scale_menu.set(state["scale"])
        self.btn_back.configure(
            state="normal" if self.history_index > 0 else "disabled",
            fg_color="#3b8ed0" if self.history_index > 0 else "gray30",
        )
        self.btn_forward.configure(
            state="normal" if self.history_index < len(self.history) - 1 else "disabled",
            fg_color="#3b8ed0" if self.history_index < len(self.history) - 1 else "gray30",
        )
        self.is_navigating = False

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.current_state = self.history[self.history_index].copy()
            self.apply_state(self.current_state)

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_state = self.history[self.history_index].copy()
            self.apply_state(self.current_state)


if __name__ == "__main__":
    app = App()
    app.mainloop()
