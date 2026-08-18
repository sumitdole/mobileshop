"""
screens/billing.py
-------------------
The core screen: search a product, tap to add to cart, adjust qty,
pick a customer (optional) and payment method, then Save. On save we
generate a plain-text receipt (shown on screen, and shareable via the
phone's normal Share sheet — WhatsApp, SMS, etc.) rather than a PDF.

Why not a PDF here: reportlab *can* be built for Android via Buildozer,
but it adds real risk to your first build (native deps, longer compile
time) and this app has no printer attached anyway — a share-able text
receipt is actually more useful on a phone. If you want a PDF later,
say so and I'll wire it in as a second, optional path once the basic
APK is confirmed working on your device.
"""

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivy.uix.spinner import Spinner
from kivy.metrics import dp

import database as db
import utils
from widgets import show_error, show_success, hex_rgba, PRIMARY, DANGER, MUTED


class CartRow:
    def __init__(self, product_id, name, rate, gst_percent, purchase_price, unit):
        self.product_id = product_id
        self.name = name
        self.rate = rate
        self.gst_percent = gst_percent
        self.purchase_price = purchase_price
        self.unit = unit
        self.qty = 1.0
        self.discount_percent = 0.0


class BillingScreen(MDBoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.app = app
        self.cart = []
        self.selected_customer_id = None
        self.selected_customer_name = "Walk-in Customer"

        header = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(6), size_hint_y=None, height=dp(84))
        header.add_widget(MDLabel(text="New Bill", font_style="H5", bold=True, size_hint_y=None, height=dp(34)))
        self.search_field = MDTextField(hint_text="Search product to add...")
        self.search_field.bind(text=lambda *_: self._update_search_results())
        header.add_widget(self.search_field)
        self.add_widget(header)

        self.results_box = MDBoxLayout(orientation="vertical", size_hint_y=None, adaptive_height=True, padding=(dp(16), 0))
        self.add_widget(self.results_box)

        scroll = MDScrollView()
        self.cart_box = MDBoxLayout(orientation="vertical", spacing=dp(6), padding=dp(12),
                                     size_hint_y=None, adaptive_height=True)
        scroll.add_widget(self.cart_box)
        self.add_widget(scroll)

        footer = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None, adaptive_height=True)

        cust_row = MDBoxLayout(spacing=dp(8), size_hint_y=None, height=dp(44))
        self.customer_label = MDLabel(text="Walk-in Customer", theme_text_color="Custom", text_color=hex_rgba(PRIMARY))
        cust_row.add_widget(self.customer_label)
        cust_row.add_widget(MDIconButton(icon="account-search", on_release=lambda *_: self._open_customer_picker()))
        footer.add_widget(cust_row)

        self.total_label = MDLabel(text=f"Total: {utils.currency(0)}", font_style="H6", bold=True,
                                    size_hint_y=None, height=dp(34))
        footer.add_widget(self.total_label)

        self.payment_spinner = Spinner(text="Cash", values=["Cash", "UPI", "Card", "Credit"],
                                        size_hint_y=None, height=dp(44))
        footer.add_widget(self.payment_spinner)

        save_btn = MDRaisedButton(text="SAVE BILL", size_hint_x=1, md_bg_color=hex_rgba("16A34A"),
                                   on_release=lambda *_: self._save_bill())
        footer.add_widget(save_btn)
        self.add_widget(footer)

    def _update_search_results(self):
        self.results_box.clear_widgets()
        term = self.search_field.text.strip()
        if not term:
            self.results_box.height = 0
            return
        conn = db.get_connection()
        rows = conn.execute("""
            SELECT id, name, brand, selling_price, gst_percent, purchase_price, stock_qty, unit
            FROM products WHERE is_active=1 AND (name LIKE ? OR brand LIKE ?) ORDER BY name LIMIT 6
        """, (f"%{term}%", f"%{term}%")).fetchall()
        conn.close()

        for r in rows:
            btn = MDFlatButton(
                text=f"{r['name']} — {utils.currency(r['selling_price'])} (stock {r['stock_qty']:g})",
                size_hint_x=1,
                on_release=lambda *_a, row=r: self._add_to_cart(row),
            )
            self.results_box.add_widget(btn)
        self.results_box.height = dp(44) * len(rows)

    def _add_to_cart(self, row):
        for item in self.cart:
            if item.product_id == row["id"]:
                item.qty += 1
                self._render_cart()
                self.search_field.text = ""
                return
        self.cart.append(CartRow(row["id"], row["name"], row["selling_price"], row["gst_percent"],
                                  row["purchase_price"], row["unit"]))
        self.search_field.text = ""
        self.results_box.clear_widgets()
        self.results_box.height = 0
        self._render_cart()

    def _render_cart(self):
        self.cart_box.clear_widgets()
        if not self.cart:
            self.cart_box.add_widget(MDLabel(text="Cart is empty.", size_hint_y=None, height=dp(30),
                                              theme_text_color="Custom", text_color=hex_rgba(MUTED)))
            self._recalculate()
            return

        for idx, item in enumerate(self.cart):
            row = MDCard(orientation="horizontal", padding=dp(8), spacing=dp(6),
                         size_hint_y=None, height=dp(56), radius=[8], elevation=0,
                         md_bg_color=hex_rgba("F1F5F9"))
            row.add_widget(MDLabel(text=item.name, size_hint_x=0.4))

            minus = MDIconButton(icon="minus", on_release=lambda *_a, i=item: self._change_qty(i, -1))
            qty_label = MDLabel(text=f"{item.qty:g}", size_hint_x=0.15, halign="center")
            plus = MDIconButton(icon="plus", on_release=lambda *_a, i=item: self._change_qty(i, 1))
            row.add_widget(minus)
            row.add_widget(qty_label)
            row.add_widget(plus)

            _, _, _, line_total = utils.calc_line_total(item.qty, item.rate, item.gst_percent, item.discount_percent)
            row.add_widget(MDLabel(text=utils.currency(line_total), size_hint_x=0.25, halign="right"))

            remove_btn = MDIconButton(icon="close", theme_text_color="Custom", text_color=hex_rgba(DANGER),
                                       on_release=lambda *_a, i=idx: self._remove(i))
            row.add_widget(remove_btn)
            self.cart_box.add_widget(row)

        self._recalculate()

    def _change_qty(self, item, delta):
        # Minus button never drops below 1 — use the ✕ remove button to delete a line entirely.
        item.qty = max(item.qty + delta, 1)
        self._render_cart()

    def _remove(self, idx):
        del self.cart[idx]
        self._render_cart()

    def _recalculate(self):
        total = 0.0
        for item in self.cart:
            _, _, _, line_total = utils.calc_line_total(item.qty, item.rate, item.gst_percent, item.discount_percent)
            total += line_total
        self._current_total = round(total, 2)
        self.total_label.text = f"Total: {utils.currency(self._current_total)}"

    def _open_customer_picker(self):
        search_field = MDTextField(hint_text="Search customer, or leave blank for Walk-in")
        results_box = MDBoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None, adaptive_height=True)

        box = MDBoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, adaptive_height=True, padding=dp(8))
        box.add_widget(search_field)
        box.add_widget(results_box)

        dialog_holder = {}

        def do_search(*_a):
            results_box.clear_widgets()
            term = search_field.text.strip()
            if not term:
                return
            conn = db.get_connection()
            rows = conn.execute("SELECT id, name, phone FROM customers WHERE name LIKE ? OR phone LIKE ? LIMIT 8",
                                (f"%{term}%", f"%{term}%")).fetchall()
            conn.close()
            for r in rows:
                btn = MDFlatButton(text=f"{r['name']} ({r['phone'] or 'no phone'})", size_hint_x=1,
                                    on_release=lambda *_a, row=r: pick(row["id"], row["name"]))
                results_box.add_widget(btn)

        def pick(cid, name):
            self.selected_customer_id = cid
            self.selected_customer_name = name
            self.customer_label.text = name
            dialog_holder["dialog"].dismiss()

        def use_walkin(*_a):
            self.selected_customer_id = None
            self.selected_customer_name = "Walk-in Customer"
            self.customer_label.text = "Walk-in Customer"
            dialog_holder["dialog"].dismiss()

        search_field.bind(text=do_search)

        dialog_holder["dialog"] = MDDialog(
            title="Select Customer", type="custom", content_cls=box,
            buttons=[
                MDFlatButton(text="WALK-IN", on_release=use_walkin),
                MDFlatButton(text="CLOSE", on_release=lambda *_a: dialog_holder["dialog"].dismiss()),
            ],
        )
        dialog_holder["dialog"].open()

    def _save_bill(self):
        if not self.cart:
            show_error("Cart is empty. Add at least one product.")
            return

        payment_method = self.payment_spinner.text
        if payment_method == "Credit" and self.selected_customer_id is None:
            show_error("Credit bills need a selected customer (not Walk-in). Tap the customer icon above.")
            return

        subtotal = discount_total = gst_total = profit = 0.0
        for item in self.cart:
            gross, disc_amt, gst_amt, _ = utils.calc_line_total(item.qty, item.rate, item.gst_percent, item.discount_percent)
            subtotal += gross
            discount_total += disc_amt
            gst_total += gst_amt
            profit += (item.rate - item.purchase_price) * item.qty
        total = round(subtotal - discount_total + gst_total, 2)

        amount_paid = 0.0 if payment_method == "Credit" else total
        credit_amount = total if payment_method == "Credit" else 0.0

        invoice_no = utils.next_invoice_number()
        conn = db.get_connection()
        try:
            cur = conn.execute("""
                INSERT INTO bills (invoice_no, customer_id, subtotal, discount, gst_amount, total, profit,
                    payment_method, amount_paid, credit_amount, status)
                VALUES (?,?,?,?,?,?,?,?,?,?, 'Completed')
            """, (invoice_no, self.selected_customer_id, subtotal, discount_total, gst_total, total,
                  round(profit, 2), payment_method, amount_paid, credit_amount))
            bill_id = cur.lastrowid
            for item in self.cart:
                _, _, _, line_total = utils.calc_line_total(item.qty, item.rate, item.gst_percent, item.discount_percent)
                conn.execute("""
                    INSERT INTO bill_items (bill_id, product_id, product_name, qty, rate, gst_percent,
                        discount, purchase_price_snapshot, total)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (bill_id, item.product_id, item.name, item.qty, item.rate, item.gst_percent,
                      item.discount_percent, item.purchase_price, line_total))
                conn.execute("UPDATE products SET stock_qty = stock_qty - ? WHERE id=?", (item.qty, item.product_id))
                conn.execute("""
                    INSERT INTO stock_adjustments (product_id, qty_change, reason, note)
                    VALUES (?, ?, 'Sale', ?)
                """, (item.product_id, -item.qty, f"Sold via {invoice_no}"))
            conn.commit()
        except Exception as e:
            conn.rollback()
            conn.close()
            show_error(f"Could not save bill: {e}")
            return
        conn.close()

        receipt_text = self._build_receipt_text(invoice_no, total)
        self._show_receipt(invoice_no, receipt_text)

        self.cart = []
        self.selected_customer_id = None
        self.selected_customer_name = "Walk-in Customer"
        self.customer_label.text = "Walk-in Customer"
        self.payment_spinner.text = "Cash"
        self._render_cart()
        self.app.refresh_dashboard()

    def _build_receipt_text(self, invoice_no, total):
        settings = utils.get_settings()
        lines = [
            settings.get("shop_name", "Shop"),
            settings.get("address", "") or "",
            f"Phone: {settings.get('phone','')}" if settings.get("phone") else "",
            "-" * 32,
            f"Invoice: {invoice_no}",
            f"Customer: {self.selected_customer_name}",
            "-" * 32,
        ]
        for item in self.cart:
            _, _, _, line_total = utils.calc_line_total(item.qty, item.rate, item.gst_percent, item.discount_percent)
            lines.append(f"{item.name} x{item.qty:g} = {utils.currency(line_total)}")
        lines.append("-" * 32)
        lines.append(f"TOTAL: {utils.currency(total)}")
        lines.append(f"Payment: {self.payment_spinner.text}")
        lines.append(settings.get("invoice_footer", "Thank you!"))
        return "\n".join(l for l in lines if l)

    def _show_receipt(self, invoice_no, receipt_text):
        box = MDBoxLayout(orientation="vertical", size_hint_y=None, adaptive_height=True, padding=dp(8))
        box.add_widget(MDLabel(text=receipt_text, size_hint_y=None, adaptive_height=True))

        dialog_holder = {}

        def share(*_a):
            try:
                from plyer import share
                share.share(text=receipt_text, title=f"Invoice {invoice_no}")
            except Exception:
                show_error("Sharing isn't available on this device/build.")

        dialog_holder["dialog"] = MDDialog(
            title=f"Bill Saved — {invoice_no}", type="custom", content_cls=box,
            buttons=[
                MDFlatButton(text="SHARE", on_release=share),
                MDFlatButton(text="DONE", on_release=lambda *_a: dialog_holder["dialog"].dismiss()),
            ],
        )
        dialog_holder["dialog"].open()
