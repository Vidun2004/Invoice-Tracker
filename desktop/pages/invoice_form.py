"""Create/Edit dialog: auto invoice number (editable), date pickers, loading save."""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from widgets.ui import DateField
from utils.invoice_no import generate_invoice_number, is_duplicate_error
import config


class InvoiceFormDialog(ctk.CTkToplevel):
    def __init__(self, master, sb, user, row, on_save, audit_fn):
        super().__init__(master)
        self.sb, self.user, self.row = sb, user, row
        self.on_save, self.audit_fn = on_save, audit_fn
        self.title("Edit invoice" if row else "New invoice")
        self.geometry("480x660")
        self.minsize(440, 580)
        self.grab_set()
        self.bind("<Control-s>", lambda _e: self.save())
        self.saving = False

        ctk.CTkLabel(self, text="Edit invoice" if row else "New invoice",
                     font=config.FONTS["h2"]).pack(anchor="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(self, text="Invoice number is auto-filled — you can change it.",
                     font=config.FONTS["small"], text_color=config.MUTED).pack(anchor="w", padx=18)

        body = ctk.CTkScrollableFrame(self, corner_radius=config.RADIUS_SM)
        body.pack(fill="both", expand=True, padx=12, pady=10)
        self.entries: dict = {}
        r = row or {}
        auto_no = r.get("invoice_number", "") or ("" if row else generate_invoice_number(config.INVOICE_PREFIX))
        self._add_invoice_no(body, auto_no, is_new=row is None)
        self._add_vendor(body, r.get("vendor_name", "") or "")
        self._add_entry(body, "amount", "Amount *", str(r.get("amount", "")))
        self._add_option(body, "currency", "Currency", config.CURRENCIES,
                         r.get("currency", config.CURRENCY_DEFAULT))
        self.date_invoice = self._add_date(body, "Invoice date *", r.get("invoice_date", ""))
        self.date_due = self._add_date(body, "Due date", r.get("due_date", ""))
        if row is not None and any(row.get(k) for k in ("pr_number", "po_number", "grn_number")):
            info = "  •  ".join(f"{k.replace('_number','').upper()}: {row.get(k)}" for k in
                                ("pr_number", "po_number", "grn_number") if row.get(k))
            ctk.CTkLabel(body, text=info, font=config.FONTS["small"],
                         text_color=config.MUTED).pack(anchor="w", padx=6, pady=6)
        if row is None:
            self._add_option(body, "type", "Type * (cannot change later)", ["standard", "straight"], "standard")
        else:
            ctk.CTkLabel(body, text=f"Type: {row.get('type')}   Stage: {row.get('current_stage')}",
                         font=config.FONTS["small"], text_color=config.MUTED).pack(anchor="w", padx=6, pady=6)
        ctk.CTkLabel(body, text="Notes").pack(anchor="w", padx=6)
        self.notes = ctk.CTkTextbox(body, height=70, corner_radius=config.RADIUS_SM)
        self.notes.pack(fill="x", padx=6, pady=4)
        self.notes.insert("1.0", r.get("notes", "") or "")

        self.err = ctk.CTkLabel(self, text="", text_color=config.DANGER, font=config.FONTS["small"],
                                wraplength=420)
        self.err.pack(padx=18)
        self.prog = ctk.CTkProgressBar(self, width=420, height=6, corner_radius=3)
        row_btn = ctk.CTkFrame(self, fg_color="transparent")
        row_btn.pack(fill="x", padx=18, pady=(0, 14))
        ctk.CTkButton(row_btn, text="Cancel", fg_color="transparent", border_width=1,
                      corner_radius=config.RADIUS_SM,
                      command=self.destroy).pack(side="right", padx=6)
        self.btn_save = ctk.CTkButton(row_btn, text="Save (Ctrl+S)", corner_radius=config.RADIUS_SM,
                                      fg_color=config.ACCENT, hover_color=config.ACCENT_HOVER,
                                      command=self.save)
        self.btn_save.pack(side="right")

    def _add_invoice_no(self, parent, initial, is_new):
        ctk.CTkLabel(parent, text="Invoice number * (auto, editable)").pack(anchor="w", padx=6, pady=(8, 0))
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=6)
        v = tk.StringVar(value=initial)
        ctk.CTkEntry(row, textvariable=v, corner_radius=config.RADIUS_SM).pack(side="left", fill="x", expand=True)
        if is_new:
            ctk.CTkButton(row, text="↻", width=40, corner_radius=config.RADIUS_SM,
                          command=lambda: v.set(generate_invoice_number(config.INVOICE_PREFIX))).pack(side="left", padx=6)
        self.entries["invoice_number"] = v

    def _add_vendor(self, parent, initial):
        ctk.CTkLabel(parent, text="Vendor * (pick or type new)").pack(anchor="w", padx=6, pady=(8, 0))
        try:
            names = [x["name"] for x in
                     self.sb.table("vendors").select("name").order("name").limit(500).execute().data or []]
        except Exception:
            names = []
        if initial and initial not in names:
            names = [initial] + names
        self.vendor_combo = ctk.CTkComboBox(parent, values=names or ["—"], width=400)
        self.vendor_combo.pack(fill="x", padx=6)
        self.vendor_combo.set(initial or "")

    def _add_entry(self, parent, key, label, initial):
        ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=6, pady=(8, 0))
        v = tk.StringVar(value=initial or "")
        ctk.CTkEntry(parent, textvariable=v, corner_radius=config.RADIUS_SM).pack(fill="x", padx=6)
        self.entries[key] = v

    def _add_option(self, parent, key, label, values, initial):
        ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=6, pady=(8, 0))
        v = tk.StringVar(value=initial)
        ctk.CTkOptionMenu(parent, variable=v, values=values).pack(fill="x", padx=6)
        self.entries[key] = v

    def _add_date(self, parent, label, initial):
        ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=6, pady=(8, 0))
        f = DateField(parent, initial=initial or "")
        f.pack(fill="x", padx=6)
        return f

    def _fail(self, msg):
        self.err.configure(text=msg)

    def _set_saving(self, on):
        self.saving = on
        self.btn_save.configure(text="Saving…", state="disabled" if on else "normal")
        if on:
            self.prog.pack(padx=18, pady=4)
            self.prog.start()
        else:
            self.prog.stop()
            self.prog.pack_forget()

    def save(self):
        if self.saving:
            return
        g = lambda k: self.entries[k].get().strip()
        vendor = self.vendor_combo.get().strip()
        inv_no, amount_s = g("invoice_number"), g("amount")
        if not inv_no or not vendor or not amount_s:
            self._fail("Invoice number, vendor and amount are required.")
            return
        try:
            amount = float(amount_s)
            if amount < 0:
                raise ValueError
        except ValueError:
            self._fail("Amount must be a positive number.")
            return
        inv_date = self.date_invoice.get().strip()
        due_date = self.date_due.get().strip() or None
        if not inv_date:
            self._fail("Invoice date is required (pick from calendar).")
            return
        payload = {
            "invoice_number": inv_no, "vendor_name": vendor, "amount": amount,
            "currency": g("currency") or config.CURRENCY_DEFAULT,
            "invoice_date": inv_date, "due_date": due_date,
            "notes": self.notes.get("1.0", "end").strip() or None,
        }
        # vendor auto-create with confirmation
        known = []
        try:
            known = [x["name"] for x in
                     self.sb.table("vendors").select("name").limit(500).execute().data or []]
        except Exception:
            pass
        add_vendor = bool(vendor and vendor not in known)
        if add_vendor:
            if not messagebox.askyesno("New vendor", f"Add '{vendor}' to vendors list?"):
                add_vendor = False
        self._set_saving(True)
        self._fail("")
        import threading

        def work():
            try:
                if add_vendor:
                    try:
                        self.sb.table("vendors").insert({"name": vendor}).execute()
                    except Exception:
                        pass  # race/duplicate — invoice save matters
                if self.row is None:
                    p = {**payload, "type": g("type"), "current_stage": "Created",
                         "created_by": self.user.id if self.user else None}
                    res = self.sb.table("invoices").insert(p).select().execute()
                    new_id = res.data[0]["id"] if isinstance(res.data, list) else res.data["id"]
                    self.audit_fn(new_id, None, "Created", "create", "created via desktop")
                else:
                    self.sb.table("invoices").update(payload).eq("id", self.row["id"]).execute()
                    self.audit_fn(self.row["id"], self.row["current_stage"],
                                  self.row["current_stage"], "edit", "edited via desktop")
            except Exception as e:  # noqa: BLE001
                err = e
                self.after(0, lambda err=err: self._save_error(err))
                return
            self.after(0, self._save_done)

        threading.Thread(target=work, daemon=True).start()

    def _save_error(self, e):
        self._set_saving(False)
        if is_duplicate_error(e):
            self._fail(f"Invoice number already exists: {self.entries['invoice_number'].get().strip()}")
        else:
            self._fail(str(e)[:300])

    def _save_done(self):
        self._set_saving(False)
        self.on_save()
        self.destroy()
