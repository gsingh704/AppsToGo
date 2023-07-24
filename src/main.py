import gi
import warnings
import sys

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio

# Import classes from other files
from download_page import Download_Page
from home_page import Home_page
from ui import Ui


class MyApp(Adw.Application):
    """
    The main application class for AppsToGo.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)

        self.ui = Ui()  # Instantiate Ui only once

        self.hp = Home_page(self.ui)
        self.dp = Download_Page(self.ui)
        self.portable_home_path = ""
        self.appimage_list = []
        self.appimage_rows = []

        warnings.filterwarnings("ignore", category=DeprecationWarning)
        self.category_combo = None

    def on_activate(self, app):
        """
        Called when the application is activated.
        """
        self.ui.header_menu_button.set_menu_model(self.header_menu())
        self.ui.set_portable_home_button.set_menu_model(self.set_portable_home_menu())
        self.ui.select_appimage_button.set_menu_model(self.split_button_menu())

        self.ui.win.set_application(app)
        self.ui.win.present()

    def header_menu(self):
        """
        Creates the header menu.
        """
        menu = Gio.Menu()
        menu.append("About AppsToGo", "app.about")

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.ui.about)
        self.add_action(about_action)

        return menu

    def set_portable_home_menu(self):
        """
        Creates the set portable home menu button.
        """
        menu = Gio.Menu()
        menu.append("Open portable home", "app.open_portable_home")

        set_portable_home_action = Gio.SimpleAction.new("open_portable_home", None)
        set_portable_home_action.connect("activate", self.hp.open_portable_home)
        self.add_action(set_portable_home_action)

        return menu

    def split_button_menu(self):
        """
        Creates the split button menu (add appimage button).
        """
        scan_folder_action = Gio.SimpleAction.new("scan_folder", None)
        scan_folder_action.connect("activate", self.hp.scan_folder)
        self.add_action(scan_folder_action)
        menu = Gio.Menu()
        menu.append("Scan Folder", "app.scan_folder")
        return menu


if __name__ == "__main__":
    app = MyApp()
    app.run(sys.argv)
