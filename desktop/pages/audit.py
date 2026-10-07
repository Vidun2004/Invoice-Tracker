"""Audit trail: filter by invoice search, source, date; read-only."""
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from widgets.ui import DateField, style_treeview, LoadingBar, run_bg
from utils.format import parse_date
import config


class AuditPage(ctk.CTkFrame):
    def __init__(self, master, sb, user):
        super().__init__(master, fg_color="transparent")
        self.sb = sb
        self.rows: list[dict] = []

        bar = ctk.CTkFrame(self, corner_radius=config.RADIUS,
                           border_width=config.BORDER_W, border_color=config.LINE)
        bar.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(bar, text="Invoice search").pack(side="left", padx=(12, 2))
        self.v_q = tk.StringVar()
        e = ctk.CTkEntry(bar, textvariable=self.v_q, width=220, placeholder_text="INV-001 or invoice id")
        e.pack(side="left", padx=6)
        e.bind("<Return>", lambda _e: self.load())
        ctk.CTkLabel(bar, text="Source").pack(side="left", padx=(10, 2))
        self.v_src = tk.StringVar(value="All")
        ctk.CTkOptionMenu(bar, variable=self.v_src, values=["All", "desktop", "web"],
                          width=120, command=lambda _v: self.render()).pack(side="left", padx=6)
        ctk.CTkButton(bar, text="↻ Load", width=90, command=self.load).pack(side="left", padx=8)
        self.lbl = ctk.CTkLabel(bar, text="", font=config.FONTS["small"], text_color=config.MUTED)
        self.lbl.pack(side="right", padx=12)
        self.loading = LoadingBar(self)

        wrap = ctk.CTkFrame(self, corner_radius=config.RADIUS,
                            border_width=config.BORDER_W, border_color=config.LINE)
        wrap.pack(fill="both", expand=True, padx=12, pady=6)
        cols = ("created_at", "invoice", "action", "from_stage", "to_stage", "source", "note")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=18)
        style_treeview(self.tree)
        for c in cols:
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=130 if c != "note" else 260)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", padx=(0, 10), pady=10)
        self.load()

    def load(self):
        self.loading.show("Loading audit…")
        q = self.v_q.get().strip()

        def fetch():
            query = self.sb.table("audit_log").select("*").order("created_at", desc=True).limit(500)
            res = query.execute()
            rows = res.data or []
            if q:
                inv = self.sb.table("invoices").select("id,invoice_number").ilike(
                    "invoice_number", f"%{q}%").limit(50).execute().data or []
                ids = {r["id"] for r in inv}
                rows = [r for r in rows if r.get("invoice_id") in ids or q in str(r.get("invoice_id", ""))]
                num = {r["id"]: r["invoice_number"] for r in inv}
                for r in rows:
                    r["_inv"] = num.get(r.get("invoice_id"), str(r.get("invoice_id"))[:8])
            else:
                for r in rows:
                    r["_inv"] = str(r.get("invoice_id"))[:8]
            return rows

        def done(rows):
            self.loading.hide()
            self.rows = rows
            self.render()

        def fail(e):
            self.loading.hide()
            messagebox.showerror("Audit load failed", str(e)[:300])

        run_bg(fetch, on_done=done, on_error=fail, master=self)

    def render(self):
        src = self.v_src.get()
        for i in self.tree.get_children():
            self.tree.delete(i)
        n = 0
        for r in self.rows:
            if src != "All" and r.get("source") != src:
                continue
            self.tree.insert("", "end", values=(
                (r.get("created_at") or "")[:19].replace("T", " "), r.get("_inv", ""),
                r.get("action", ""), r.get("from_stage", "") or "",
                r.get("to_stage", "") or "", r.get("source", ""), r.get("note", "") or ""))
            n += 1
        self.lbl.configure(text=f"{n} events")
