"""
screens/customers.py
---------------------
Customer list with credit (udhar) balance shown right on each row,
since that's the number a shop owner checks most often. Tap a
customer to see purchase history and record a credit payment.
"""

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDFloatingActionButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.dialog import MDDialog
from kivy.uix.spinner import Spinner
from kivy.metrics import dp

import database as db
import utils
from widgets import FormDialog, show_error, show_success, hex_rgba, TouchCard, DANGER, MUTED


class CustomersScreen(MDBoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.app = app

        header = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None, height=dp(90))
        header.add_widget(MDLabel(text="Customers", font_style="H5", bold=True, size_hint_y=None, height=dp(36)))
        self.search_field = MDTextField(hint_text="Search by name or phone...")
        self.search_field.bind(text=lambda *_: self.refresh())
        header.add_widget(self.search_field)
        self.add_widget(header)

        scroll = MDScrollView()
        self.list_box = MDBoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12),
                                     size_hint_y=None, adaptive_height=True)
        scroll.add_widget(self.list_box)
        self.add_widget(scroll)

        float_layer = MDFloatLayout(size_hint_y=None, height=0)
        fab = MDFloatingActionButton(icon="account-plus", pos_hint={"right": 0.97, "y": 0.03},
                                      on_release=lambda *_: self.open_add_dialog())
        float_layer.add_widget(fab)
        self.add_widget(float_layer)

        self.refresh()

    def refresh(self):
        conn = db.get_connection()
        term = self.search_field.text.strip()
        query = "SELECT * FROM customers WHERE 1=1"
        params = []
        if term:
            query += " AND (name LIKE ? OR phone LIKE ?)"
            params += [f"%{term}%", f"%{term}%"]
        query += " ORDER BY name LIMIT 300"
        customers = conn.execute(query, params).fetchall()

        self.list_box.clear_widgets()
        if not customers:
            self.list_box.add_widget(MDLabel(text="No customers found.", size_hint_y=None, height=dp(30)))
            conn.close()
            return

        for c in customers:
            billed = conn.execute("SELECT COALESCE(SUM(credit_amount),0) s FROM bills WHERE customer_id=?", (c["id"],)).fetchone()["s"]
            paid = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM credit_payments WHERE customer_id=?", (c["id"],)).fetchone()["s"]
            balance = round(billed - paid, 2)
            self.list_box.add_widget(self._build_row(c, balance))
        conn.close()

    def _build_row(self, c, balance):
        card = TouchCard(orientation="horizontal", padding=dp(10), spacing=dp(8),
                       size_hint_y=None, height=dp(66), radius=[10], elevation=1,
                       md_bg_color=hex_rgba("FFFFFF"), on_release=lambda *_a: self._show_detail(c["id"]))

        info = MDBoxLayout(orientation="vertical")
        info.add_widget(MDLabel(text=c["name"], bold=True, font_style="Subtitle2"))
        info.add_widget(MDLabel(text=c["phone"] or "No phone", font_style="Caption",
                                 theme_text_color="Custom", text_color=hex_rgba(MUTED)))
        card.add_widget(info)

        balance_color = DANGER if balance > 0 else MUTED
        balance_label = MDLabel(
            text=f"Credit:\n{utils.currency(balance)}", halign="right", font_style="Caption",
            theme_text_color="Custom", text_color=hex_rgba(balance_color),
        )
        card.add_widget(balance_label)
        return card

    def open_add_dialog(self):
        name_field = MDTextField(hint_text="Customer Name *")
        phone_field = MDTextField(hint_text="Phone Number", input_filter="int")
        address_field = MDTextField(hint_text="Address")

        def save(values, dialog):
            name = values["name"].strip()
            if not name:
                show_error("Customer name is required.")
                return
            conn = db.get_connection()
            conn.execute("INSERT INTO customers (name, phone, address) VALUES (?,?,?)",
                        (name, values["phone"], values["address"]))
            conn.commit()
            conn.close()
            dialog.dismiss()
            self.refresh()
            show_success("Customer added.")

        FormDialog("Add Customer", [("name", name_field), ("phone", phone_field), ("address", address_field)], save).open()

    def _show_detail(self, customer_id):
        conn = db.get_connection()
        c = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
        bills = conn.execute(
            "SELECT invoice_no, bill_date, total, payment_method FROM bills WHERE customer_id=? ORDER BY bill_date DESC LIMIT 20",
            (customer_id,),
        ).fetchall()
        billed = conn.execute("SELECT COALESCE(SUM(credit_amount),0) s FROM bills WHERE customer_id=?", (customer_id,)).fetchone()["s"]
        paid = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM credit_payments WHERE customer_id=?", (customer_id,)).fetchone()["s"]
        conn.close()
        balance = round(billed - paid, 2)

        box = MDBoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, adaptive_height=True, padding=dp(8))
        box.add_widget(MDLabel(text=f"Phone: {c['phone'] or '-'}", size_hint_y=None, height=dp(24)))
        box.add_widget(MDLabel(text=f"Credit Balance: {utils.currency(balance)}", bold=True, size_hint_y=None, height=dp(24)))
        box.add_widget(MDLabel(text="Recent Purchases:", bold=True, size_hint_y=None, height=dp(24)))
        if not bills:
            box.add_widget(MDLabel(text="No purchases yet.", size_hint_y=None, height=dp(22), font_style="Caption"))
        for b in bills:
            box.add_widget(MDLabel(
                text=f"{b['invoice_no']}  {b['bill_date'][:16]}  {utils.currency(b['total'])}",
                font_style="Caption", size_hint_y=None, height=dp(20),
            ))

        dialog_holder = {}

        def open_payment_form(*_a):
            dialog_holder["dialog"].dismiss()
            self._open_payment_dialog(customer_id, balance)

        buttons = [
            MDFlatButton(text="CLOSE", on_release=lambda *_a: dialog_holder["dialog"].dismiss()),
            MDFlatButton(text="RECORD PAYMENT", on_release=open_payment_form),
        ]
        dialog_holder["dialog"] = MDDialog(title=c["name"], type="custom", content_cls=box, buttons=buttons)
        dialog_holder["dialog"].open()

    def _open_payment_dialog(self, customer_id, current_balance):
        amount_field = MDTextField(hint_text=f"Payment Amount (outstanding: {utils.currency(current_balance)})", input_filter="float")
        method_spinner = Spinner(text="Cash", values=["Cash", "UPI", "Card"], size_hint_y=None, height=dp(44))

        def save(values, dialog):
            try:
                amount = utils.validate_positive_number(values["amount"], "Amount")
                if amount <= 0:
                    raise ValueError("Enter an amount greater than zero.")
            except ValueError as e:
                show_error(str(e))
                return
            conn = db.get_connection()
            conn.execute("INSERT INTO credit_payments (customer_id, amount, method) VALUES (?,?,?)",
                        (customer_id, amount, values["method"]))
            conn.commit()
            conn.close()
            dialog.dismiss()
            self.refresh()
            self.app.refresh_dashboard()
            show_success("Payment recorded.")

        FormDialog("Record Credit Payment", [("amount", amount_field), ("method", method_spinner)], save, save_text="Record").open()
