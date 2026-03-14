import asyncio
import threading
import traceback
import customtkinter as ctk
from src.automation.browser_manager import BrowserManager
from src.gui.dashboard import DashboardPanel
from src.gui.listing_panel import ListingPanel
from src.gui.pricing_panel import PricingPanel
from src.gui.reply_panel import ReplyPanel
from src.gui.settings_panel import SettingsPanel
from src.data.database import init_database
from src.utils.logger import setup_logger
from src.utils.i18n import t

logger = setup_logger("gui")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MercariApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title(t("app_title"))
        self.geometry("1100x720")
        self.minsize(900, 600)

        init_database()

        self.browser = BrowserManager()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        self._build_ui()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run_async(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.nav_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.nav_frame.grid(row=0, column=0, sticky="nswe")
        self.nav_frame.grid_propagate(False)

        logo_label = ctk.CTkLabel(
            self.nav_frame, text=t("app_logo"),
            font=ctk.CTkFont(size=18, weight="bold")
        )
        logo_label.pack(pady=(30, 10))

        version_label = ctk.CTkLabel(
            self.nav_frame, text="v1.0",
            font=ctk.CTkFont(size=12), text_color="gray"
        )
        version_label.pack(pady=(0, 20))

        separator = ctk.CTkFrame(self.nav_frame, height=2, fg_color="gray30")
        separator.pack(fill="x", padx=20, pady=5)

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", t("nav_dashboard")),
            ("listing", t("nav_listing")),
            ("pricing", t("nav_pricing")),
            ("reply", t("nav_reply")),
            ("settings", t("nav_settings")),
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.nav_frame, text=label,
                font=ctk.CTkFont(size=14),
                height=40, corner_radius=8,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                anchor="w",
                command=lambda k=key: self._show_panel(k)
            )
            btn.pack(fill="x", padx=15, pady=3)
            self.nav_buttons[key] = btn

        spacer = ctk.CTkFrame(self.nav_frame, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        self.browser_status = ctk.CTkLabel(
            self.nav_frame, text=t("browser_stopped"),
            font=ctk.CTkFont(size=11), text_color="gray"
        )
        self.browser_status.pack(pady=5)

        self.browser_btn = ctk.CTkButton(
            self.nav_frame, text=t("browser_start"),
            font=ctk.CTkFont(size=13),
            height=36, corner_radius=8,
            fg_color="#28a745", hover_color="#218838",
            command=self._toggle_browser
        )
        self.browser_btn.pack(fill="x", padx=15, pady=(5, 15))

        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        self.panels = {}
        self.panels["dashboard"] = DashboardPanel(self.content_frame, self)
        self.panels["listing"] = ListingPanel(self.content_frame, self)
        self.panels["pricing"] = PricingPanel(self.content_frame, self)
        self.panels["reply"] = ReplyPanel(self.content_frame, self)
        self.panels["settings"] = SettingsPanel(self.content_frame, self)

        for panel in self.panels.values():
            panel.grid(row=0, column=0, sticky="nswe")

        self._show_panel("dashboard")

    def _show_panel(self, key: str):
        for k, btn in self.nav_buttons.items():
            if k == key:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

        self.panels[key].tkraise()

        if hasattr(self.panels[key], 'on_show'):
            self.panels[key].on_show()

    def _toggle_browser(self):
        if self.browser.is_running:
            self.browser_btn.configure(state="disabled", text="...")
            async def _stop():
                try:
                    await self.browser.close()
                except Exception:
                    pass
                self.after(0, self._on_browser_stopped)
            self.run_async(_stop())
        else:
            self.browser_btn.configure(state="disabled", text=t("browser_starting"))
            self.browser_status.configure(
                text=t("browser_starting"), text_color="#f0ad4e"
            )

            async def _start():
                try:
                    await self.browser.start()
                    self.after(0, self._on_browser_started)
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"浏览器启动失败: {error_msg}\n{traceback.format_exc()}")
                    self.after(0, lambda: self._on_browser_error(error_msg))

            self.run_async(_start())

    def _on_browser_started(self):
        self.browser_status.configure(text=t("browser_running"), text_color="#28a745")
        self.browser_btn.configure(
            text=t("browser_stop"), fg_color="#dc3545", hover_color="#c82333",
            state="normal"
        )

    def _on_browser_stopped(self):
        self.browser_status.configure(text=t("browser_stopped"), text_color="gray")
        self.browser_btn.configure(
            text=t("browser_start"), fg_color="#28a745", hover_color="#218838",
            state="normal"
        )

    def _on_browser_error(self, error_msg: str):
        self.browser_status.configure(
            text=t("browser_error"), text_color="#dc3545"
        )
        self.browser_btn.configure(
            text=t("browser_start"), fg_color="#28a745", hover_color="#218838",
            state="normal"
        )
        from tkinter import messagebox
        messagebox.showerror(
            t("error"),
            t("browser_error_msg", error=error_msg)
        )

    def on_closing(self):
        if self.browser.is_running:
            self.run_async(self.browser.close())
        self._loop.call_soon_threadsafe(self._loop.stop)
        self.destroy()


def main():
    app = MercariApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
