"""Clean shell: sidebar nav, loading login, status bar."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import customtkinter as ctk
from widgets.ui import run_bg
from utils.session import save_session, load_session, clear_session
from supabase_client import get_client
from pages.dashboard import DashboardPage
from pages.invoices import InvoicesPage
from pages.audit import AuditPage
from pages.vendors import VendorsPage
from pages.users import UsersPage
import config

ctk.set_appearance_mode(config.APPEARANCE_MODE)
ctk.set_default_color_theme(config.COLOR_THEME)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{config.APP_TITLE} v{config.APP_VERSION} — {config.APP_SUBTITLE}")
        self.minsize(config.WINDOW_MIN_W, config.WINDOW_MIN_H)
        self._center(config.WINDOW_DEFAULT_W, config.WINDOW_DEFAULT_H)
        self._set_icon()
        self.sb = None
        self.user = None
        self.role = "user"
        self.current = None
        self.pages = {}
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.show_login()

    def _center(self, w, h):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{max(x,0)}+{max(y,0)}")

    def _set_icon(self):
        """Window + taskbar icon. Works in dev and PyInstaller onefile."""
        import sys
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        ico = os.path.join(base, "assets", "icon.ico")
        png = os.path.join(base, "assets", "icon.png")
        try:
            if os.path.exists(ico):
                self.iconbitmap(ico)
        except Exception:
            pass
        try:
            if os.path.exists(png):
                from PIL import Image, ImageTk
                im = Image.open(png).resize((32, 32))
                self._icon_img = ImageTk.PhotoImage(im)
                self.iconphoto(True, self._icon_img)
        except Exception:
            pass
        try:  # Windows taskbar grouping + icon
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SSL.InvoiceTracker.1.0")
        except Exception:
            pass

    # --- clean login with loading ---
    def show_login(self):
        self.login_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.login_wrap.place(relx=0.5, rely=0.5, anchor="center")
        card = ctk.CTkFrame(self.login_wrap, corner_radius=14, border_width=1,
                            border_color=("#e2e8f0", "#2a2f3a"))
        card.pack(padx=20, pady=20)
        ctk.CTkLabel(card, text="🧾", font=("Segoe UI", 36)).pack(pady=(24, 0))
        ctk.CTkLabel(card, text=config.APP_TITLE, font=config.FONTS["title"]).pack(padx=44)
        ctk.CTkLabel(card, text=config.APP_SUBTITLE, font=config.FONTS["small"],
                     text_color=config.MUTED).pack(padx=44, pady=(0, 6))
        self.e_email = ctk.CTkEntry(card, placeholder_text="Email", width=300, height=38,
                                    corner_radius=config.RADIUS_SM)
        self.e_email.pack(padx=44, pady=(12, 6))
        self.e_pw = ctk.CTkEntry(card, placeholder_text="Password", show="*", width=300, height=38,
                                 corner_radius=config.RADIUS_SM)
        self.e_pw.pack(padx=44, pady=6)
        self.e_pw.bind("<Return>", lambda _e: self.do_login())
        self.e_email.bind("<Return>", lambda _e: self.do_login())
        self.btn_login = ctk.CTkButton(card, text="Sign in", command=self.do_login, width=300, height=38,
                                       corner_radius=config.RADIUS_SM,
                                       fg_color=config.ACCENT, hover_color=config.ACCENT_HOVER)
        self.btn_login.pack(padx=44, pady=(12, 4))
        self.v_remember = ctk.CTkCheckBox(card, text="Remember me for 1 day")
        self.v_remember.pack(padx=44, pady=4)
        try:
            self.v_remember.select()
        except Exception:
            pass
        self.login_prog = ctk.CTkProgressBar(card, width=300, height=6, corner_radius=3)
        self.login_prog.pack(padx=44, pady=(0, 4))
        self.login_prog.pack_forget()
        self.login_err = ctk.CTkLabel(card, text="", font=config.FONTS["small"], text_color=config.DANGER,
                                      wraplength=300)
        self.login_err.pack(padx=44, pady=(0, 18))
        self.e_email.focus_set()
        self.after(200, self.try_restore)

    def try_restore(self):
        saved = load_session()
        if not saved or not hasattr(self, "login_wrap") or not self.login_wrap.winfo_exists():
            return
        self.btn_login.configure(text="Restoring session…", state="disabled")
        self.login_prog.pack(padx=44, pady=(0, 4))
        self.login_prog.start()

        def work():
            sb = get_client()
            res = sb.auth.set_session(saved["access_token"], saved["refresh_token"])
            user = res.user or sb.auth.get_user().user
            role = "user"
            try:
                pr = sb.table("profiles").select("role").eq("id", user.id).limit(1).execute()
                if pr.data:
                    role = pr.data[0].get("role", "user")
            except Exception:
                pass
            return sb, user, role

        def done(result):
            self.login_prog.stop()
            sb, user, role = result
            # refresh stored tokens (rotation)
            try:
                sess = sb.auth.get_session()
                if sess and sess.access_token:
                    save_session(sess.access_token, sess.refresh_token, user.email or "")
            except Exception:
                pass
            self.sb, self.user, self.role = sb, user, role
            try:
                self.login_wrap.destroy()
            except Exception:
                pass
            self.show_shell()

        def fail(_e):
            clear_session()
            try:
                self.login_prog.stop()
                self.login_prog.pack_forget()
                self.btn_login.configure(text="Sign in", state="normal")
                if self.e_email.get().strip() == "" and saved.get("email"):
                    self.e_email.insert(0, saved.get("email"))
            except Exception:
                pass

        run_bg(work, on_done=done, on_error=fail, master=self)

    def do_login(self):
        email, pw = self.e_email.get().strip(), self.e_pw.get()
        if not email or not pw:
            self.login_err.configure(text="Enter email and password.")
            return
        self.btn_login.configure(text="Signing in…", state="disabled")
        self.login_prog.pack(padx=44, pady=(0, 4))
        self.login_prog.start()
        self.login_err.configure(text="")

        def work():
            sb = get_client()
            res = sb.auth.sign_in_with_password({"email": email, "password": pw})
            role = "user"
            try:
                pr = sb.table("profiles").select("role").eq("id", res.user.id).limit(1).execute()
                if pr.data:
                    role = pr.data[0].get("role", "user")
            except Exception:
                pass
            return sb, res, role

        def done(result):
            self.login_prog.stop()
            self.login_prog.pack_forget()
            self.sb, res, self.role = result[0], result[1], result[2]
            self.user = res.user
            try:
                sess = self.sb.auth.get_session()
                if getattr(self.v_remember, "get", lambda: 0)() and sess and sess.access_token:
                    save_session(sess.access_token, sess.refresh_token, email)
            except Exception:
                pass
            self.login_wrap.destroy()
            self.show_shell()

        def fail(e):
            self.login_prog.stop()
            self.login_prog.pack_forget()
            self.btn_login.configure(text="Sign in", state="normal")
            self.login_err.configure(text=str(e)[:220])

        run_bg(work, on_done=done, on_error=fail, master=self)

    # --- shell ---
    def show_shell(self):
        side = ctk.CTkFrame(self, width=config.NAV_W, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        ctk.CTkLabel(side, text="🧾 " + config.APP_TITLE, font=config.FONTS["h2"]).pack(padx=16, pady=(18, 0), anchor="w")
        ctk.CTkLabel(side, text=(self.user.email if self.user else ""),
                     font=config.FONTS["small"], text_color=config.MUTED).pack(padx=16, anchor="w")
        ctk.CTkLabel(side, text=f"● {getattr(self, 'role', 'user').upper()}",
                     font=("Segoe UI", 10, "bold"),
                     text_color=config.ACCENT if getattr(self, "role", "") == "admin" else config.MUTED).pack(padx=16, pady=(2, 0), anchor="w")
        self.nav_btns = {}
        names = ["Dashboard", "Invoices", "Vendors", "Audit"]
        if getattr(self, "role", "user") == "admin":
            names.append("Users")
        for name in names:
            b = ctk.CTkButton(side, text=name, anchor="w", fg_color="transparent",
                              corner_radius=config.RADIUS_SM,
                              command=lambda n=name: self.show_page(n))
            b.pack(fill="x", padx=10, pady=4)
            self.nav_btns[name] = b
        ctk.CTkLabel(side, text="Appearance", font=config.FONTS["small"],
                     text_color=config.MUTED).pack(padx=16, pady=(18, 2), anchor="w")
        self.v_mode = ctk.CTkOptionMenu(side, values=["System", "Light", "Dark"],
                                        command=ctk.set_appearance_mode,
                                        corner_radius=config.RADIUS_SM)
        self.v_mode.set(config.APPEARANCE_MODE)
        self.v_mode.pack(fill="x", padx=10)
        ctk.CTkButton(side, text="Sign out", fg_color="transparent", border_width=1,
                      corner_radius=config.RADIUS_SM,
                      command=self.sign_out).pack(fill="x", padx=10, pady=18, side="bottom")

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)
        self.container = main
        self.pages["Dashboard"] = DashboardPage(main, self.sb, self.user)
        is_admin = getattr(self, "role", "user") == "admin"
        self.pages["Invoices"] = InvoicesPage(main, self.sb, self.user, is_admin=is_admin)
        self.pages["Vendors"] = VendorsPage(main, self.sb, self.user, is_admin=is_admin)
        self.pages["Audit"] = AuditPage(main, self.sb, self.user)
        if getattr(self, "role", "user") == "admin":
            self.pages["Users"] = UsersPage(main, self.sb, self.user, is_admin=True)
        self.status = ctk.CTkLabel(self, text=f"Signed in ({self.role}) · {config.APP_TITLE}",
                                   font=config.FONTS["small"], text_color=config.MUTED)
        self.status.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=2)
        self.show_page("Dashboard")

    def show_page(self, name):
        if self.current:
            self.current.grid_forget()
        self.current = self.pages[name]
        self.current.grid(row=0, column=0, sticky="nsew")
        for n, b in self.nav_btns.items():
            b.configure(fg_color=config.ACCENT if n == name else "transparent",
                        text_color="white" if n == name else ("gray10", "gray90"))
        if hasattr(self.current, "load"):
            try:
                self.current.load()
            except Exception:
                pass

    def sign_out(self):
        clear_session()
        try:
            self.sb.auth.sign_out()
        except Exception:
            pass
        for w in self.winfo_children():
            w.destroy()
        self.grid_columnconfigure(1, weight=0)
        self.user, self.sb, self.current, self.pages = None, None, None, {}
        self.role = "user"
        self.show_login()


if __name__ == "__main__":
    App().mainloop()
