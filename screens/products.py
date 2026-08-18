"""
screens/products.py
--------------------
Product list with live search, and an Add/Edit form dialog. Tap a
product row to edit it; a visible "Delete" icon sits on each row
(phones don't have a right-click, so it has to be visible).
"""

from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton, MDFloatingActionButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.card import MDCard
from kivymd.uix.floatlayout import MDFloatLayout
from kivy.uix.spinner import Spinner
from kivy.metrics import dp

import database as db
import utils
from widgets import FormDialog, show_error, show_success, confirm_dialog, hex_rgba, DANGER, MUTED


class ProductsScreen(MDBoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.app = app

        header = MDBoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8), size_hint_y=None, height=dp(90))
        header.add_widget(MDLabel(text="Products", font_style="H5", bold=True, size_hint_y=None, height=dp(36)))
        self.search_field = MDTextField(hint_text="Search by name, brand or category...")
        self.search_field.bind(text=lambda *_: self.refresh())
        header.add_widget(self.search_field)
        self.add_widget(header)

        scroll = MDScrollView()
        self.list_box = MDBoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12),
                                     size_hint_y=None, adaptive_height=True)
        scroll.add_widget(self.list_box)
        self.add_widget(scroll)

        float_layer = MDFloatLayout(size_hint_y=None, height=0)
        fab = MDFloatingActionButton(
            icon="plus", pos_hint={"right": 0.97, "y": 0.03},
            on_release=lambda *_: self.open_add_dialog(),
        )
        float_layer.add_widget(fab)
        self.add_widget(float_layer)

        self.refresh()

    def refresh(self):
        conn = db.get_connection()
        term = self.search_field.text.strip()
        query = """
            SELECT p.*, c.name as category_name FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.is_active = 1
        """
        params = []
        if term:
            query += " AND (p.name LIKE ? OR p.brand LIKE ? OR c.name LIKE ?)"
            like = f"%{term}%"
            params += [like, like, like]
        query += " ORDER BY p.name LIMIT 300"
        rows = conn.execute(query, params).fetchall()
        conn.close()

        self.list_box.clear_widgets()
        if not rows:
            self.list_box.add_widget(MDLabel(text="No products found.", size_hint_y=None, height=dp(30)))
            return
        for r in rows:
            self.list_box.add_widget(self._build_row(r))

    def _build_row(self, r):
        card = MDCard(orientation="horizontal", padding=dp(10), spacing=dp(8),
                       size_hint_y=None, height=dp(72), radius=[10], elevation=1,
                       md_bg_color=hex_rgba("FFFFFF"))

        info = MDBoxLayout(orientation="vertical")
        stock_txt = f"Stock: {r['stock_qty']:g} {r['unit']}"
        if r["stock_qty"] <= 0:
            stock_txt += "  •  OUT OF STOCK"
        elif r["stock_qty"] <= r["min_stock"]:
            stock_txt += "  •  LOW"
        info.add_widget(MDLabel(text=r["name"], bold=True, font_style="Subtitle2"))
        info.add_widget(MDLabel(
            text=f"{r['category_name'] or '-'}  •  {utils.currency(r['selling_price'])}  •  {stock_txt}",
            font_style="Caption", theme_text_color="Custom", text_color=hex_rgba(MUTED),
        ))
        card.add_widget(info)

        edit_btn = MDIconButton(icon="pencil", on_release=lambda *_a, row=r: self.open_edit_dialog(row["id"]))
        del_btn = MDIconButton(icon="delete", theme_text_color="Custom", text_color=hex_rgba(DANGER),
                                on_release=lambda *_a, row=r: self._delete(row["id"], row["name"]))
        card.add_widget(edit_btn)
        card.add_widget(del_btn)
        return card

    def _delete(self, product_id, name):
        def do_delete():
            conn = db.get_connection()
            conn.execute("UPDATE products SET is_active = 0 WHERE id=?", (product_id,))
            conn.commit()
            conn.close()
            self.refresh()
            self.app.refresh_dashboard()
        confirm_dialog("Delete Product", f"Delete '{name}'?", do_delete)

    def _get_category_names(self):
        conn = db.get_connection()
        rows = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
        conn.close()
        return [r["name"] for r in rows] or ["Miscellaneous"]

    def open_add_dialog(self):
        self._open_form()

    def open_edit_dialog(self, product_id):
        conn = db.get_connection()
        row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        conn.close()
        if row:
            self._open_form(dict(row))

    def _open_form(self, existing=None):
        is_edit = existing is not None
        cats = self._get_category_names()

        name_field = MDTextField(hint_text="Product Name *", text=existing["name"] if is_edit else "")
        cat_spinner = Spinner(text=(self._cat_name(existing) if is_edit else cats[0]), values=cats, size_hint_y=None, height=dp(44))
        brand_field = MDTextField(hint_text="Brand", text=existing["brand"] if is_edit and existing["brand"] else "")
        purchase_field = MDTextField(hint_text="Purchase Price *", input_filter="float",
                                      text=str(existing["purchase_price"]) if is_edit else "0")
        selling_field = MDTextField(hint_text="Selling Price *", input_filter="float",
                                     text=str(existing["selling_price"]) if is_edit else "0")
        gst_field = MDTextField(hint_text="GST %", input_filter="float",
                                 text=str(existing["gst_percent"]) if is_edit else "18")
        stock_field = MDTextField(hint_text="Stock Quantity *", input_filter="float",
                                   text=str(existing["stock_qty"]) if is_edit else "0")
        unit_spinner = Spinner(text=(existing["unit"] if is_edit else "pcs"),
                                values=["pcs", "meter", "kg", "box", "roll", "set", "litre"],
                                size_hint_y=None, height=dp(44))
        min_stock_field = MDTextField(hint_text="Minimum Stock Level", input_filter="float",
                                       text=str(existing["min_stock"]) if is_edit else "5")
        shelf_field = MDTextField(hint_text="Shelf Location", text=existing["shelf_location"] if is_edit and existing["shelf_location"] else "")

        fields = [
            ("name", name_field), ("category", cat_spinner), ("brand", brand_field),
            ("purchase_price", purchase_field), ("selling_price", selling_field),
            ("gst_percent", gst_field), ("stock_qty", stock_field), ("unit", unit_spinner),
            ("min_stock", min_stock_field), ("shelf_location", shelf_field),
        ]

        def save(values, dialog):
            try:
                name = values["name"].strip()
                if not name:
                    raise ValueError("Product name is required.")
                purchase_price = utils.validate_positive_number(values["purchase_price"], "Purchase Price")
                selling_price = utils.validate_positive_number(values["selling_price"], "Selling Price")
                gst_percent = utils.validate_positive_number(values["gst_percent"], "GST %")
                stock_qty = utils.validate_positive_number(values["stock_qty"], "Stock Quantity")
                min_stock = utils.validate_positive_number(values["min_stock"], "Minimum Stock")
            except ValueError as e:
                show_error(str(e))
                return

            conn = db.get_connection()
            category_id = self._category_id_for_name(conn, values["category"])
            if is_edit:
                conn.execute("""
                    UPDATE products SET name=?, category_id=?, brand=?, purchase_price=?, selling_price=?,
                    gst_percent=?, stock_qty=?, unit=?, min_stock=?, shelf_location=?, updated_at=datetime('now')
                    WHERE id=?
                """, (name, category_id, values["brand"], purchase_price, selling_price, gst_percent,
                      stock_qty, values["unit"], min_stock, values["shelf_location"], existing["id"]))
            else:
                conn.execute("""
                    INSERT INTO products (name, category_id, brand, purchase_price, selling_price,
                    gst_percent, stock_qty, unit, min_stock, shelf_location)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (name, category_id, values["brand"], purchase_price, selling_price, gst_percent,
                      stock_qty, values["unit"], min_stock, values["shelf_location"]))
            conn.commit()
            conn.close()
            dialog.dismiss()
            self.refresh()
            self.app.refresh_dashboard()
            show_success("Product saved.")

        FormDialog("Edit Product" if is_edit else "Add Product", fields, save, save_text="Save").open()

    def _cat_name(self, existing):
        if not existing.get("category_id"):
            return self._get_category_names()[0]
        conn = db.get_connection()
        row = conn.execute("SELECT name FROM categories WHERE id=?", (existing["category_id"],)).fetchone()
        conn.close()
        return row["name"] if row else self._get_category_names()[0]

    def _category_id_for_name(self, conn, name):
        row = conn.execute("SELECT id FROM categories WHERE name=?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        return cur.lastrowid
