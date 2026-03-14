import json
import customtkinter as ctk
from tkinter import filedialog, messagebox
from src.core.listing_engine import ListingEngine
from src.core.template_engine import TemplateEngine
from src.data.database import ProductRepository
from src.utils.logger import setup_logger
from src.utils.i18n import t

logger = setup_logger("listing_panel")


class ListingPanel(ctk.CTkFrame):

    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.engine = None
        self.template = TemplateEngine()
        self._imported_products = []

        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(
            self, text=t("listing_title"),
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 15))

        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=1, column=0, sticky="we", padx=10, pady=5)

        import_btn = ctk.CTkButton(
            top_frame, text=t("btn_import_csv"),
            font=ctk.CTkFont(size=13), height=35,
            command=self._import_csv
        )
        import_btn.pack(side="left", padx=10, pady=10)

        add_btn = ctk.CTkButton(
            top_frame, text=t("btn_add_manual"),
            font=ctk.CTkFont(size=13), height=35,
            fg_color="#6c757d", hover_color="#5a6268",
            command=self._show_add_dialog
        )
        add_btn.pack(side="left", padx=5, pady=10)

        self.publish_btn = ctk.CTkButton(
            top_frame, text=t("btn_start_publish"),
            font=ctk.CTkFont(size=13, weight="bold"), height=35,
            fg_color="#28a745", hover_color="#218838",
            command=self._start_publish
        )
        self.publish_btn.pack(side="right", padx=10, pady=10)

        self.stop_btn = ctk.CTkButton(
            top_frame, text=t("btn_stop_publish"),
            font=ctk.CTkFont(size=13), height=35,
            fg_color="#dc3545", hover_color="#c82333",
            state="disabled",
            command=self._stop_publish
        )
        self.stop_btn.pack(side="right", padx=5, pady=10)

        progress_frame = ctk.CTkFrame(self)
        progress_frame.grid(row=2, column=0, sticky="we", padx=10, pady=5)

        self.progress_label = ctk.CTkLabel(
            progress_frame, text=t("status_ready"),
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.pack(side="left", padx=15, pady=8)

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=12)
        self.progress_bar.pack(fill="x", padx=15, pady=8, expand=True)
        self.progress_bar.set(0)

        list_frame = ctk.CTkFrame(self)
        list_frame.grid(row=3, column=0, sticky="nswe", padx=10, pady=(5, 10))
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(list_frame, fg_color="gray25", height=35)
        header_frame.grid(row=0, column=0, sticky="we")
        header_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        headers = [t("header_title"), t("header_category"), t("header_price"), t("header_status")]
        for i, text in enumerate(headers):
            ctk.CTkLabel(
                header_frame, text=text,
                font=ctk.CTkFont(size=12, weight="bold")
            ).grid(row=0, column=i, padx=10, pady=5)

        self.product_list = ctk.CTkScrollableFrame(list_frame)
        self.product_list.grid(row=1, column=0, sticky="nswe")
        self.product_list.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self._refresh_list()

    def _import_csv(self):
        file_path = filedialog.askopenfilename(
            title=t("btn_import_csv"),
            filetypes=[("CSV", "*.csv"), ("All", "*.*")]
        )
        if not file_path:
            return

        try:
            products = ListingEngine.import_from_csv(file_path, optimize=True)
            if not products:
                messagebox.showwarning(t("warning"), t("import_empty"))
                return

            product_ids = ListingEngine.add_products_to_queue(products)
            self._imported_products = product_ids
            messagebox.showinfo(t("success"), t("import_success", count=len(products)))
            self._refresh_list()

        except Exception as e:
            messagebox.showerror(t("error"), t("import_error", error=e))
            logger.error(f"CSV导入出错: {e}")

    def _show_add_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title(t("dialog_add_title"))
        dialog.geometry("500x600")
        dialog.transient(self.app)
        dialog.grab_set()

        fields = {}
        field_configs = [
            ("title", t("field_title"), ""),
            ("price", t("field_price"), ""),
            ("category", t("field_category"), ""),
            ("condition", t("field_condition"), "目立った傷や汚れなし"),
            ("notes", t("field_notes"), ""),
        ]

        for i, (key, label, default) in enumerate(field_configs):
            ctk.CTkLabel(
                dialog, text=label,
                font=ctk.CTkFont(size=13)
            ).pack(padx=20, pady=(10 if i == 0 else 2, 2), anchor="w")

            if key == "notes":
                entry = ctk.CTkTextbox(dialog, height=100, font=ctk.CTkFont(size=12))
            else:
                entry = ctk.CTkEntry(dialog, font=ctk.CTkFont(size=12), height=35)
                if default:
                    entry.insert(0, default)

            entry.pack(fill="x", padx=20, pady=(0, 5))
            fields[key] = entry

        ctk.CTkLabel(
            dialog, text=t("field_images"),
            font=ctk.CTkFont(size=13)
        ).pack(padx=20, pady=(2, 2), anchor="w")

        images_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        images_frame.pack(fill="x", padx=20, pady=(0, 5))

        images_entry = ctk.CTkEntry(images_frame, font=ctk.CTkFont(size=12), height=35)
        images_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        def browse_images():
            paths = filedialog.askopenfilenames(
                title=t("btn_browse"),
                filetypes=[("Images", "*.jpg *.jpeg *.png *.webp")]
            )
            if paths:
                images_entry.delete(0, "end")
                images_entry.insert(0, ";".join(paths))

        ctk.CTkButton(
            images_frame, text=t("btn_browse"), width=60, height=35,
            command=browse_images
        ).pack(side="right")

        fields["images"] = images_entry

        optimize_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            dialog, text=t("chk_optimize"),
            variable=optimize_var,
            font=ctk.CTkFont(size=12)
        ).pack(padx=20, pady=10, anchor="w")

        def save_product():
            title_val = fields["title"].get() if isinstance(fields["title"], ctk.CTkEntry) else ""
            price_str = fields["price"].get() if isinstance(fields["price"], ctk.CTkEntry) else "0"

            if not title_val:
                messagebox.showwarning(t("warning"), t("warn_no_title"))
                return

            try:
                price = int(price_str)
            except ValueError:
                messagebox.showwarning(t("warning"), t("warn_invalid_price"))
                return

            product = {
                'title': title_val,
                'price': price,
                'category': fields["category"].get(),
                'condition': fields["condition"].get(),
                'notes': fields["notes"].get("1.0", "end").strip() if isinstance(fields["notes"], ctk.CTkTextbox) else "",
            }

            images_str = fields["images"].get()
            if images_str:
                image_list = [p.strip() for p in images_str.split(';') if p.strip()]
                product['images'] = json.dumps(image_list)
            else:
                product['images'] = '[]'

            if optimize_var.get():
                product = self.template.process_product(product)

            ProductRepository.add(product)
            dialog.destroy()
            self._refresh_list()
            messagebox.showinfo(t("success"), t("add_success"))

        ctk.CTkButton(
            dialog, text=t("btn_add_queue"),
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40, fg_color="#28a745", hover_color="#218838",
            command=save_product
        ).pack(fill="x", padx=20, pady=15)

    def _refresh_list(self):
        for widget in self.product_list.winfo_children():
            widget.destroy()

        products = ProductRepository.get_all()

        if not products:
            ctk.CTkLabel(
                self.product_list, text=t("no_products"),
                font=ctk.CTkFont(size=13), text_color="gray"
            ).grid(row=0, column=0, columnspan=4, pady=30)
            return

        status_colors = {
            "pending": "#3498db", "listed": "#2ecc71",
            "sold": "#e67e22", "failed": "#e74c3c",
        }
        status_map = {
            "pending": t("status_pending"), "listed": t("status_listed"),
            "sold": t("status_sold"), "failed": t("status_failed"),
        }

        for i, p in enumerate(products):
            status_color = status_colors.get(p['status'], "gray")
            status_text = status_map.get(p['status'], p['status'])

            ctk.CTkLabel(
                self.product_list, text=p['title'][:25],
                font=ctk.CTkFont(size=12)
            ).grid(row=i, column=0, padx=10, pady=3, sticky="w")

            ctk.CTkLabel(
                self.product_list, text=(p.get('category') or '-')[:15],
                font=ctk.CTkFont(size=12), text_color="gray"
            ).grid(row=i, column=1, padx=10, pady=3)

            ctk.CTkLabel(
                self.product_list, text=f"¥{p['price']:,}",
                font=ctk.CTkFont(size=12)
            ).grid(row=i, column=2, padx=10, pady=3)

            ctk.CTkLabel(
                self.product_list, text=status_text,
                font=ctk.CTkFont(size=12), text_color=status_color
            ).grid(row=i, column=3, padx=10, pady=3)

    def _start_publish(self):
        if not self.app.browser.is_running:
            messagebox.showwarning(t("warning"), t("need_browser"))
            return

        pending = ProductRepository.get_all(status='pending')
        if not pending:
            messagebox.showinfo(t("warning"), t("no_pending"))
            return

        self.engine = ListingEngine(self.app.browser)
        self.engine.set_progress_callback(self._on_progress)

        self.publish_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

        self.app.run_async(self.engine.publish_queue())

    def _stop_publish(self):
        if self.engine:
            self.engine.stop()
        self.publish_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_label.configure(text=t("status_stopped"))

    def _on_progress(self, current, total, title, status):
        self.app.after(0, lambda: self._update_progress(current, total, title, status))

    def _update_progress(self, current, total, title, status):
        self.progress_bar.set(current / total if total > 0 else 0)
        self.progress_label.configure(text=f"[{current}/{total}] {title[:20]} - {status}")

        if current >= total:
            self.publish_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self._refresh_list()

    def on_show(self):
        self._refresh_list()
