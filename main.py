"""
main.py (mobile)
-----------------
Entry point for the Android app. Run on a desktop for quick iteration
with `python main.py` (Kivy runs fine on a dev PC too, useful for
testing the UI before doing a full Android build) or package with
Buildozer per README_MOBILE.md.
"""

import os
from kivymd.app import MDApp
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem

import database as db

from screens.dashboard import DashboardScreen
from screens.billing import BillingScreen
from screens.products import ProductsScreen
from screens.customers import CustomersScreen
from screens.inventory import InventoryScreen


class ShopManagerApp(MDApp):
    def build(self):
        self.title = "Shop Manager"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"

        # Android-safe writable location for the SQLite file.
        data_dir = self.user_data_dir
        os.makedirs(data_dir, exist_ok=True)
        db.set_db_path(os.path.join(data_dir, "shop_data.db"))
        db.init_db()

        nav = MDBottomNavigation(panel_color=self.theme_cls.primary_color)
        self.nav = nav

        self.dashboard_screen = DashboardScreen(self)
        self.billing_screen = BillingScreen(self)
        self.products_screen = ProductsScreen(self)
        self.customers_screen = CustomersScreen(self)
        self.inventory_screen = InventoryScreen(self)

        tab_defs = [
            ("dashboard", "Home", "home", self.dashboard_screen),
            ("billing", "Bill", "cart-plus", self.billing_screen),
            ("products", "Products", "package-variant", self.products_screen),
            ("customers", "Customers", "account-group", self.customers_screen),
            ("inventory", "Stock", "warehouse", self.inventory_screen),
        ]
        for name, text, icon, screen_widget in tab_defs:
            item = MDBottomNavigationItem(name=name, text=text, icon=icon)
            item.add_widget(screen_widget)
            nav.add_widget(item)

        return nav

    def refresh_dashboard(self):
        """Called by any screen after a data-changing action, so the
        Dashboard's numbers are correct next time the user opens it."""
        if hasattr(self, "dashboard_screen"):
            self.dashboard_screen.refresh()


if __name__ == "__main__":
    ShopManagerApp().run()
