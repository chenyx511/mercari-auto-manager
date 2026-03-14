import customtkinter as ctk
from tkinter import messagebox
from src.utils.config import load_config, save_config, get
from src.utils.logger import setup_logger
from src.utils.i18n import t, current_language

logger = setup_logger("settings_panel")

LANGUAGE_OPTIONS = {
    "中文": "zh",
    "日本語": "ja",
    "English": "en",
}
LANGUAGE_REVERSE = {v: k for k, v in LANGUAGE_OPTIONS.items()}


class SettingsPanel(ctk.CTkFrame):

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(
            self, text=t("settings_title"),
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 15))

        scroll_frame = ctk.CTkScrollableFrame(self)
        scroll_frame.grid(row=1, column=0, sticky="nswe", padx=10, pady=5)
        scroll_frame.grid_columnconfigure(1, weight=1)

        row = 0

        # --- 语言设置 ---
        row = self._add_section_title(scroll_frame, t("settings_language"), row)

        cur_lang = current_language()
        cur_label = LANGUAGE_REVERSE.get(cur_lang, "中文")
        self.language_var = ctk.StringVar(value=cur_label)

        ctk.CTkLabel(
            scroll_frame, text=t("settings_language"),
            font=ctk.CTkFont(size=13)
        ).grid(row=row, column=0, sticky="w", padx=15, pady=5)
        ctk.CTkOptionMenu(
            scroll_frame, variable=self.language_var,
            values=list(LANGUAGE_OPTIONS.keys()),
            width=180, height=32
        ).grid(row=row, column=1, sticky="w", padx=15, pady=5)
        row += 1

        # --- 浏览器设置 ---
        row = self._add_section_title(scroll_frame, t("settings_browser"), row)

        self.headless_var = ctk.BooleanVar(value=get('browser.headless', False))
        row = self._add_checkbox(scroll_frame, t("settings_headless"), self.headless_var, row)

        self.slow_mo_var = ctk.StringVar(value=str(get('browser.slow_mo', 500)))
        row = self._add_entry(scroll_frame, t("settings_slowmo"), self.slow_mo_var, row)

        # --- 上架设置 ---
        row = self._add_section_title(scroll_frame, t("settings_listing"), row)

        self.listing_delay_var = ctk.StringVar(value=str(get('listing.delay_between_items_seconds', 30)))
        row = self._add_entry(scroll_frame, t("settings_listing_delay"), self.listing_delay_var, row)

        self.listing_random_var = ctk.StringVar(value=str(get('listing.random_delay_range', 10)))
        row = self._add_entry(scroll_frame, t("settings_listing_random"), self.listing_random_var, row)

        # --- 调价设置 ---
        row = self._add_section_title(scroll_frame, t("settings_pricing"), row)

        self.pricing_enabled_var = ctk.BooleanVar(value=get('pricing.enabled', False))
        row = self._add_checkbox(scroll_frame, t("settings_pricing_enable"), self.pricing_enabled_var, row)

        self.pricing_interval_var = ctk.StringVar(value=str(get('pricing.check_interval_minutes', 60)))
        row = self._add_entry(scroll_frame, t("settings_pricing_interval"), self.pricing_interval_var, row)

        self.min_price_var = ctk.StringVar(value=str(get('pricing.min_price', 300)))
        row = self._add_entry(scroll_frame, t("settings_pricing_min"), self.min_price_var, row)

        strategies = get('pricing.strategies', [])
        ctk.CTkLabel(
            scroll_frame, text=t("settings_pricing_strategy"),
            font=ctk.CTkFont(size=13)
        ).grid(row=row, column=0, sticky="w", padx=15, pady=5)
        row += 1

        self.strategy_entries = []
        for s in strategies:
            frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            frame.grid(row=row, column=0, columnspan=2, sticky="we", padx=30, pady=2)

            days_var = ctk.StringVar(value=str(s.get('days_unsold', 0)))
            ctk.CTkLabel(frame, text=t("settings_days"), font=ctk.CTkFont(size=12)).pack(side="left", padx=5)
            ctk.CTkEntry(frame, textvariable=days_var, width=60, height=30).pack(side="left", padx=5)

            pct_var = ctk.StringVar(value=str(s.get('discount_percent', 0)))
            ctk.CTkLabel(frame, text=t("settings_discount"), font=ctk.CTkFont(size=12)).pack(side="left", padx=5)
            ctk.CTkEntry(frame, textvariable=pct_var, width=60, height=30).pack(side="left", padx=5)

            self.strategy_entries.append((days_var, pct_var))
            row += 1

        # --- 自动回复设置 ---
        row = self._add_section_title(scroll_frame, t("settings_reply"), row)

        self.reply_enabled_var = ctk.BooleanVar(value=get('auto_reply.enabled', False))
        row = self._add_checkbox(scroll_frame, t("settings_reply_enable"), self.reply_enabled_var, row)

        self.reply_interval_var = ctk.StringVar(value=str(get('auto_reply.check_interval_seconds', 120)))
        row = self._add_entry(scroll_frame, t("settings_reply_interval"), self.reply_interval_var, row)

        # --- 日志设置 ---
        row = self._add_section_title(scroll_frame, t("settings_log"), row)

        self.log_level_var = ctk.StringVar(value=get('logging.level', 'INFO'))
        ctk.CTkLabel(
            scroll_frame, text=t("settings_log_level"),
            font=ctk.CTkFont(size=13)
        ).grid(row=row, column=0, sticky="w", padx=15, pady=5)
        ctk.CTkOptionMenu(
            scroll_frame, variable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            width=150, height=30
        ).grid(row=row, column=1, sticky="w", padx=15, pady=5)
        row += 1

        # --- 保存按钮 ---
        save_btn = ctk.CTkButton(
            self, text=t("btn_save"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40, width=200,
            fg_color="#28a745", hover_color="#218838",
            command=self._save_settings
        )
        save_btn.grid(row=2, column=0, pady=15)

    def _add_section_title(self, parent, text, row) -> int:
        if row > 0:
            sep = ctk.CTkFrame(parent, height=1, fg_color="gray40")
            sep.grid(row=row, column=0, columnspan=2, sticky="we", padx=10, pady=10)
            row += 1

        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 8))
        return row + 1

    def _add_entry(self, parent, label, var, row) -> int:
        ctk.CTkLabel(
            parent, text=label,
            font=ctk.CTkFont(size=13)
        ).grid(row=row, column=0, sticky="w", padx=15, pady=5)
        ctk.CTkEntry(
            parent, textvariable=var,
            font=ctk.CTkFont(size=12), height=32, width=200
        ).grid(row=row, column=1, sticky="w", padx=15, pady=5)
        return row + 1

    def _add_checkbox(self, parent, label, var, row) -> int:
        ctk.CTkCheckBox(
            parent, text=label, variable=var,
            font=ctk.CTkFont(size=13)
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=15, pady=5)
        return row + 1

    def _save_settings(self):
        try:
            config = load_config()

            lang_label = self.language_var.get()
            lang_code = LANGUAGE_OPTIONS.get(lang_label, 'zh')
            config['language'] = lang_code

            config['browser']['headless'] = self.headless_var.get()
            config['browser']['slow_mo'] = int(self.slow_mo_var.get())

            config['listing']['delay_between_items_seconds'] = int(self.listing_delay_var.get())
            config['listing']['random_delay_range'] = int(self.listing_random_var.get())

            config['pricing']['enabled'] = self.pricing_enabled_var.get()
            config['pricing']['check_interval_minutes'] = int(self.pricing_interval_var.get())
            config['pricing']['min_price'] = int(self.min_price_var.get())

            strategies = []
            for days_var, pct_var in self.strategy_entries:
                strategies.append({
                    'days_unsold': int(days_var.get()),
                    'discount_percent': int(pct_var.get()),
                })
            config['pricing']['strategies'] = strategies

            config['auto_reply']['enabled'] = self.reply_enabled_var.get()
            config['auto_reply']['check_interval_seconds'] = int(self.reply_interval_var.get())

            config['logging']['level'] = self.log_level_var.get()

            save_config(config)
            messagebox.showinfo(t("success"), t("save_success"))
            logger.info("设置已保存")

        except ValueError as e:
            messagebox.showerror(t("error"), t("save_error_num", error=e))
        except Exception as e:
            messagebox.showerror(t("error"), t("save_error", error=e))
            logger.error(f"保存设置出错: {e}")

    def on_show(self):
        pass
