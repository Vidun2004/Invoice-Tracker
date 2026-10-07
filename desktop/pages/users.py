"""User manager (admin only): list profiles, edit display name + role."""
from tkinter import ttk, messagebox
import tkinter as tk
import customtkinter as ctk
from widgets.ui import LoadingBar, run_bg, style_table
import config


class UsersPage(ctk.CTkFrame):
    def __init__(self, master, sb, user, is_admin=False):
        super().__init__(master, fg_color="transparent")
        self.sb = sb
        self.is_admin = is_admin
        self.rows: list[dict] = []
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(top, text="Users", font=config.FONTS["title"]).pack(side="left")
        self.btn_refresh = ctk.CTkButton(top, text="↻ Refresh", width=100,
                                        corner_radius=config.RADIUS_SM, command=self.load)
        self.btn_refresh.pack(side="right")
        if not is_admin:
            ctk.CTkLabel(self, text="Admin only — ask an admin to change roles.",
                         font=config.FONTS["body"], text_color=config.DANGER).pack(pady=40)
            return
        self.loading = LoadingBar(self)
        wrap = ctk.CTkFrame(self, corner_radius=config.RADIUS,
                            border_width=config.BORDER_W, border_color=config.LINE)
        wrap.pack(fill="both", expand=True, padx=12, pady=8)
        self.tree = ttk.Treeview(wrap, columns=("email", "display_name", "role"), show="headings", height=16)
        for c, w in (("email", 240), ("display_name", 200), ("role", 120)):
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=w)
        style_table(self.tree)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", lambda _e: self.open_edit())
        bot = ctk.CTkFrame(self, fg_color="transparent")
        bot.pack(fill="x", padx=12, pady=(0, 12))
        ctk.CTkButton(bot, text="Edit role / name", width=150, command=self.open_edit).pack(side="left")
        ctk.CTkLabel(bot, text="Role controls Users page access. Auth accounts are created in Supabase Auth.",
                     font=config.FONTS["small"], text_color=config.MUTED).pack(side="left", padx=12)
        self.load()

    def load(self):
        if not self.is_admin:
            return
        self.loading.show("Loading users…")

        def fetch():
            return (self.sb.table("profiles").select("*").order("created_at").limit(200).execute().data or [])

        def done(rows):
            self.loading.hide()
            self.rows = rows
            for i in self.tree.get_children():
                self.tree.delete(i)
            for r in rows:
                self.tree.insert("", "end", iid=r["id"],
                                 values=(r.get("email", ""), r.get("display_name", "") or "", r.get("role", "")))

        def fail(e):
            self.loading.hide()
            messagebox.showerror("Users failed", str(e)[:250])

        run_bg(fetch, on_done=done, on_error=fail, master=self)

    def open_edit(self):
        if not self.is_admin:
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Users", "Select a user first.")
            return
        row = next((r for r in self.rows if r["id"] == sel[0]), None)
        if row:
            UserDialog(self, self.sb, row, self.load)


class UserDialog(ctk.CTkToplevel):
    def __init__(self, master, sb, row, on_save):
        super().__init__(master)
        self.sb, self.row, self.on_save = sb, row, on_save
        self.title("Edit user")
        self.geometry("380x300")
        self.grab_set()
        ctk.CTkLabel(self, text=row.get("email", ""), font=config.FONTS["h2"]).pack(padx=18, pady=(14, 4), anchor="w")
        ctk.CTkLabel(self, text="Display name").pack(padx=18, anchor="w")
        self.v_name = tk.StringVar(value=row.get("display_name", "") or "")
        ctk.CTkEntry(self, textvariable=self.v_name, corner_radius=config.RADIUS_SM).pack(fill="x", padx=18)
        ctk.CTkLabel(self, text="Role").pack(padx=18, pady=(8, 0), anchor="w")
        self.v_role = tk.StringVar(value=row.get("role", "user"))
        ctk.CTkOptionMenu(self, variable=self.v_role, values=["user", "admin"]).pack(fill="x", padx=18)
        self.err = ctk.CTkLabel(self, text="", text_color=config.DANGER, font=config.FONTS["small"])
        self.err.pack(padx=18, pady=6)
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=12)
        ctk.CTkButton(btns, text="Cancel", fg_color="transparent", border_width=1,
                      corner_radius=config.RADIUS_SM, command=self.destroy).pack(side="right", padx=6)
        ctk.CTkButton(btns, text="Save", corner_radius=config.RADIUS_SM,
                      fg_color=config.ACCENT, hover_color=config.ACCENT_HOVER,
                      command=self.save).pack(side="right")

    def save(self):
        try:
            self.sb.table("profiles").update(
                {"display_name": self.v_name.get().strip() or None,
                 "role": self.v_role.get()}).eq("id", self.row["id"]).execute()
            self.on_save()
            self.destroy()
        except Exception as e:  # noqa: BLE001
            self.err.configure(text=str(e)[:200])
