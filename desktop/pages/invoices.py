"""Invoice list: simple by default, filters hidden, advance asks for PR/PO/GRN number."""
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date
import customtkinter as ctk
from widgets.ui import DateField, style_treeview, LoadingBar, run_bg
from pages.invoice_form import InvoiceFormDialog
from utils.stages import next_stage, can_transition
from utils.format import parse_date, is_overdue
import config

STAGE_HINT = {
    "PR": "Enter the PR number you received.",
    "PO": "Enter the PO number you received.",
    "GRN": "Enter the GRN number after goods received.",
    "SentToFinance": "Confirm finance has the invoice. Photo app can also do this.",
    "Paid": "Confirm payment is done.",
}
NUMBER_FIELD = {"PR": "pr_number", "PO": "po_number", "GRN": "grn_number"}


class InvoicesPage(ctk.CTkFrame):
    def __init__(self, master, sb, user, is_admin=False):
        super().__init__(master, fg_color="transparent")
        self.sb, self.user, self.is_admin = sb, user, is_admin
        self.all_rows: list[dict] = []
        self.view_rows: list[dict] = []

        # --- simple top bar ---
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 4))
        top.grid_columnconfigure(0, weight=1)
        self.v_search = tk.StringVar()
        self.search = ctk.CTkEntry(top, textvariable=self.v_search, width=320,
                                   placeholder_text="🔍  Search invoice / vendor…  (shows all by default)")
        self.search.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search.bind("<KeyRelease>", lambda _e: self.after(300, self.apply_filters))
        self.btn_filter = ctk.CTkButton(top, text="Filters ▾", width=100, fg_color="transparent",
                                        border_width=1, border_color=config.MUTED,
                                        text_color=config.MUTED, command=self.toggle_filters)
        self.btn_filter.grid(row=0, column=1, padx=4)
        ctk.CTkButton(top, text="↻", width=44, command=self.load).grid(row=0, column=2, padx=4)
        ctk.CTkButton(top, text="+ New Invoice", width=140, fg_color=config.SUCCESS,
                      hover_color=config.SUCCESS_HOVER, command=self.open_create).grid(row=0, column=3, padx=4)
        self.v_archived = tk.BooleanVar(value=False)
        if is_admin:
            ctk.CTkCheckBox(top, text="🗑 Archived", variable=self.v_archived,
                            command=self.apply_filters).grid(row=0, column=4, padx=4)

        # --- collapsible filters (hidden by default) ---
        self.filter_box = ctk.CTkFrame(self, corner_radius=config.RADIUS,
                                         border_width=config.BORDER_W, border_color=config.LINE)
        self.filters_visible = False
        self.v_type = tk.StringVar(value="All")
        self.v_stage = tk.StringVar(value="All")
        self.v_vendor = tk.StringVar(value="All")
        self.v_overdue = tk.BooleanVar(value=False)
        self.v_min = tk.StringVar()
        self.v_max = tk.StringVar()
        self._build_filters()
        self.loading = LoadingBar(self)

        # --- table ---
        wrap = ctk.CTkFrame(self, corner_radius=config.RADIUS,
                            border_width=config.BORDER_W, border_color=config.LINE)
        wrap.pack(fill="both", expand=True, padx=12, pady=8)
        cols = ("invoice_number", "vendor_name", "amount", "stage", "due_date", "flag")
        self.tree = ttk.Treeview(wrap, columns=cols, show="headings", height=17)
        style_treeview(self.tree)
        heads = {"invoice_number": "Invoice", "vendor_name": "Vendor", "amount": "Amount",
                 "stage": "Stage", "due_date": "Due", "flag": ""}
        widths = {"invoice_number": 140, "vendor_name": 200, "amount": 130,
                  "stage": 140, "due_date": 110, "flag": 90}
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], anchor="w")
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", padx=(0, 10), pady=10)
        self.tree.tag_configure("overdue", foreground="#dc2626")
        self.tree.tag_configure("paid", foreground="#16a34a")
        # status tints — whole-row background per stage for quick recognition
        for _st, _bg in (("Created", "#f1f5f9"), ("PR", "#e0f2fe"), ("PO", "#ede9fe"),
                         ("GRN", "#fef3c7"), ("SentToFinance", "#dbeafe"), ("Paid", "#dcfce7")):
            self.tree.tag_configure(f"st_{_st}", background=_bg)
        self.tree.tag_configure("archived", foreground="#94a3b8")
        self.tree.bind("<Double-1>", lambda _e: self.open_detail())
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.refresh_advance_btn())

        # legend so colors are readable without guessing
        legend = ctk.CTkFrame(self, fg_color="transparent")
        legend.pack(fill="x", padx=14, pady=(0, 2))
        for _st in ("Created", "PR", "PO", "GRN", "SentToFinance", "Paid"):
            dot = ctk.CTkFrame(legend, width=12, height=12, corner_radius=3,
                               fg_color=config.STAGE_COLORS.get(_st, config.MUTED))
            dot.pack(side="left", padx=(0, 4))
            ctk.CTkLabel(legend, text=_st, font=config.FONTS["small"],
                         text_color=config.MUTED).pack(side="left", padx=(0, 12))

        # --- bottom bar: summary + actions ---
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=12, pady=(0, 12))
        self.footer = ctk.CTkLabel(bottom, text="", font=config.FONTS["body"])
        self.footer.pack(side="left")
        ctk.CTkButton(bottom, text="Export", width=80, fg_color="transparent", border_width=1,
                      border_color=config.MUTED, text_color=config.MUTED,
                      command=self.export_csv).pack(side="left", padx=8)
        ctk.CTkButton(bottom, text="Edit", width=80, command=self.open_edit).pack(side="left", padx=4)
        ctk.CTkButton(bottom, text="Delete", width=80, fg_color=config.DANGER,
                      hover_color=config.DANGER_HOVER, command=self.delete_selected).pack(side="left", padx=4)
        self.btn_restore = ctk.CTkButton(bottom, text="↩ Restore", width=90,
                                         command=self.restore_selected)
        if is_admin:
            self.btn_restore.pack(side="left", padx=4)
        ctk.CTkLabel(bottom, text="Double-click a row to view details + proof",
                     font=config.FONTS["small"], text_color=config.MUTED).pack(side="left", padx=12)
        self.btn_adv = ctk.CTkButton(bottom, text="Next →", width=240, height=38,
                                     corner_radius=config.RADIUS,
                                     fg_color=config.ACCENT, hover_color=config.ACCENT_HOVER,
                                     text_color=config.ACCENT_INK,
                                     font=("Consolas", 12, "bold"), command=self.advance_stage)
        self.btn_adv.pack(side="right")
        self.lbl_status = ctk.CTkLabel(bottom, text="", font=config.FONTS["small"], text_color=config.MUTED)
        self.lbl_status.pack(side="right", padx=10)
        self.load()

    def _build_filters(self):
        f = self.filter_box
        for i in range(4):
            f.grid_columnconfigure(i, weight=1)
        ctk.CTkLabel(f, text="Type").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 0))
        ctk.CTkLabel(f, text="Stage").grid(row=0, column=1, sticky="w", padx=12, pady=(10, 0))
        ctk.CTkLabel(f, text="Vendor").grid(row=0, column=2, sticky="w", padx=12, pady=(10, 0))
        ctk.CTkLabel(f, text="Dates / Amount").grid(row=0, column=3, sticky="w", padx=12, pady=(10, 0))
        ctk.CTkOptionMenu(f, variable=self.v_type, values=["All", "standard", "straight"],
                          command=lambda _v: self.apply_filters()).grid(row=1, column=0, sticky="ew", padx=12)
        ctk.CTkOptionMenu(f, variable=self.v_stage,
                          values=["All", "Created", "PR", "PO", "GRN", "SentToFinance", "Paid"],
                          command=lambda _v: self.apply_filters()).grid(row=1, column=1, sticky="ew", padx=12)
        self.opt_vendor = ctk.CTkOptionMenu(f, variable=self.v_vendor, values=["All"],
                                            command=lambda _v: self.apply_filters())
        self.opt_vendor.grid(row=1, column=2, sticky="ew", padx=12)
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.grid(row=1, column=3, sticky="ew", padx=12)
        self.d_from = DateField(row, width=110)
        self.d_from.pack(side="left", padx=2)
        self.d_to = DateField(row, width=110)
        self.d_to.pack(side="left", padx=2)
        row2 = ctk.CTkFrame(f, fg_color="transparent")
        row2.grid(row=2, column=0, columnspan=4, sticky="ew", padx=12, pady=8)
        ctk.CTkCheckBox(row2, text="Overdue only", variable=self.v_overdue,
                        command=self.apply_filters).pack(side="left", padx=4)
        ctk.CTkLabel(row2, text="Min").pack(side="left", padx=(12, 2))
        ctk.CTkEntry(row2, textvariable=self.v_min, width=90).pack(side="left")
        ctk.CTkLabel(row2, text="Max").pack(side="left", padx=(8, 2))
        ctk.CTkEntry(row2, textvariable=self.v_max, width=90).pack(side="left")
        ctk.CTkButton(row2, text="Apply", width=80, command=self.apply_filters).pack(side="left", padx=8)
        ctk.CTkButton(row2, text="Clear", width=80, fg_color="transparent", border_width=1,
                      border_color=config.MUTED, text_color=config.MUTED,
                      command=self.clear_filters).pack(side="left")

    def toggle_filters(self):
        if self.filters_visible:
            self.filter_box.pack_forget()
            self.btn_filter.configure(text="Filters ▾")
            self.filters_visible = False
        else:
            self.filter_box.pack(fill="x", padx=12, pady=4)
            self.btn_filter.configure(text="Filters ▴")
            self.filters_visible = True

    # --- data ---
    def load(self):
        self.loading.show("Loading invoices…")
        self.lbl_status.configure(text="")

        def fetch():
            res = self.sb.table("invoices").select("*").order("created_at", desc=True).limit(config.PAGE_LIMIT).execute()
            rows = res.data or []
            proof_ids = set()
            try:
                ids = [r["id"] for r in rows[:200]]
                if ids:
                    pr = self.sb.table("finance_proofs").select("invoice_id").in_("invoice_id", ids).execute()
                    proof_ids = {r["invoice_id"] for r in (pr.data or [])}
            except Exception:
                pass
            return rows, proof_ids

        def done(result):
            self.loading.hide()
            rows, proof_ids = result
            self.all_rows = rows
            self.proof_ids = proof_ids
            vendors = sorted({r.get("vendor_name", "") for r in self.all_rows if r.get("vendor_name")})
            self.opt_vendor.configure(values=["All"] + vendors)
            self.apply_filters()
            self.lbl_status.configure(text=f"{len(self.all_rows)} invoices")

        def fail(e):
            self.loading.hide()
            self.lbl_status.configure(text="Error")
            messagebox.showerror("Load failed", str(e)[:300])

        run_bg(fetch, on_done=done, on_error=fail, master=self)

    def clear_filters(self):
        self.v_search.set("")
        self.v_type.set("All")
        self.v_stage.set("All")
        self.v_vendor.set("All")
        self.v_overdue.set(False)
        self.d_from.set("")
        self.d_to.set("")
        self.v_min.set("")
        self.v_max.set("")
        self.apply_filters()

    def apply_filters(self):
        q = self.v_search.get().strip().lower()
        typ, stg, ven = self.v_type.get(), self.v_stage.get(), self.v_vendor.get()
        d_from = parse_date(self.d_from.get())
        d_to = parse_date(self.d_to.get())
        try:
            fmin = float(self.v_min.get()) if self.v_min.get().strip() else None
        except ValueError:
            fmin = None
        try:
            fmax = float(self.v_max.get()) if self.v_max.get().strip() else None
        except ValueError:
            fmax = None
        out = []
        show_archived = getattr(self, "v_archived", None) and self.v_archived.get()
        for r in self.all_rows:
            is_del = bool(r.get("deleted_at"))
            if show_archived:
                if not (self.is_admin and is_del):
                    continue
            elif is_del:
                continue
            if typ != "All" and r.get("type") != typ:
                continue
            if stg != "All" and r.get("current_stage") != stg:
                continue
            if ven != "All" and r.get("vendor_name") != ven:
                continue
            if self.v_overdue.get() and not is_overdue(r):
                continue
            if q and q not in " ".join(str(r.get(k, "")) for k in
                    ("invoice_number", "vendor_name", "pr_number", "po_number", "grn_number")).lower():
                continue
            d_inv = parse_date(r.get("invoice_date") or "")
            if d_from and (not d_inv or d_inv < d_from):
                continue
            if d_to and (not d_inv or d_inv > d_to):
                continue
            amt = float(r.get("amount") or 0)
            if fmin is not None and amt < fmin:
                continue
            if fmax is not None and amt > fmax:
                continue
            out.append(r)
        self.view_rows = out
        self.render()

    def render(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        total = 0.0
        proof_ids = getattr(self, "proof_ids", set())
        for r in self.view_rows:
            st = r.get("current_stage", "")
            tags, flags = [f"st_{st}"], []
            if is_overdue(r):
                tags.append("overdue")
                flags.append("⚠ overdue")
            elif r.get("current_stage") == "Paid":
                tags.append("paid")
                flags.append("✓ paid")
            if r["id"] in proof_ids:
                flags.append("📷 proof")
            if r.get("deleted_at"):
                tags.append("archived")
                flags.append("🗑 archived")
            flag = " · ".join(flags)
            stage = r.get("current_stage", "")
            if r.get("type") == "standard" and stage in ("PR", "PO", "GRN"):
                num = r.get({"PR": "pr_number", "PO": "po_number", "GRN": "grn_number"}[stage]) or ""
                stage = f"{stage} ({num})" if num else stage
            self.tree.insert("", "end", iid=r["id"], tags=tuple(tags), values=(
                r.get("invoice_number", ""), r.get("vendor_name", ""),
                f"{r.get('currency','LKR')} {float(r.get('amount') or 0):,.2f}",
                stage, r.get("due_date", "") or "", flag))
            total += float(r.get("amount") or 0)
        self.footer.configure(text=f"{len(self.view_rows)} invoices  •  Total {total:,.2f}")
        self.refresh_advance_btn()
        if hasattr(self, "btn_restore"):
            arch = bool(getattr(self, "v_archived", None) and self.v_archived.get())
            self.btn_restore.configure(state="normal" if arch else "disabled")

    # --- selection + advance ---
    def selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        _id = sel[0]
        return next((r for r in self.all_rows if r["id"] == _id), None)

    def refresh_advance_btn(self):
        row = self.selected()
        if not row:
            self.btn_adv.configure(text="Select an invoice →", state="disabled")
            return
        if row.get("deleted_at"):
            self.btn_adv.configure(text="🗑 Archived — restore first", state="disabled")
            return
        nxt = next_stage(row["type"], row["current_stage"])
        if not nxt:
            self.btn_adv.configure(text="✓ Completed (Paid)", state="disabled")
        else:
            self.btn_adv.configure(text=f"Move to {nxt}  →", state="normal")

    def audit(self, invoice_id, frm, to, action, note=""):
        self.sb.table("audit_log").insert({
            "invoice_id": invoice_id, "from_stage": frm, "to_stage": to,
            "action": action, "note": note, "source": "desktop",
            "actor": self.user.id if self.user else None}).execute()

    def open_create(self):
        InvoiceFormDialog(self, self.sb, self.user, None, self.load, self.audit)

    def open_detail(self):
        row = self.selected()
        if not row:
            return
        ProofDialog(self, self.sb, row)

    def open_edit(self):
        row = self.selected()
        if not row:
            messagebox.showinfo("Invoices", "Click a row first, then Edit.")
            return
        InvoiceFormDialog(self, self.sb, self.user, row, self.load, self.audit)

    def delete_selected(self):
        row = self.selected()
        if not row:
            messagebox.showinfo("Invoices", "Click a row first, then Delete.")
            return
        if not self.is_admin:
            messagebox.showinfo("Invoices", "Admin only — ask an admin to delete.")
            return
        if not messagebox.askyesno("Delete", f"Archive {row['invoice_number']}?\nIt hides from lists but history is kept."):
            return
        try:
            from datetime import datetime, timezone
            self.sb.table("invoices").update(
                {"deleted_at": datetime.now(timezone.utc).isoformat()}).eq("id", row["id"]).execute()
            self.audit(row["id"], row["current_stage"], row["current_stage"], "delete", "archived via desktop")
            self.load()
        except Exception as e:
            messagebox.showerror("Delete failed", str(e)[:250])

    def restore_selected(self):
        row = self.selected()
        if not row:
            messagebox.showinfo("Archived", "Select an archived invoice first.")
            return
        if not self.is_admin:
            messagebox.showinfo("Archived", "Admin only.")
            return
        if not row.get("deleted_at"):
            messagebox.showinfo("Archived", "This invoice is not archived.")
            return
        try:
            self.sb.table("invoices").update({"deleted_at": None}).eq("id", row["id"]).execute()
            self.audit(row["id"], row["current_stage"], row["current_stage"], "restore", "restored via desktop")
            self.load()
        except Exception as e:
            messagebox.showerror("Restore failed", str(e)[:250])

    def advance_stage(self):
        row = self.selected()
        if not row:
            messagebox.showinfo("Invoices", "Click a row first, then Move.")
            return
        nxt = next_stage(row["type"], row["current_stage"])
        if not nxt:
            messagebox.showinfo("Invoices", "Already paid — done.")
            return
        if not can_transition(row["type"], row["current_stage"], nxt):
            messagebox.showerror("Invoices", "That move is not allowed.")
            return
        AdvanceDialog(self, row, nxt, self._confirm_advance)

    def _confirm_advance(self, row, nxt, number):
        try:
            payload = {"current_stage": nxt}
            if nxt in NUMBER_FIELD and number:
                payload[NUMBER_FIELD[nxt]] = number
            self.sb.table("invoices").update(payload).eq("id", row["id"]).execute()
            note = f"{NUMBER_FIELD[nxt]}={number}" if nxt in NUMBER_FIELD else "manual advance desktop"
            self.audit(row["id"], row["current_stage"], nxt, "stage_change", note)
            self.load()
        except Exception as e:
            messagebox.showerror("Move failed", str(e))

    def export_csv(self):
        if not self.view_rows:
            messagebox.showinfo("Export", "Nothing to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        keys = ["invoice_number", "vendor_name", "amount", "currency", "type",
                "current_stage", "invoice_date", "due_date", "pr_number", "po_number", "grn_number"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(self.view_rows)
        messagebox.showinfo("Export", f"Exported {len(self.view_rows)} rows.")


class AdvanceDialog(ctk.CTkToplevel):
    """Pretty one-step move dialog. Asks for PR/PO/GRN number when needed."""
    def __init__(self, master, row, nxt, on_confirm):
        super().__init__(master)
        self.row, self.nxt, self.on_confirm = row, nxt, on_confirm
        self.title(f"Move to {nxt}")
        self.geometry("400x340")
        self.minsize(360, 300)
        self.grab_set()
        ctk.CTkLabel(self, text=row["invoice_number"], font=config.FONTS["h2"]).pack(padx=20, pady=(18, 0))
        ctk.CTkLabel(self, text=f"{row['current_stage']}  →  {nxt}",
                     font=config.FONTS["body"]).pack(padx=20)
        ctk.CTkLabel(self, text=STAGE_HINT.get(nxt, ""), font=config.FONTS["small"],
                     text_color=config.MUTED, wraplength=340).pack(padx=20, pady=8)
        self.var_num = tk.StringVar(value=row.get(NUMBER_FIELD.get(nxt, ""), "") or "")
        if nxt in NUMBER_FIELD:
            ctk.CTkLabel(self, text=f"{nxt} number *").pack(anchor="w", padx=20)
            self.entry = ctk.CTkEntry(self, textvariable=self.var_num,
                                      placeholder_text=f"e.g. {nxt}-2026-001")
            self.entry.pack(fill="x", padx=20, pady=4)
            self.after(120, lambda: self.entry.focus_set())
            self.bind("<Return>", lambda _e: self.confirm())
        else:
            self.entry = None
        self.err = ctk.CTkLabel(self, text="", text_color=config.DANGER, font=config.FONTS["small"])
        self.err.pack(padx=20)
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=14, side="bottom")
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1,
                      border_color=config.MUTED, text_color=config.MUTED,
                      command=self.destroy).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(btns, text=f"Confirm → {nxt}", fg_color=config.ACCENT,
                      command=self.confirm).pack(side="right", expand=True, fill="x", padx=(6, 0))

    def confirm(self):
        num = self.var_num.get().strip() if self.entry else ""
        if self.nxt in NUMBER_FIELD and not num:
            self.err.configure(text=f"Please enter the {self.nxt} number.")
            return
        self.destroy()
        self.on_confirm(self.row, self.nxt, num or None)


class ProofDialog(ctk.CTkToplevel):
    """View-only: clearly sectioned invoice + proof. Double-click a row to open."""
    def __init__(self, master, sb, row):
        super().__init__(master)
        self.sb, self.row = sb, row
        self.title(row.get('invoice_number', 'Details'))
        self.minsize(440, 420)
        self.grab_set()
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.after(40, self._autosize)

        # --- header: number + stage pill (fixed top) ---
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 4))
        ctk.CTkLabel(head, text=row.get('invoice_number', ''), font=config.FONTS["title"]).pack(side="left")
        stage = row.get('current_stage', '')
        pill = ctk.CTkLabel(head, text=f"  {stage}  ", font=config.FONTS["small"],
                            fg_color=config.STAGE_COLORS.get(stage, config.MUTED),
                            text_color="white", corner_radius=12)
        pill.pack(side="right", pady=6)

        # --- scrollable middle (info + proof) so bottom never clips ---
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=0)

        # --- info card ---
        card = ctk.CTkFrame(scroll, corner_radius=config.RADIUS,
                            border_width=1, border_color=config.LINE)
        card.pack(fill="x", padx=12, pady=8)
        card.grid_columnconfigure((0, 1), weight=1, uniform="info")
        self._field(card, 0, 0, "VENDOR", row.get('vendor_name', '—'))
        try:
            amt = f"{row.get('currency','LKR')} {float(row.get('amount') or 0):,.2f}"
        except (TypeError, ValueError):
            amt = str(row.get('amount', '—'))
        self._field(card, 0, 1, "AMOUNT", amt)
        self._field(card, 1, 0, "TYPE", (row.get('type', '—')).upper())
        self._field(card, 1, 1, "DUE DATE", row.get('due_date', '') or '—')
        self._field(card, 2, 0, "INVOICE DATE", row.get('invoice_date', '') or '—')
        prpo = "   ".join(f"{k.replace('_number','').upper()}: {row.get(k)}" for k in
                          ("pr_number", "po_number", "grn_number") if row.get(k))
        self._field(card, 2, 1, "REFS", prpo or '—')
        notes = (row.get('notes') or '').strip()
        if notes:
            ctk.CTkLabel(card, text="NOTES", font=("Segoe UI", 10, "bold"),
                         text_color=config.MUTED).grid(row=3, column=0, sticky="w", padx=14, pady=(8, 0))
            ctk.CTkLabel(card, text=notes[:300], font=config.FONTS["small"],
                         wraplength=480, justify="left").grid(row=4, column=0, columnspan=2,
                                                              sticky="w", padx=14, pady=(0, 12))

        # --- proof section ---
        ctk.CTkLabel(scroll, text="FINANCE PHOTO PROOF", font=("Segoe UI", 11, "bold"),
                     text_color=config.MUTED).pack(padx=14, pady=(8, 0), anchor="w")
        proof_card = ctk.CTkFrame(scroll, corner_radius=config.RADIUS,
                                  border_width=1, border_color=config.LINE)
        proof_card.pack(fill="x", padx=12, pady=6)
        self.status = ctk.CTkLabel(proof_card, text="Loading…", font=("Segoe UI", 12, "bold"))
        self.status.pack(padx=14, pady=(12, 0), anchor="w")
        self.prog = ctk.CTkProgressBar(proof_card, width=440, height=6, corner_radius=3)
        self.prog.pack(padx=14, pady=6, fill="x")
        self.prog.start()
        self.meta = ctk.CTkLabel(proof_card, text="", font=config.FONTS["small"],
                                 text_color=config.MUTED, justify="left")
        self.meta.pack(padx=14, anchor="w")
        self.img_frame = ctk.CTkFrame(proof_card, corner_radius=config.RADIUS_SM,
                                      border_width=1, border_color=config.LINE)
        self.img_frame.pack(padx=14, pady=10, fill="both", expand=True)
        self.img_label = ctk.CTkLabel(self.img_frame, text="—")
        self.img_label.pack(fill="both", expand=True, padx=8, pady=8)
        # --- Close pinned at bottom, always visible ---
        ctk.CTkButton(self, text="Close", width=200, corner_radius=config.RADIUS_SM,
                      fg_color=config.ACCENT, hover_color=config.ACCENT_HOVER,
                      command=self.destroy).grid(row=2, column=0, padx=18, pady=12)
        self._load()

    def _field(self, parent, r, c, label, value):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=r, column=c, sticky="ew", padx=14, pady=6)
        ctk.CTkLabel(box, text=label, font=("Segoe UI", 10, "bold"),
                     text_color=config.MUTED).pack(anchor="w")
        ctk.CTkLabel(box, text=str(value), font=("Segoe UI", 13, "bold"),
                     wraplength=220, justify="left").pack(anchor="w")

    def _autosize(self):
        """Fit window to content, capped to 90% of screen."""
        try:
            self.update_idletasks()
            w = min(max(self.winfo_reqwidth() + 20, 460), int(self.winfo_screenwidth() * 0.9))
            h = min(max(self.winfo_reqheight() + 20, 420), int(self.winfo_screenheight() * 0.9))
            x = max((self.winfo_screenwidth() - w) // 2, 0)
            y = max((self.winfo_screenheight() - h) // 2, 0)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _load(self):
        import threading

        def fetch():
            res = self.sb.table("finance_proofs").select("*").eq(
                "invoice_id", self.row["id"]).order("captured_at", desc=True).limit(1).execute()
            return (res.data or [None])[0]

        def done(rec):
            self.prog.stop()
            self.prog.pack_forget()
            if not rec:
                self.status.configure(text="⊘  No photo proof yet")
                self.meta.configure(text="This invoice has not been sent with a photo yet.")
                self.img_label.configure(text="—")
                self.after(30, self._autosize)
                return
            cap = (rec.get("captured_at") or "").replace("T", " ")[:19]
            self.meta.configure(text=f"✓ Sent to finance: {cap}  •  {self.row.get('invoice_number')}")
            self.status.configure(text="Loading photo…")
            self._load_img(rec)

        def fail(e):
            self.prog.stop()
            self.prog.pack_forget()
            self.status.configure(text=f"Load failed: {str(e)[:140]}")

        threading.Thread(target=lambda: self._bg(fetch, done, fail), daemon=True).start()

    def _bg(self, fetch, done, fail):
        try:
            out = fetch()
        except Exception as e:  # noqa: BLE001
            err = e
            self.after(0, lambda err=err: fail(err))
            return
        self.after(0, lambda out=out: done(out))

    def _load_img(self, rec):
        import threading

        def fetch_img():
            data = self.sb.storage.from_("finance-proofs").download(rec["photo_path"])
            return bytes(data) if not isinstance(data, (bytes, bytearray)) else data

        def done_img(raw):
            from io import BytesIO
            from PIL import Image
            try:
                img = Image.open(BytesIO(raw))
                img.thumbnail((440, 340))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self.img_label.configure(image=ctk_img, text="")
                self._img = ctk_img
                self.status.configure(text="✓  Photo proof")
                self.after(30, self._autosize)
            except Exception as e:  # noqa: BLE001
                self.status.configure(text=f"Image error: {e}")

        def fail_img(e):
            self.status.configure(text=f"Photo unavailable: {str(e)[:140]}")

        threading.Thread(target=lambda: self._bg(fetch_img, done_img, fail_img), daemon=True).start()
