"""Vendor manager: add/edit/delete vendors. Used by invoice form dropdown."""
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from widgets.ui import LoadingBar, run_bg, style_table
import config


class VendorsPage(ctk.CTkFrame):
    def __init__(self, master, sb, user, is_admin=False):
        super().__init__(master, fg_color="transparent")
        self.sb, self.is_admin = sb, is_admin
        self.rows: list[dict] = []
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(top, text="Vendors", font=config.FONTS["title"]).pack(side="left")
        ctk.CTkButton(top, text="↻ Refresh", width=100, corner_radius=config.RADIUS_SM,
                      command=self.load).pack(side="right", padx=4)
        ctk.CTkButton(top, text="+ New Vendor", width=130, corner_radius=config.RADIUS_SM,
                      fg_color=config.SUCCESS, hover_color=config.SUCCESS_HOVER,
                      command=self.open_create).pack(side="right", padx=4)
        self.loading = LoadingBar(self)
        wrap = ctk.CTkFrame(self, corner_radius=config.RADIUS,
                            border_width=config.BORDER_W, border_color=config.LINE)
        wrap.pack(fill="both", expand=True, padx=12, pady=8)
        self.tree = ttk.Treeview(wrap, columns=("name", "contact", "notes"), show="headings", height=16)
        for c, w in (("name", 220), ("contact", 200), ("notes", 320)):
            self.tree.heading(c, text=c.title())
            self.tree.column(c, width=w)
        style_table(self.tree)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        vsb.pack(side="right", fill="y", padx=(0, 10), pady=10)
        self.tree.bind("<Double-1>", lambda _e: self.open_edit())
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(bot, text="Edit", width=90, command=self.open_edit).pack(side="left", padx=4)
        ctk.CTkButton(bot, text="Delete", width=90, fg_color=config.DANGER,
                      hover_color=config.DANGER_HOVER, command=self.delete).pack(side="left", padx=4)
        ctk.CTkLabel(bot, text="Double-click to edit. Invoice form suggests these but manual entry still allowed.",
                     font=config.FONTS["small"], text_color=config.MUTED).pack(side="left", padx=12)
        self.load()

    def load(self):
        self.loading.show("Loading vendors…")

        def fetch():
            return (self.sb.table("vendors").select("*").order("name").limit(500).execute().data or [])

        def done(rows):
            self.loading.hide()
            self.rows = rows
            for i in self.tree.get_children():
                self.tree.delete(i)
            for r in rows:
                self.tree.insert("", "end", iid=r["id"],
                                 values=(r.get("name", ""), r.get("contact", "") or "", r.get("notes", "") or ""))

        def fail(e):
            self.loading.hide()
            messagebox.showerror("Vendors failed", str(e)[:250])

        run_bg(fetch, on_done=done, on_error=fail, master=self)

    def _sel(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Vendors", "Select a vendor first.")
            return None
        return next((r for r in self.rows if r["id"] == sel[0]), None)

    def open_create(self):
        VendorDialog(self, self.sb, None, self.load)

    def open_edit(self):
        r = self._sel()
        if r:
            VendorDialog(self, self.sb, r, self.load)

    def delete(self):
        r = self._sel()
        if not r:
            return
        if not self.is_admin:
            messagebox.showinfo("Vendors", "Admin only — ask an admin to delete.")
            return
        if not messagebox.askyesno("Delete", f"Delete vendor '{r['name']}'?\nInvoices using it keep their text."):
            return
        try:
            self.sb.table("vendors").delete().eq("id", r["id"]).execute()
            self.load()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Delete failed", str(e)[:250])


class VendorDialog(ctk.CTkToplevel):
    def __init__(self, master, sb, row, on_save):
        super().__init__(master)
        self.sb, self.row, self.on_save = sb, row, on_save
        self.title("Edit vendor" if row else "New vendor")
        self.geometry("400x340")
        self.grab_set()
        r = row or {}
        ctk.CTkLabel(self, text="Edit vendor" if row else "New vendor",
                     font=config.FONTS["h2"]).pack(anchor="w", padx=18, pady=(14, 4))
        self.v_name = tk.StringVar(value=r.get("name", ""))
        self.v_contact = tk.StringVar(value=r.get("contact", "") or "")
        for lbl, var in (("Name *", self.v_name), ("Contact", self.v_contact)):
            ctk.CTkLabel(self, text=lbl).pack(anchor="w", padx=18, pady=(8, 0))
            ctk.CTkEntry(self, textvariable=var, corner_radius=config.RADIUS_SM).pack(fill="x", padx=18)
        ctk.CTkLabel(self, text="Notes").pack(anchor="w", padx=18, pady=(8, 0))
        self.notes = ctk.CTkTextbox(self, height=70, corner_radius=config.RADIUS_SM)
        self.notes.pack(fill="x", padx=18)
        self.notes.insert("1.0", r.get("notes", "") or "")
        self.err = ctk.CTkLabel(self, text="", text_color=config.DANGER, font=config.FONTS["small"])
        self.err.pack(padx=18)
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=12)
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1,
                      corner_radius=config.RADIUS_SM, command=self.destroy).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", corner_radius=config.RADIUS_SM,
                      fg_color=config.ACCENT, hover_color=config.ACCENT_HOVER,
                      command=self.save).pack(side="right")

    def save(self):
        name = self.v_name.get().strip()
        if not name:
            self.err.configure(text="Name is required.")
            return
        payload = {"name": name, "contact": self.v_contact.get().strip() or None,
                   "notes": self.notes.get("1.0", "end").strip() or None}
        try:
            if self.row is None:
                self.sb.table("vendors").insert(payload).execute()
            else:
                self.sb.table("vendors").update(payload).eq("id", self.row["id"]).execute()
            self.on_save()
            self.destroy()
        except Exception as e:  # noqa: BLE001
            s = str(e).lower()
            if "duplicate" in s or "unique" in s:
                self.err.configure(text="Vendor name already exists.")
            else:
                self.err.configure(text=str(e)[:200])
