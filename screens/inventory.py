"""
screens/inventory.py
---------------------
Stock overview, sorted so low/out-of-stock items float to the top
(that's the list a shop owner actually needs on a phone — not the
full alphabetical catalog). Tap a row to make a manual adjustment.
"""

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.scrollview import MDScrollView
from kivy.uix.spinner import Spinner
from kivy.metrics import dp

import database as db
import utils
from widgets import FormDialog, show_error, show_success, hex_rgba, TouchCard, DANGER, WARNING, MUTED

REASONS = ["Damaged", "Lost", "Returned", "Stock Correction", "Other"]


class InventoryScreen(MDBoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.app = app

        header = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None, height=dp(90))
        header.add_widget(MDLabel(text="Inventory", font_style="H5", bold=True, size_hint_y=None, height=dp(36)))
        self.search_field = MDTextField(hint_text="Search product...")
        self.search_field.bind(text=lambda *_: self.refresh())
        header.add_widget(self.search_field)
        self.add_widget(header)

        scroll = MDScrollView()
        self.list_box = MDBoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12),
                                     size_hint_y=None, adaptive_height=True)
        scroll.add_widget(self.list_box)
        self.add_widget(scroll)

        self.refresh()

    def refresh(self):
        conn = db.get_connection()
        term = self.search_field.text.strip()
        query = """
            SELECT p.id, p.name, p.stock_qty, p.unit, p.min_stock
            FROM products p WHERE p.is_active = 1
        """
        params = []
        if term:
            query += " AND p.name LIKE ?"
            params.append(f"%{term}%")
        query += " ORDER BY (p.stock_qty <= p.min_stock) DESC, p.stock_qty ASC LIMIT 300"
        rows = conn.execute(query, params).fetchall()
        conn.close()

        self.list_box.clear_widgets()
        if not rows:
            self.list_box.add_widget(MDLabel(text="No products found.", size_hint_y=None, height=dp(30)))
            return
        for r in rows:
            self.list_box.add_widget(self._build_row(r))

    def _build_row(self, r):
        if r["stock_qty"] <= 0:
            status, color = "OUT OF STOCK", DANGER
        elif r["stock_qty"] <= r["min_stock"]:
            status, color = "LOW STOCK", WARNING
        else:
            status, color = "OK", "16A34A"

        card = TouchCard(orientation="horizontal", padding=dp(10), spacing=dp(8),
                       size_hint_y=None, height=dp(64), radius=[10], elevation=1,
                       md_bg_color=hex_rgba("FFFFFF"),
                       on_release=lambda *_a, row=r: self.open_adjust_dialog(row))

        info = MDBoxLayout(orientation="vertical")
        info.add_widget(MDLabel(text=r["name"], bold=True, font_style="Subtitle2"))
        info.add_widget(MDLabel(text=f"Stock: {r['stock_qty']:g} {r['unit']}  •  Min: {r['min_stock']:g}",
                                 font_style="Caption", theme_text_color="Custom", text_color=hex_rgba(MUTED)))
        card.add_widget(info)
        card.add_widget(MDLabel(text=status, halign="right", bold=True, font_style="Caption",
                                 theme_text_color="Custom", text_color=hex_rgba(color)))
        return card

    def open_adjust_dialog(self, product):
        qty_field = MDTextField(hint_text=f"Quantity change (current stock: {product['stock_qty']:g})", input_filter="float")
        reason_spinner = Spinner(text=REASONS[0], values=REASONS, size_hint_y=None, height=dp(44))
        note_field = MDTextField(hint_text="Note (optional)")

        def save(values, dialog):
            try:
                qty_change = float(values["qty_change"])
            except (ValueError, TypeError):
                show_error("Quantity change must be a number (e.g. 5 or -3).")
                return
            conn = db.get_connection()
            conn.execute("UPDATE products SET stock_qty = stock_qty + ? WHERE id=?", (qty_change, product["id"]))
            conn.execute("""
                INSERT INTO stock_adjustments (product_id, qty_change, reason, note)
                VALUES (?,?,?,?)
            """, (product["id"], qty_change, values["reason"], values["note"]))
            conn.commit()
            conn.close()
            dialog.dismiss()
            self.refresh()
            self.app.refresh_dashboard()
            show_success("Stock adjusted.")

        FormDialog(
            f"Adjust: {product['name']}",
            [("qty_change", qty_field), ("reason", reason_spinner), ("note", note_field)],
            save, save_text="Apply",
        ).open()
