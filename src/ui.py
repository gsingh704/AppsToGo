import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GdkPixbuf


class Ui(Adw.Application):
    def __init__(self) -> None:
        """
        Initializes the Ui class, which is a subclass of Adw.Application.
        """
        super().__init__()

        # Create the main box for the UI
        self.main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )

        # Create a toast overlay to display messages
        self.toast_overlay = Adw.ToastOverlay(
            child=self.main_box,
        )

        # Create the main window for the UI
        self.win = Adw.Window(
            content=self.toast_overlay,
            default_height=400,
            default_width=700,
        )

        # Create the header bar for the UI
        self.header_bar = Adw.HeaderBar(
            css_classes=["flat"],
        )

        # Create the menu button for the header bar
        self.header_menu_button = Gtk.MenuButton(
            icon_name="open-menu-symbolic",
        )

        # Add the menu button to the header bar
        self.header_bar.pack_end(self.header_menu_button)

        # Create the home page box for the UI
        self.home_page_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )

        # Create the portable home button content
        self.portable_home_button_content = Adw.ButtonContent(
            label="Not set",
            icon_name="user-home-symbolic",
        )

        # Create the split button for the portable home button
        self.set_portable_home_button = Adw.SplitButton(
            child=self.portable_home_button_content,
            margin_bottom=10,
            margin_top=10,
            css_classes=["accent"],
        )

        # Create the split button for selecting AppImages
        self.select_appimage_button = Adw.SplitButton(
            icon_name="list-add-symbolic",
        )

        # Create the preferences group for AppImages
        self.appimage_group = Adw.PreferencesGroup(
            header_suffix=self.select_appimage_button,
            title="AppImages",
            vexpand=True,
        )

        # Create the header box for the download section
        self.download_header_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
        )

        # Create the search entry for the download section
        self.search_entry = Gtk.SearchEntry(
            margin_start=20,
        )

        # Create the combo box for selecting categories in the download section
        self.category_combo = Gtk.ComboBoxText()

        # Create the preferences group for the download section
        self.download_app_group = Adw.PreferencesGroup(
            title="Download",
            header_suffix=self.download_header_box,
            margin_top=10,
            vexpand=True,
            vexpand_set=True,
        )

        # Create the scrolled window for the home page
        self.home_page_window = Gtk.ScrolledWindow(
            child=Adw.Clamp(
                child=self.home_page_box,
                vexpand=True,
            ),
        )

        # Create the scrolled window for the download section
        self.download_window = Gtk.ScrolledWindow(
            child=Adw.Clamp(
                child=self.download_app_group,
                vexpand=True,
            ),
        )

        # Create the view stack for the UI
        self.stack = Adw.ViewStack.new()

        # Create the view switcher for the UI
        self.view_switcher = Adw.ViewSwitcher(
            stack=self.stack, policy=Adw.ViewSwitcherPolicy.WIDE
        )

        # Add the home page and download section to the view stack
        self.stack.add_titled_with_icon(
            self.home_page_window, "home", "Home", "user-home-symbolic"
        )
        self.stack.add_titled_with_icon(
            self.download_window, "download", "Download", "document-save-symbolic"
        )

        # Set the title widget for the header bar to the view switcher
        self.header_bar.set_title_widget(self.view_switcher)

        # Add the header bar and view stack to the main box
        self.main_box.append(self.header_bar)
        self.main_box.append(self.stack)

        # Add the portable home button and AppImages group to the home page box
        self.home_page_box.append(self.set_portable_home_button)
        self.home_page_box.append(self.appimage_group)

        # Add the search entry and category combo to the download header box
        self.download_header_box.append(self.search_entry)
        self.download_header_box.append(self.category_combo)

    def show_toast(self, message, timeout):
        """
        Displays a toast message with the given message and timeout.

        Args:
            message (str): The message to display.
            timeout (int): The amount of time to display the message, in milliseconds.
        """
        toast = Adw.Toast.new(message)
        toast.set_timeout(timeout)
        toast.set_priority(Adw.ToastPriority.NORMAL)
        toast.connect("dismissed", toast.dismiss)

        overlay = self.toast_overlay
        overlay.add_toast(toast)

    def about(self, action, param):
        """
        Displays the About dialog for the application.
        """
        diaolog = Adw.AboutWindow(
            application_name="AppsToGo",
            version="0.0.3",
            comments="A portable app manager",
            website="github.com/gsingh704/AppsToGo",
            developers=["Gurjant Singh"],
            license_type=Gtk.License.GPL_3_0,
            issue_url="github.com/gsingh704/AppsToGo/issues",
            transient_for=self.win,
            application_icon="org.gurji.AppsToGo",
            copyright=(
                "© 2023 Gurjant Singh\n"
                "This program comes with ABSOLUTELY NO WARRANTY.\n"
                "This is free software, and you are welcome to redistribute it under certain conditions.\n"
                "See the GNU General Public License v3.0 for details."
            ),
        )

        diaolog.present()
