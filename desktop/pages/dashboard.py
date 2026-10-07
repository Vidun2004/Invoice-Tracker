"""Dashboard: KPI cards + stage/type breakdown + overdue + recent activity."""
from collections import Counter
import customtkinter as ctk
from tkinter import messagebox
from widgets.ui import KpiCard, LoadingBar, run_bg
from utils.format import fmt_money, is_overdue
import config


class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, sb, user, goto_invoices=None):
        super().__init__(master, fg_color="transparent")
        self.sb = sb
        self.user = user
        self.goto_invoices = goto_invoices

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(header, text="Dashboard", font=config.FONTS["title"]).pack(side="left")
        ctk.CTkLabel(header, text=config.APP_SUBTITLE, font=config.FONTS["small"],
                     text_color=config.MUTED).pack(side="left", padx=10, pady=6)
        self.btn_refresh = ctk.CTkButton(header, text="↻ Refresh", width=110, corner_radius=config.RADIUS_SM, command=self.load)
        self.btn_refresh.pack(side="right")
        self.status = ctk.CTkLabel(header, text="", font=config.FONTS["small"], text_color=config.MUTED)
        self.status.pack(side="right", padx=10)
        self.loading = LoadingBar(self)

        self.cards = ctk.CTkFrame(self, fg_color="transparent")
        self.cards.pack(fill="x", padx=12)
        for i in range(4):
            self.cards.grid_columnconfigure(i, weight=1, uniform="kpi")
        self.k_total = KpiCard(self.cards, "Total invoices", accent=config.ACCENT)
        self.k_value = KpiCard(self.cards, "Total value", accent=config.WARNING)
        self.k_pending = KpiCard(self.cards, "Pending value", accent=config.DANGER)
        self.k_overdue = KpiCard(self.cards, "Overdue", accent="#7c3aed")
        for i, k in enumerate((self.k_total, self.k_value, self.k_pending, self.k_overdue)):
            k.grid(row=0, column=i, sticky="nsew", padx=6, pady=6)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="both", expand=True, padx=12, pady=6)
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=1)
        bottom.grid_rowconfigure(0, weight=1)

        self.stage_box = ctk.CTkFrame(bottom, corner_radius=config.RADIUS,
                                       border_width=config.BORDER_W, border_color=config.LINE)
        self.stage_box.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        ctk.CTkLabel(self.stage_box, text="By stage", font=config.FONTS["h2"]).pack(anchor="w", padx=14, pady=(12, 4))
        self.stage_lines = ctk.CTkLabel(self.stage_box, text="—", font=config.FONTS["body"], justify="left")
        self.stage_lines.pack(anchor="w", padx=14, pady=6)

        right = ctk.CTkFrame(bottom, corner_radius=config.RADIUS,
                           border_width=config.BORDER_W, border_color=config.LINE)
        right.grid(row=0, column=1, sticky="nsew", padx=6, pady=6)
        ctk.CTkLabel(right, text="Needs attention (overdue / unpaid)", font=config.FONTS["h2"]).pack(
            anchor="w", padx=14, pady=(12, 4))
        self.attn = ctk.CTkTextbox(right, height=180)
        self.attn.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.load()

    def load(self):
        self.btn_refresh.configure(state="disabled")
        self.loading.show("Loading dashboard…")
        self.status.configure(text="")

        def fetch():
            res = self.sb.table("invoices").select(
                "invoice_number,vendor_name,amount,currency,type,current_stage,due_date,deleted_at"
            ).order("created_at", desc=True).limit(config.PAGE_LIMIT).execute()
            return [r for r in (res.data or []) if not r.get("deleted_at")]

        def done(rows):
            self.loading.hide()
            self.btn_refresh.configure(state="normal")
            self._render(rows)

        def fail(e):
            self.loading.hide()
            self.btn_refresh.configure(state="normal")
            self.status.configure(text="Error")
            messagebox.showerror("Dashboard failed", str(e)[:300])

        run_bg(fetch, on_done=done, on_error=fail, master=self)

    def _render(self, rows):
        total_val = sum(float(r.get("amount") or 0) for r in rows)
        pending = sum(float(r.get("amount") or 0) for r in rows if r.get("current_stage") != "Paid")
        overdue = [r for r in rows if is_overdue(r)]
        cur = rows[0].get("currency", config.CURRENCY_DEFAULT) if rows else config.CURRENCY_DEFAULT
        self.k_total.set(str(len(rows)), f"{Counter(r.get('type') for r in rows).get('standard',0)} standard · {Counter(r.get('type') for r in rows).get('straight',0)} straight")
        self.k_value.set(fmt_money(total_val, cur), "all invoices")
        self.k_pending.set(fmt_money(pending, cur), "unpaid")
        self.k_overdue.set(str(len(overdue)), f"{fmt_money(sum(float(r.get('amount') or 0) for r in overdue), cur)} overdue")
        by_stage = Counter(r.get("current_stage", "?") for r in rows)
        order = ["Created", "PR", "PO", "GRN", "SentToFinance", "Paid"]
        lines = [f"{s:<14} {by_stage.get(s,0):>4}" for s in order if by_stage.get(s, 0)]
        self.stage_lines.configure(text="\n".join(lines) if lines else "No data")
        self.attn.delete("1.0", "end")
        if not overdue:
            self.attn.insert("end", "All clear — nothing overdue.")
        else:
            for r in overdue[:30]:
                self.attn.insert("end", f"{r['invoice_number']} · {r.get('vendor_name','')} · {fmt_money(r.get('amount'), r.get('currency','LKR'))} · due {r.get('due_date')}\n")
        self.status.configure(text=f"{len(rows)} loaded")
