"""
screens/dashboard.py
---------------------
Home tab: today's sales/profit, stock alerts, pending credit, and
quick-jump buttons to the other tabs.
"""

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.scrollview import MDScrollView
from kivy.metrics import dp

import database as db
import utils
from widgets import StatCard, PRIMARY, SUCCESS, WARNING, DANGER, hex_rgba


class DashboardScreen(MDBoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.app = app

        scroll = MDScrollView()
        self.content = MDBoxLayout(
            orientation="vertical", padding=dp(16), spacing=dp(12),
            size_hint_y=None, adaptive_height=True,
        )
        scroll.add_widget(self.content)
        self.add_widget(scroll)

        self.content.add_widget(MDLabel(
            text="Dashboard", font_style="H5", bold=True,
            size_hint_y=None, height=dp(40),
        ))

        grid = MDGridLayout(cols=2, spacing=dp(10), size_hint_y=None, adaptive_height=True)
        self.cards = {}
        card_defs = [
            ("today_sales", "Today's Sales", PRIMARY),
            ("today_profit", "Today's Profit", SUCCESS),
            ("total_products", "Total Products", "6B7280"),
            ("total_customers", "Total Customers", "6B7280"),
            ("low_stock", "Low Stock", WARNING),
            ("pending_credit", "Pending Credit", DANGER),
        ]
        for key, label, accent in card_defs:
            card = StatCard(label, "0", accent=accent)
            grid.add_widget(card)
            self.cards[key] = card
        self.content.add_widget(grid)

        self.content.add_widget(MDLabel(
            text="Quick Actions", font_style="Subtitle1", bold=True,
            size_hint_y=None, height=dp(30),
        ))
        actions = MDBoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, adaptive_height=True)
        actions.add_widget(MDRaisedButton(
            text="+ New Bill", size_hint_x=1, on_release=lambda *_: self._goto("billing"),
        ))
        actions.add_widget(MDRaisedButton(
            text="View Products", size_hint_x=1, md_bg_color=hex_rgba("64748B"),
            on_release=lambda *_: self._goto("products"),
        ))
        actions.add_widget(MDRaisedButton(
            text="View Inventory / Low Stock", size_hint_x=1, md_bg_color=hex_rgba("64748B"),
            on_release=lambda *_: self._goto("inventory"),
        ))
        self.content.add_widget(actions)

        self.content.add_widget(MDLabel(
            text="Recent Bills", font_style="Subtitle1", bold=True,
            size_hint_y=None, height=dp(30),
        ))
        self.recent_bills_box = MDBoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None, adaptive_height=True)
        self.content.add_widget(self.recent_bills_box)

        self.refresh()

    def _goto(self, tab_name):
        self.app.nav.switch_tab(tab_name)

    def refresh(self):
        conn = db.get_connection()
        today_start, today_end = utils.today_range()

        today_sales = conn.execute(
            "SELECT COALESCE(SUM(total),0) s FROM bills WHERE bill_date BETWEEN ? AND ? AND status='Completed'",
            (today_start, today_end),
        ).fetchone()["s"]
        today_profit = conn.execute(
            "SELECT COALESCE(SUM(profit),0) s FROM bills WHERE bill_date BETWEEN ? AND ? AND status='Completed'",
            (today_start, today_end),
        ).fetchone()["s"]
        total_products = conn.execute("SELECT COUNT(*) c FROM products WHERE is_active=1").fetchone()["c"]
        total_customers = conn.execute("SELECT COUNT(*) c FROM customers").fetchone()["c"]
        low_stock = conn.execute(
            "SELECT COUNT(*) c FROM products WHERE is_active=1 AND stock_qty <= min_stock"
        ).fetchone()["c"]
        credit_billed = conn.execute("SELECT COALESCE(SUM(credit_amount),0) s FROM bills").fetchone()["s"]
        credit_paid = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM credit_payments").fetchone()["s"]
        pending_credit = round(credit_billed - credit_paid, 2)

        recent_bills = conn.execute("""
            SELECT b.invoice_no, COALESCE(c.name,'Walk-in') as customer, b.total, b.bill_date
            FROM bills b LEFT JOIN customers c ON b.customer_id = c.id
            ORDER BY b.id DESC LIMIT 8
        """).fetchall()
        conn.close()

        self.cards["today_sales"].set_value(utils.currency(today_sales))
        self.cards["today_profit"].set_value(utils.currency(today_profit))
        self.cards["total_products"].set_value(str(total_products))
        self.cards["total_customers"].set_value(str(total_customers))
        self.cards["low_stock"].set_value(str(low_stock))
        self.cards["pending_credit"].set_value(utils.currency(pending_credit))

        self.recent_bills_box.clear_widgets()
        if not recent_bills:
            self.recent_bills_box.add_widget(MDLabel(text="No bills yet.", size_hint_y=None, height=dp(28)))
        for b in recent_bills:
            line = f"{b['invoice_no']}  •  {b['customer']}  •  {utils.currency(b['total'])}"
            self.recent_bills_box.add_widget(MDLabel(text=line, size_hint_y=None, height=dp(26), font_style="Caption"))
