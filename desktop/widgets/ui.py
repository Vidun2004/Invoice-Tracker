"""Clean widgets + loading bar."""
import tkinter as tk
from tkinter import ttk
import threading
import customtkinter as ctk
import config


class Card(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, corner_radius=config.RADIUS,
                         border_width=1,
                         border_color=("#e2e8f0", "#2a2f3a"), **kwargs)


class KpiCard(Card):
    def __init__(self, master, label, value="—", sub="", accent=None, **kwargs):
        super().__init__(master)
        ctk.CTkLabel(self, text=label, font=config.FONTS["kpi_label"],
                     text_color=config.MUTED).pack(anchor="w", padx=14, pady=(12, 0))
        self.val = ctk.CTkLabel(self, text=value, font=config.FONTS["kpi_value"])
        self.val.pack(anchor="w", padx=14)
        self.sub = ctk.CTkLabel(self, text=sub, font=config.FONTS["small"],
                                text_color=config.MUTED)
        self.sub.pack(anchor="w", padx=14, pady=(0, 12))

    def set(self, value, sub=""):
        self.val.configure(text=value)
        self.sub.configure(text=sub)


class LoadingBar(ctk.CTkFrame):
    """Thin indeterminate progress + message. Pack at top, toggle with show/hide."""
    def __init__(self, master):
        super().__init__(master, fg_color="transparent", height=26)
        self.label = ctk.CTkLabel(self, text="", font=config.FONTS["small"],
                                  text_color=config.MUTED)
        self.label.pack(side="left", padx=4)
        self.bar = ctk.CTkProgressBar(self, width=220, height=8,
                                      corner_radius=4)
        self.bar.pack(side="left", padx=8)
        self.bar.set(0)
        self._on = False

    def show(self, msg="Loading…"):
        self.label.configure(text=msg)
        self.pack(fill="x", padx=12, pady=(8, 0))
        self._on = True
        self.bar.start()

    def hide(self, msg=""):
        if self._on:
            self.bar.stop()
            self.pack_forget()
            self._on = False
        if msg:
            self.label.configure(text=msg)


def run_bg(fn, on_done=None, on_error=None, master=None):
    """Run blocking fn() in background thread, callbacks back on UI thread."""
    def work():
        try:
            result = fn()
        except Exception as e:  # noqa: BLE001
            err = e
            if on_error and master:
                master.after(0, lambda err=err: on_error(err))
            return
        if on_done and master:
            master.after(0, lambda result=result: on_done(result))
    threading.Thread(target=work, daemon=True).start()


class DateField(ctk.CTkFrame):
    def __init__(self, master, initial="", width=200):
        super().__init__(master, fg_color="transparent")
        self.var = tk.StringVar(value=initial or "")
        try:
            from tkcalendar import DateEntry
            self.entry = DateEntry(self, textvariable=self.var, date_pattern="yyyy-MM-dd",
                                   width=18, borderwidth=1, justify="left")
            self.entry.pack(fill="x")
            self.get = self.var.get
            self.set = self.var.set
        except Exception:
            self.entry = ctk.CTkEntry(self, textvariable=self.var, width=width,
                                      corner_radius=config.RADIUS_SM,
                                      placeholder_text="YYYY-MM-DD")
            self.entry.pack(fill="x")
            self.get = self.var.get
            self.set = self.var.set


def style_table(tree: ttk.Treeview):
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Treeview", rowheight=30, font=("Segoe UI", 11), borderwidth=0)
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), borderwidth=0)
    tree.tag_configure("overdue", foreground="#dc2626")
    tree.tag_configure("paid", foreground="#16a34a")


# Backwards compat for older imports
def style_treeview(tree):
    return style_table(tree)
