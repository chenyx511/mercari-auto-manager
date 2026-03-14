import customtkinter as ctk
from tkinter import messagebox
from src.core.reply_engine import ReplyEngine
from src.data.database import MessageRepository
from src.utils.config import get
from src.utils.logger import setup_logger
from src.utils.i18n import t

logger = setup_logger("reply_panel")


class ReplyPanel(ctk.CTkFrame):

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.engine = None

        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(
            self, text=t("reply_title"),
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 15))

        rules_frame = ctk.CTkFrame(self)
        rules_frame.grid(row=1, column=0, sticky="we", padx=10, pady=5)

        ctk.CTkLabel(
            rules_frame, text=t("reply_rules"),
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(padx=15, pady=(10, 5), anchor="w")

        rules = get('auto_reply.rules', [])
        for rule in rules:
            keywords = ', '.join(rule.get('keywords', []))
            reply = rule.get('reply', '')[:60]
            text = f"  Keywords: [{keywords}]\n      -> {reply}..."
            ctk.CTkLabel(
                rules_frame, text=text,
                font=ctk.CTkFont(size=12), justify="left"
            ).pack(padx=15, pady=3, anchor="w")

        interval = get('auto_reply.check_interval_seconds', 120)
        ctk.CTkLabel(
            rules_frame, text=t("reply_interval_fmt", sec=interval),
            font=ctk.CTkFont(size=12), text_color="gray"
        ).pack(padx=15, pady=(5, 10), anchor="w")

        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=2, column=0, sticky="we", padx=10, pady=5)

        self.start_btn = ctk.CTkButton(
            control_frame, text=t("btn_start_reply"),
            font=ctk.CTkFont(size=13, weight="bold"), height=38,
            fg_color="#28a745", hover_color="#218838",
            command=self._start_monitoring
        )
        self.start_btn.pack(side="left", padx=10, pady=10)

        self.stop_btn = ctk.CTkButton(
            control_frame, text=t("btn_stop_reply"),
            font=ctk.CTkFont(size=13), height=38,
            fg_color="#dc3545", hover_color="#c82333",
            state="disabled",
            command=self._stop_monitoring
        )
        self.stop_btn.pack(side="left", padx=5, pady=10)

        self.status_label = ctk.CTkLabel(
            control_frame, text=t("reply_status_off"),
            font=ctk.CTkFont(size=13), text_color="gray"
        )
        self.status_label.pack(side="right", padx=15, pady=10)

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=3, column=0, sticky="nswe", padx=10, pady=(5, 10))
        log_frame.grid_rowconfigure(1, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            log_frame, text=t("reply_log"),
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        self.log_textbox = ctk.CTkTextbox(
            log_frame, font=ctk.CTkFont(size=12), state="disabled"
        )
        self.log_textbox.grid(row=1, column=0, sticky="nswe", padx=15, pady=(5, 15))

    def _start_monitoring(self):
        if not self.app.browser.is_running:
            messagebox.showwarning(t("warning"), t("need_browser"))
            return

        self.engine = ReplyEngine(self.app.browser)
        self.engine.set_log_callback(self._on_reply_log)

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_label.configure(text=t("reply_status_on"), text_color="#28a745")

        self.app.run_async(self.engine.start_monitoring())

    def _stop_monitoring(self):
        if self.engine:
            self.engine.stop()
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text=t("reply_status_stop"), text_color="gray")

    def _on_reply_log(self, buyer_msg, reply_msg, product_id, status):
        self.app.after(0, lambda: self._update_log(buyer_msg, reply_msg, product_id, status))

    def _update_log(self, buyer_msg, reply_msg, product_id, status):
        self.log_textbox.configure(state="normal")
        line = (
            f"[{status}] Product: {product_id}\n"
            f"  Buyer: {buyer_msg[:50]}\n"
            f"  Reply: {reply_msg[:50]}\n"
            f"{'─' * 50}\n"
        )
        self.log_textbox.insert("end", line)
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def on_show(self):
        self._load_message_history()

    def _load_message_history(self):
        try:
            messages = MessageRepository.get_recent(20)
            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", "end")

            if messages:
                for msg in messages:
                    time_str = msg.get('replied_at', '')[:19] if msg.get('replied_at') else ''
                    line = (
                        f"[{time_str}] Product: {msg.get('mercari_product_id', '-')}\n"
                        f"  Buyer: {msg.get('buyer_message', '')[:50]}\n"
                        f"  Reply: {msg.get('reply_message', '')[:50]}\n"
                        f"{'─' * 50}\n"
                    )
                    self.log_textbox.insert("end", line)
            else:
                self.log_textbox.insert("end", t("no_reply_log") + "\n")

            self.log_textbox.configure(state="disabled")
        except Exception as e:
            logger.error(f"加载消息历史出错: {e}")
