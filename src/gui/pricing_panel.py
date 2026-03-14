import customtkinter as ctk
from tkinter import messagebox
from src.core.pricing_engine import PricingEngine
from src.utils.config import get
from src.utils.logger import setup_logger
from src.utils.i18n import t

logger = setup_logger("pricing_panel")


class PricingPanel(ctk.CTkFrame):

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.engine = None

        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(
            self, text=t("pricing_title"),
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 15))

        strategy_frame = ctk.CTkFrame(self)
        strategy_frame.grid(row=1, column=0, sticky="we", padx=10, pady=5)

        ctk.CTkLabel(
            strategy_frame, text=t("pricing_strategy"),
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=15, pady=(10, 5), anchor="w")

        strategies = get('pricing.strategies', [])
        for s in strategies:
            days = s.get('days_unsold', 0)
            pct = s.get('discount_percent', 0)
            ctk.CTkLabel(
                strategy_frame, text=t("pricing_days_fmt", days=days, pct=pct),
                font=ctk.CTkFont(size=13)
            ).pack(padx=15, pady=2, anchor="w")

        min_price = get('pricing.min_price', 300)
        ctk.CTkLabel(
            strategy_frame, text=t("pricing_min_fmt", price=min_price),
            font=ctk.CTkFont(size=13), text_color="#e67e22"
        ).pack(padx=15, pady=(2, 10), anchor="w")

        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=2, column=0, sticky="we", padx=10, pady=5)

        self.check_btn = ctk.CTkButton(
            control_frame, text=t("btn_check_price"),
            font=ctk.CTkFont(size=13), height=35,
            command=self._check_prices
        )
        self.check_btn.pack(side="left", padx=10, pady=10)

        self.execute_btn = ctk.CTkButton(
            control_frame, text=t("btn_execute_price"),
            font=ctk.CTkFont(size=13, weight="bold"), height=35,
            fg_color="#e67e22", hover_color="#d35400",
            command=self._execute_pricing
        )
        self.execute_btn.pack(side="left", padx=5, pady=10)

        self.stop_btn = ctk.CTkButton(
            control_frame, text=t("btn_stop"),
            font=ctk.CTkFont(size=13), height=35,
            fg_color="#dc3545", hover_color="#c82333",
            state="disabled",
            command=self._stop_pricing
        )
        self.stop_btn.pack(side="left", padx=5, pady=10)

        self.status_label = ctk.CTkLabel(
            control_frame, text="",
            font=ctk.CTkFont(size=12), text_color="gray"
        )
        self.status_label.pack(side="right", padx=15, pady=10)

        result_frame = ctk.CTkFrame(self)
        result_frame.grid(row=3, column=0, sticky="nswe", padx=10, pady=(5, 10))
        result_frame.grid_rowconfigure(1, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            result_frame, text=t("pricing_log"),
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        self.result_textbox = ctk.CTkTextbox(
            result_frame, font=ctk.CTkFont(size=12), state="disabled"
        )
        self.result_textbox.grid(row=1, column=0, sticky="nswe", padx=15, pady=(5, 15))

        self._adjustments = []

    def _check_prices(self):
        if not self.app.browser.is_running:
            messagebox.showwarning(t("warning"), t("need_browser"))
            return

        self.engine = PricingEngine(self.app.browser)
        self._adjustments = self.engine.check_prices()

        self.result_textbox.configure(state="normal")
        self.result_textbox.delete("1.0", "end")

        if not self._adjustments:
            self.result_textbox.insert("end", t("pricing_none") + "\n")
            self.status_label.configure(text=t("pricing_none"))
        else:
            self.result_textbox.insert("end", t("pricing_found", count=len(self._adjustments)))
            for adj in self._adjustments:
                p = adj['product']
                line = (
                    f"  [{p['id']}] {p['title'][:25]}\n"
                    f"      ¥{p['price']:,} -> ¥{adj['new_price']:,}  "
                    f"({adj['reason']})\n\n"
                )
                self.result_textbox.insert("end", line)
            self.status_label.configure(
                text=t("pricing_found", count=len(self._adjustments)).strip(),
                text_color="#e67e22"
            )

        self.result_textbox.configure(state="disabled")

    def _execute_pricing(self):
        if not self.app.browser.is_running:
            messagebox.showwarning(t("warning"), t("need_browser"))
            return

        if not self._adjustments:
            self._check_prices()
            if not self._adjustments:
                return

        if not messagebox.askyesno(
            t("confirm"),
            t("pricing_confirm", count=len(self._adjustments))
        ):
            return

        self.engine = PricingEngine(self.app.browser)
        self.engine.set_progress_callback(self._on_pricing_progress)

        self.execute_btn.configure(state="disabled")
        self.check_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        self.app.run_async(self.engine.execute_price_adjustments(self._adjustments))

    def _stop_pricing(self):
        if self.engine:
            self.engine.stop()
        self.execute_btn.configure(state="normal")
        self.check_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text=t("status_stopped"))

    def _on_pricing_progress(self, title, old_price, new_price, status):
        self.app.after(0, lambda: self._update_pricing_ui(title, old_price, new_price, status))

    def _update_pricing_ui(self, title, old_price, new_price, status):
        self.result_textbox.configure(state="normal")
        line = f"  {title[:20]}: ¥{old_price:,} -> ¥{new_price:,} [{status}]\n"
        self.result_textbox.insert("end", line)
        self.result_textbox.see("end")
        self.result_textbox.configure(state="disabled")
        self.status_label.configure(text=status)

    def on_show(self):
        pass
