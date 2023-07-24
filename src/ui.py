import os
import json
import shutil
import subprocess
import threading
import gi
import requests
import warnings

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, GdkPixbuf


class Ui(Adw.Application):
    def __init__(self) -> None:
        super().__init__()

        self.main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )
        self.toast_overlay = Adw.ToastOverlay(
            child=self.main_box,
        )
        self.win = Adw.Window(
            content=self.toast_overlay,
            default_height=400,
            default_width=700,
        )

        self.header_bar = Adw.HeaderBar(
            css_classes=["flat"],
        )
        self.header_menu_button = Gtk.MenuButton(
            icon_name="open-menu-symbolic",
        )
        self.header_bar.pack_end(self.header_menu_button)

        self.home_page_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )

        self.portable_home_button_content = Adw.ButtonContent(
            label="Not set",
            icon_name="user-home-symbolic",
        )

        self.set_portable_home_button = Adw.SplitButton(
            child=self.portable_home_button_content,
            # menu_model=self.set_portable_home_menu(),
            margin_bottom=10,
            margin_top=10,
            css_classes=["accent"],
        )

        self.select_appimage_button = Adw.SplitButton(
            icon_name="list-add-symbolic",
            # menu_model=self.split_button_menu(),
        )

        self.appimage_group = Adw.PreferencesGroup(
            header_suffix=self.select_appimage_button,
            title="AppImages",
            vexpand=True,  # Set vexpand property to True
        )

        self.download_header_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
        )

        self.search_entry = Gtk.SearchEntry(
            margin_start=20,  # Set the margin-start property to 20
        )
        self.category_combo = Gtk.ComboBoxText()

        self.download_app_group = Adw.PreferencesGroup(
            title="Download",
            header_suffix=self.download_header_box,
            margin_top=10,
            vexpand=True,  # Set vexpand property to True
            vexpand_set=True,  # Set vexpand-set property to True
        )

        self.home_page_window = Gtk.ScrolledWindow(
            child=Adw.Clamp(
                child=self.home_page_box,
                vexpand=True,  # Set vexpand property to True
            ),
        )

        self.download_window = Gtk.ScrolledWindow(
            child=Adw.Clamp(
                child=self.download_app_group,
                vexpand=True,  # Set vexpand property to True
            ),
        )

        self.stack = Adw.ViewStack.new()
        self.view_switcher = Adw.ViewSwitcher(
            stack=self.stack, policy=Adw.ViewSwitcherPolicy.WIDE
        )
        self.stack.add_titled_with_icon(
            self.home_page_window, "home", "Home", "user-home-symbolic"
        )
        self.stack.add_titled_with_icon(
            self.download_window, "download", "Download", "document-save-symbolic"
        )
        self.header_bar.set_title_widget(self.view_switcher)
        self.main_box.append(self.header_bar)
        self.main_box.append(self.stack)

        self.home_page_box.append(self.set_portable_home_button)
        self.home_page_box.append(self.appimage_group)
        self.download_header_box.append(self.search_entry)
        self.download_header_box.append(self.category_combo)

    def show_toast(self, message, timeout):
        toast = Adw.Toast.new(message)
        toast.set_timeout(timeout)
        toast.set_priority(Adw.ToastPriority.NORMAL)
        toast.connect("dismissed", toast.dismiss)

        overlay = self.toast_overlay
        overlay.add_toast(toast)

    def about(self, action, param):
        diaolog = Adw.AboutWindow(
            application_name="AppsToGo",
            version="0.0.2",
            comments="A portable app manager",
            website="github.com/gsingh704/AppsToGo",
            developers=["Gurjant Singh"],
            license_type=Gtk.License.GPL_3_0,
            issue_url="github.com/gsingh704/AppsToGo/issues",
            transient_for=self.win,
        )

        diaolog.present()
