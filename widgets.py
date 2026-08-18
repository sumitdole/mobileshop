"""
widgets.py
----------
Small shared pieces used by every screen: color constants and a couple
of reusable KivyMD widget helpers, so all five screens look consistent.
"""

from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivy.metrics import dp

PRIMARY = "2563EB"
SUCCESS = "16A34A"
DANGER = "DC2626"
WARNING = "D97706"
MUTED = "6B7280"


class TouchCard(ButtonBehavior, MDCard):
    """
    Plain MDCard does NOT fire on_release in KivyMD (it isn't a button).
    This mixes in Kivy's core ButtonBehavior so `on_release=...` actually
    works — used anywhere a whole row/card needs to be tappable
    (Customers list, Inventory list).
    """
    pass


def hex_rgba(hex_color, alpha=1.0):
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return [r, g, b, alpha]


class StatCard(MDCard):
    """A dashboard KPI tile: big value + small label."""

    def __init__(self, label, value="0", accent=PRIMARY, **kwargs):
        super().__init__(
            orientation="vertical", padding=dp(14), spacing=dp(4),
            size_hint_y=None, height=dp(90), radius=[12], elevation=1,
            md_bg_color=hex_rgba("FFFFFF"),
            **kwargs,
        )
        self.value_label = MDLabel(
            text=value, font_style="H6", bold=True,
            theme_text_color="Custom", text_color=hex_rgba(accent),
            size_hint_y=None, height=dp(32),
        )
        self.add_widget(self.value_label)
        self.add_widget(MDLabel(
            text=label, font_style="Caption",
            theme_text_color="Custom", text_color=hex_rgba(MUTED),
            size_hint_y=None, height=dp(20),
        ))

    def set_value(self, value):
        self.value_label.text = str(value)


def simple_dialog(title, text, buttons_text=("OK",), on_ok=None):
    """A one-off info/confirmation popup. `on_ok` is called if the first
    button is pressed; the dialog always closes on any button press."""
    box = {"dialog": None}

    def close(*_a):
        box["dialog"].dismiss()

    def confirm(*_a):
        close()
        if on_ok:
            on_ok()

    buttons = []
    if len(buttons_text) == 1:
        buttons = [MDFlatButton(text=buttons_text[0], on_release=confirm)]
    else:
        buttons = [
            MDFlatButton(text=buttons_text[0], on_release=close),
            MDFlatButton(text=buttons_text[1], on_release=confirm),
        ]

    box["dialog"] = MDDialog(title=title, text=text, buttons=buttons)
    box["dialog"].open()
    return box["dialog"]


def show_error(message):
    simple_dialog("Error", message)


def show_success(message):
    simple_dialog("Success", message)


def confirm_dialog(title, message, on_confirm):
    simple_dialog(title, message, buttons_text=("Cancel", "Yes"), on_ok=on_confirm)


class FormDialog:
    """
    A modal form built from a list of (key, MDTextField-or-Spinner) fields,
    with Cancel / Save buttons. Used by Products, Customers, and Inventory
    for Add/Edit popups so they all look and behave the same way.

    Usage:
        fields = [("name", MDTextField(hint_text="Product Name")), ...]
        FormDialog("Add Product", fields, on_save=my_save_func).open()
        # my_save_func receives a dict {key: field.text}
    """

    def __init__(self, title, fields, on_save, save_text="Save"):
        self.fields = fields  # list of (key, widget)
        self.on_save = on_save

        content = MDBoxLayout(
            orientation="vertical", spacing=dp(12), padding=dp(8),
            size_hint_y=None, adaptive_height=True,
        )
        for key, widget in fields:
            content.add_widget(widget)

        self.dialog = MDDialog(
            title=title,
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *_: self.dialog.dismiss()),
                MDFlatButton(text=save_text.upper(), on_release=self._handle_save),
            ],
        )

    def _handle_save(self, *_a):
        values = {}
        for key, widget in self.fields:
            if hasattr(widget, "text"):
                values[key] = widget.text
        self.on_save(values, self.dialog)

    def open(self):
        self.dialog.open()
