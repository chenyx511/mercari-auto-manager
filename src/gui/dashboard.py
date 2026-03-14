import customtkinter as ctk
from tkinter import messagebox
from src.automation.mercari_operations import MercariOperations
from src.data.database import ProductRepository, OperationLogRepository
from src.utils.logger import setup_logger
from src.utils.i18n import t

logger = setup_logger("dashboard")


class DashboardPanel(ctk.CTkFrame):

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="we", padx=10, pady=(10, 20))
        top_bar.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            top_bar, text=t("dashboard_title"),
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        self.sync_btn = ctk.CTkButton(
            btn_frame, text=t("btn_sync_mercari"),
            font=ctk.CTkFont(size=13),
            height=35, width=180,
            fg_color="#e67e22", hover_color="#d35400",
            command=self._sync_from_mercari
        )
        self.sync_btn.pack(side="left", padx=5)

        refresh_btn = ctk.CTkButton(
            btn_frame, text=t("btn_refresh"),
            font=ctk.CTkFont(size=13),
            height=35, width=100,
            command=self.on_show
        )
        refresh_btn.pack(side="left", padx=5)

        stats_frame = ctk.CTkFrame(self)
        stats_frame.grid(row=1, column=0, sticky="we", padx=10, pady=5)
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.stat_cards = {}
        card_configs = [
            ("pending", t("stat_pending"), "0", "#3498db"),
            ("listed", t("stat_listed"), "0", "#2ecc71"),
            ("sold", t("stat_sold"), "0", "#e67e22"),
            ("total_ops", t("stat_ops"), "0", "#9b59b6"),
        ]

        for i, (key, label, value, color) in enumerate(card_configs):
            card = self._create_stat_card(stats_frame, label, value, color)
            card.grid(row=0, column=i, sticky="we", padx=8, pady=10)
            self.stat_cards[key] = card

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, sticky="nswe", padx=10, pady=(15, 10))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        log_title = ctk.CTkLabel(
            log_frame, text=t("recent_logs"),
            font=ctk.CTkFont(size=16, weight="bold")
        )
        log_title.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        self.log_textbox = ctk.CTkTextbox(
            log_frame, font=ctk.CTkFont(size=12),
            state="disabled"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nswe", padx=15, pady=(5, 15))

    def _create_stat_card(self, parent, label: str, value: str, color: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.grid_columnconfigure(0, weight=1)

        value_label = ctk.CTkLabel(
            card, text=value,
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=color
        )
        value_label.grid(row=0, column=0, padx=15, pady=(15, 5))
        card._value_label = value_label

        name_label = ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        name_label.grid(row=1, column=0, padx=15, pady=(0, 15))

        return card

    def _sync_from_mercari(self):
        if not self.app.browser.is_running:
            messagebox.showwarning(t("warning"), t("sync_need_browser"))
            return

        self.sync_btn.configure(state="disabled", text=t("sync_start"))

        async def _do_sync():
            try:
                ops = MercariOperations(self.app.browser)

                is_logged_in = await ops.check_login_status()
                if not is_logged_in:
                    self.app.after(0, lambda: self._on_sync_error(
                        t("sync_need_browser")
                    ))
                    return

                listings = await ops.fetch_my_listings()

                imported = 0
                for item in listings:
                    existing = ProductRepository.get_all()
                    already_exists = any(
                        p.get('mercari_id') == item['mercari_id']
                        for p in existing
                    )
                    if not already_exists:
                        product = {
                            'title': item.get('title', ''),
                            'price': item.get('price', 0),
                            'category': '',
                            'condition': '目立った傷や汚れなし',
                            'images': '[]',
                        }
                        pid = ProductRepository.add(product)
                        ProductRepository.update_status(
                            pid, 'listed', item['mercari_id']
                        )
                        imported += 1

                OperationLogRepository.add(
                    'sync', None,
                    f"从 Mercari 同步 {len(listings)} 件商品 (新增 {imported} 件)"
                )

                self.app.after(0, lambda: self._on_sync_done(len(listings)))

            except Exception as e:
                logger.error(f"同步出错: {e}")
                self.app.after(0, lambda: self._on_sync_error(str(e)))

        self.app.run_async(_do_sync())

    def _on_sync_done(self, count: int):
        self.sync_btn.configure(state="normal", text=t("btn_sync_mercari"))
        messagebox.showinfo(t("success"), t("sync_done", count=count))
        self.on_show()

    def _on_sync_error(self, error: str):
        self.sync_btn.configure(state="normal", text=t("btn_sync_mercari"))
        messagebox.showerror(t("error"), t("sync_fail", error=error))

    def on_show(self):
        try:
            counts = ProductRepository.count_by_status()
            self.stat_cards["pending"]._value_label.configure(text=str(counts.get("pending", 0)))
            self.stat_cards["listed"]._value_label.configure(text=str(counts.get("listed", 0)))
            self.stat_cards["sold"]._value_label.configure(text=str(counts.get("sold", 0)))

            logs = OperationLogRepository.get_recent(20)
            self.stat_cards["total_ops"]._value_label.configure(text=str(len(logs)))

            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", "end")

            if logs:
                for log in logs:
                    time_str = log.get('created_at', '')[:19]
                    op_type = log.get('operation_type', '')
                    details = log.get('details', '')
                    status = log.get('status', '')
                    icon = "OK" if status == "success" else "NG"
                    line = f"[{time_str}] {icon} [{op_type}] {details}\n"
                    self.log_textbox.insert("end", line)
            else:
                self.log_textbox.insert("end", t("no_logs") + "\n")

            self.log_textbox.configure(state="disabled")

        except Exception as e:
            logger.error(f"刷新仪表盘出错: {e}")
