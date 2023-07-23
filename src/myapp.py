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



class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)
        self.portable_home_path = ""
        self.appimage_list = []
        self.appimage_rows = []
        self.download_app_rows = []
        warnings.filterwarnings("ignore", category=DeprecationWarning)

    def on_activate(self, app):
        self.setup_ui()
        self.data = self.getData()
        self.category_filter = None

        self.set_portable_home_button.set_menu_model(self.set_portable_home_menu())
        self.select_appimage_button.set_menu_model(self.split_button_menu())

        self.select_appimage_button.connect("clicked", self.select_appimage)
        self.set_portable_home_button.connect("clicked", self.set_portable_home)

        self.category_combo.connect("changed", self.on_category_changed)
        self.populate_categories()
        self.category_combo.set_active(0)

        self.load_portable_home_path_config()
        self.load_appimage_list_from_config()

        self.search_entry.connect("activate", self.on_search_activated)
        self.showData(self.category_filter)

    def setup_ui(self):
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
            menu_model=self.header_menu(),
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
            menu_model=self.set_portable_home_menu(),
            margin_bottom=10,
            margin_top=10,
            css_classes=["accent"],
        )

        self.select_appimage_button = Adw.SplitButton(
            icon_name="list-add-symbolic",
            menu_model=self.split_button_menu(),
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

        self.win.set_application(self)
        self.win.present()

    def scan_folder(self, action, param):
        Gtk.FileDialog.select_folder(
            Gtk.FileDialog.new(), None, None, self.scan_folder_callback
        )

    def scan_folder_callback(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder is not None:
                selected_path = folder.get_path()
                for file in os.listdir(selected_path):
                    if file.endswith(".AppImage") or file.endswith(".appimage"):
                        self.create_copy_appimage_row(os.path.join(selected_path, file))
        except GLib.Error as error:
            print(f"Error selecting folder: {error.message}")
            Gtk.AppChooserDialog.new()

    def create_copy_appimage_row(self, file):
        appimage_name = os.path.basename(file)

        appimage_name = self.copy_appimage(file)
        if appimage_name is not None:
            self.create_appimage_row(appimage_name, self.portable_home_path)
            self.save_appimage_list_to_config(appimage_name)

    def copy_appimage(self, appimage_origin):
        appimage_name = os.path.splitext(os.path.basename(appimage_origin))[0]
        appimage_destination = os.path.join(
            self.portable_home_path, appimage_name, appimage_name + ".AppImage"
        )
        if os.path.exists(appimage_destination):
            self.show_toast(appimage_name + " already exists", 3000)
            return None

        os.makedirs(os.path.dirname(appimage_destination), exist_ok=True)
        shutil.copy2(appimage_origin, appimage_destination)

        appimage_data_folder = os.path.join(
            os.path.dirname(appimage_destination), appimage_name + ".AppImage.home"
        )
        os.makedirs(appimage_data_folder, exist_ok=True)
        os.chmod(appimage_destination, 0o755)
        self.save_appimage_list_to_config(appimage_name)
        return appimage_name

    def create_appimage_row(self, appimage_name, portable_home_path):
        appimage_group = self.appimage_group

        appimage_row = Adw.ActionRow(
            title=appimage_name,
        )
        appimage_group.add(appimage_row)

        appimage_path = os.path.join(
            portable_home_path, appimage_name, appimage_name + ".AppImage"
        )

        # run
        run_button = Gtk.Button(
            icon_name="media-playback-start",
            tooltip_text="Run " + appimage_name,
            valign=Gtk.Align.CENTER,
            css_classes=["suggested-action", "circular"],
        )
        run_button.connect("clicked", self.run_appimage, appimage_path)

        # open folder
        open_appimage_folder_button = Gtk.Button(
            icon_name="folder-symbolic",
            tooltip_text="Open " + appimage_name + " folder",
            valign=Gtk.Align.CENTER,
            css_classes=["raised"],
        )
        open_appimage_folder_button.connect(
            "clicked", self.open_appimage_folder, appimage_path
        )

        # remove
        remove_button = Gtk.Button(
            icon_name="user-trash-symbolic",
            tooltip_text="Remove " + appimage_name,
            valign=Gtk.Align.CENTER,
            css_classes=["destructive-action"],
        )
        remove_button.connect(
            "clicked",
            self.confirm_remove,
            appimage_name,
            portable_home_path,
            appimage_group,
            appimage_row,
        )
        # edit
        edit_button = Gtk.Button(
            icon_name="document-edit-symbolic",
            tooltip_text="Edit " + appimage_name,
            valign=Gtk.Align.CENTER,
            css_classes=["raised"],
        )
        edit_button.connect(
            "clicked",
            self.edit_appimage,
            appimage_name,
            portable_home_path,
            appimage_group,
            appimage_row,
        )

        appimage_row.add_suffix(remove_button)
        appimage_row.add_suffix(open_appimage_folder_button)
        appimage_row.add_suffix(edit_button)
        appimage_row.add_suffix(run_button)

        self.appimage_rows.append(appimage_row)

        appimage_row.new()

    def edit_appimage(
        self, button, appimage_name, portable_home_path, appimage_group, appimage_row
    ):
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            margin_bottom=10,
            margin_end=10,
            margin_start=10,
            margin_top=10,
            spacing=10,
        )
        dialog = Adw.MessageDialog(
            transient_for=self.win,
            child=box,
        )
        heading = Gtk.Label(
            label="Edit " + appimage_name,
            margin_bottom=10,
            margin_end=10,
            margin_start=10,
            margin_top=10,
        )
        entry = Adw.EntryRow(
            text=appimage_name,
            margin_bottom=10,
            margin_end=10,
            margin_start=10,
            margin_top=10,
        )
        box2 = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=10,
            halign=Gtk.Align.END,
            margin_end=10,
        )
        save_button = Gtk.Button(
            label="Save",
            halign=Gtk.Align.END,
            css_classes=["suggested-action"],
            width_request=100,
        )
        save_button.connect(
            "clicked",
            self.save_edit,
            entry,
            appimage_name,
            portable_home_path,
            appimage_group,
            appimage_row,
            dialog,
        )
        cancel_button = Gtk.Button(
            label="Cancel",
            halign=Gtk.Align.END,
            width_request=100,
        )
        cancel_button.connect("clicked", self.cancel_edit, dialog)
        box.append(heading)
        box.append(entry)
        box.append(box2)
        box2.append(cancel_button)
        box2.append(save_button)
        dialog.present()

    def save_edit(
        self,
        button,
        entry,
        appimage_name,
        portable_home_path,
        appimage_group,
        appimage_row,
        dialog,
    ):
        new_appimage_name = entry.get_text()
        if new_appimage_name == "":
            self.show_toast("Name cannot be empty", 3000)
            return
        if new_appimage_name == appimage_name:
            dialog.close()
            return
        new_appimage_folder = os.path.join(portable_home_path, new_appimage_name)
        if os.path.exists(new_appimage_folder):
            self.show_toast(new_appimage_name + " already exists", 3000)
            return
        old_appimage_folder = os.path.join(portable_home_path, appimage_name)
        os.rename(old_appimage_folder, new_appimage_folder)
        os.rename(
            os.path.join(new_appimage_folder, appimage_name + ".AppImage"),
            os.path.join(new_appimage_folder, new_appimage_name + ".AppImage"),
        )
        os.rename(
            os.path.join(new_appimage_folder, appimage_name + ".AppImage.home"),
            os.path.join(new_appimage_folder, new_appimage_name + ".AppImage.home"),
        )
        config_file = os.path.join(portable_home_path, ".config")
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                appimage_list = json.load(f)
            if appimage_name in appimage_list:
                index = appimage_list.index(appimage_name)
                appimage_list[index] = new_appimage_name

            with open(config_file, "w") as f:
                json.dump(appimage_list, f)

        appimage_row.set_title(new_appimage_name)
        dialog.close()

    def cancel_edit(self, button, dialog):
        dialog.close()

    def confirm_remove(
        self, button, appimage_name, portable_home_path, appimage_group, appimage_row
    ):
        dialog = Adw.MessageDialog(
            heading="Are you sure you want to remove " + appimage_name + "?",
            transient_for=self.win,
            body="This will remove the AppImage and all of its data.",
            close_response="Cancel",
            default_response="Cancel",
        )
        dialog.add_response("Cancel", "Cancel")
        dialog.add_response("Remove", "Remove")

        dialog.set_response_appearance("Remove", Adw.ResponseAppearance.DESTRUCTIVE)

        dialog.connect(
            "response",
            self.handle_remove_response,
            appimage_name,
            portable_home_path,
            appimage_row,
        )
        dialog.present()

    def handle_remove_response(
        self,
        dialog,
        response_id,
        appimage_name,
        portable_home_path,
        appimage_row,
    ):
        if response_id == "Remove":
            shutil.rmtree(os.path.join(portable_home_path, appimage_name))
            config_file = os.path.join(portable_home_path, ".config")

            if os.path.exists(config_file):
                with open(config_file, "r") as f:
                    appimage_list = json.load(f)

                if appimage_name in appimage_list:
                    appimage_list.remove(appimage_name)

                with open(config_file, "w") as f:
                    json.dump(appimage_list, f)
                self.appimage_group.remove(appimage_row)

                if appimage_row in self.appimage_rows:
                    self.appimage_rows.remove(appimage_row)

                self.show_toast(appimage_name + " removed", 3000)

    def open_appimage_folder(self, button, appimage_path):
        appimage_data_folder = os.path.join(os.path.dirname(appimage_path))
        subprocess.Popen(["xdg-open", appimage_data_folder])

    def run_appimage(self, button, appimage_path):
        subprocess.Popen([appimage_path])

    def set_portable_home(self, button):
        Gtk.FileDialog.select_folder(
            Gtk.FileDialog.new(), None, None, self.set_portable_home_callback
        )

    def set_portable_home_callback(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder is not None:
                selected_path = folder.get_path()
                self.portable_home_path = os.path.join(selected_path, "AppsToGo")
                os.makedirs(self.portable_home_path, exist_ok=True)

                self.portable_home_button_content.set_label(self.portable_home_path)

                config_path = os.path.join(os.path.expanduser("~/.config/AppsToGo"))
                os.makedirs(config_path, exist_ok=True)
                config_file = os.path.join(config_path, "config.json")
                with open(config_file, "w") as f:
                    f.write(self.portable_home_path)
                self.reload_appimage_list()

        except GLib.Error as error:
            print(f"Error selecting folder: {error.message}")
            Gtk.AppChooserDialog.new()

    def reload_appimage_list(self):
        for row in self.appimage_rows:
            self.appimage_group.remove(row)
        self.appimage_rows = []
        self.load_appimage_list_from_config()

    def select_appimage(self, button):
        select_appimage_dialog = Gtk.FileDialog.new()
        filter_appimage = Gtk.FileFilter()
        filter_appimage.set_name("AppImage files")
        filter_appimage.add_pattern("*.AppImage")
        filter_appimage.add_pattern("*.appimage")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_appimage)
        select_appimage_dialog.set_filters(filters)
        select_appimage_dialog.set_default_filter(filter_appimage)
        select_appimage_dialog.open(self.win, None, self.select_appimage_callback)

    def select_appimage_callback(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file is not None:
                file_origin = file.get_path()
                self.create_copy_appimage_row(file_origin)

        except GLib.Error as error:
            print(f"Error selecting file: {error.message}")
            Gtk.AppChooserDialog.new()

    def load_portable_home_path_config(self):
        self.set_portable_home_button.connect("clicked", self.set_portable_home)
        try:
            config_file = os.path.join(
                os.path.expanduser("~/.config/AppsToGo/config.json")
            )
            with open(config_file, "r") as f:
                self.portable_home_path = f.read()
        except FileNotFoundError:
            self.portable_home_path = "Not set"
        self.portable_home_button_content.set_label(self.portable_home_path)

    def save_appimage_list_to_config(self, appimage_name):
        config_file = os.path.join(self.portable_home_path, ".config")
        if not os.path.exists(config_file):
            with open(config_file, "w") as f:
                f.write("[]")
                self.appimage_list = []
        else:
            with open(config_file, "r") as f:
                self.appimage_list = json.load(f)

        if appimage_name not in self.appimage_list:
            self.appimage_list.append(appimage_name)

        with open(config_file, "w") as f:
            json.dump(self.appimage_list, f)

    def load_appimage_list_from_config(self):
        portable_home_path = self.portable_home_path
        config_file = os.path.join(portable_home_path, ".config")
        if not os.path.exists(config_file):
            self.appimage_list = []
            return []
        with open(config_file, "r") as f:
            self.appimage_list = json.load(f)
        for appimage in self.appimage_list:
            self.create_appimage_row(appimage, portable_home_path)

    def show_toast(self, message, timeout):
        toast = Adw.Toast.new(message)
        toast.set_timeout(timeout)
        toast.set_priority(Adw.ToastPriority.NORMAL)
        toast.connect("dismissed", toast.dismiss)

        overlay = self.toast_overlay
        overlay.add_toast(toast)

    def header_menu(self):
        menu = Gio.Menu()
        menu.append("About  AppsToGo", "app.about")

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.about)
        self.add_action(about_action)
        return menu

    def set_portable_home_menu(self):
        menu = Gio.Menu()
        menu.append("Open Portable Home", "app.open_portable_home")

        open_portable_home_action = Gio.SimpleAction.new("open_portable_home", None)
        open_portable_home_action.connect("activate", self.open_portable_home)
        self.add_action(open_portable_home_action)
        return menu

    def open_portable_home(self, action, param):
        subprocess.Popen(["xdg-open", self.portable_home_path])

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

    def split_button_menu(self):
        scan_folder_action = Gio.SimpleAction.new("scan_folder", None)
        scan_folder_action.connect("activate", self.scan_folder)
        self.add_action(scan_folder_action)
        menu = Gio.Menu()
        menu.append("Scan Folder", "app.scan_folder")
        return menu

    def getData(self, selected_category=None):
        url = "https://appimage.github.io/feed.json"
        response = requests.get(url)
        data = response.json()
        return data

    def showData(self, selected_category):
        for row in self.download_app_rows:
            self.download_app_group.remove(row)
        self.download_app_rows = []
        thread = threading.Thread(
            target=self.load_data_and_images, args=(selected_category,), daemon=True
        )
        thread.start()

    def on_search_activated(self, entry):
        search_query = entry.get_text()
        self.category_combo.set_active(0)
        active_item = self.category_combo.get_active_iter()
        if active_item:
            selected_category = self.category_combo.get_model().get_value(
                active_item, 0
            )
        else:
            selected_category = None
        if not search_query:
            self.showData(selected_category)
        else:
            self.searchData(search_query)

    def searchData(self, search_query):
        for row in self.download_app_rows:
            self.download_app_group.remove(row)
        self.download_app_rows = []
        thread = threading.Thread(
            target=self.load_search_data_and_images, args=(search_query,), daemon=True
        )
        thread.start()

    def load_search_data_and_images(self, search_query):
        items = self.data["items"]
        search_results = []
        for item in items:
            name = item.get("name", "")
            description = item.get("description", "")
            if (
                search_query.lower() in name.lower()
                or search_query.lower() in description.lower()
            ):
                search_results.append(item)

        appimage_io_url = "https://appimage.github.io/database"

        self.setup_download_row(
            None, search_results, len(search_results), appimage_io_url
        )
        GLib.idle_add(
            self.download_app_group.set_title, f"Search Results - {len(search_results)}"
        )

    def load_data_and_images(self, selected_category):
        items = self.data["items"]
        appimages_count = 0
        filtered_items = []
        for item in items:
            if selected_category in item["categories"]:
                filtered_items.append(item)
                appimages_count += 1

        appimage_io_url = "https://appimage.github.io/database"

        self.setup_download_row(
            selected_category, filtered_items, appimages_count, appimage_io_url
        )
        GLib.idle_add(
            self.download_app_group.set_title, f"Appimages - {appimages_count}"
        )

    def on_category_changed(self, combo):
        active_item = combo.get_active_iter()
        if active_item:
            selected_category = combo.get_model().get_value(active_item, 0)
            self.showData(selected_category)

    def populate_categories(self):
        categories = set()
        for item in self.data["items"]:
            if "categories" in item:
                categories.update(item["categories"])
        categories = [category for category in categories if category is not None]
        self.category_combo.append_text("Categories")

        for category in sorted(categories):
            self.category_combo.append_text(category)

    def setup_download_row(
        self, selected_category, items, appimages_count, appimage_io_url
    ):
        for item in items:
            name = item["name"]
            categories = item.get("categories", [])
            authors = item.get("authors", "")
            authors_name = authors[0]["name"] if authors and len(authors) > 0 else None
            authors_url = authors[0]["url"] if authors and len(authors) > 0 else None
            license = item.get("license", "")

            icon = self.get_icon(appimage_io_url, item)
            screenshot = self.get_image(appimage_io_url, name)

            description = item.get("description", "")
            if not selected_category or (
                selected_category and selected_category in categories
            ):
                links = item["links"]

                if links is None:
                    continue
                download_url = ""
                for link in links:
                    if link["type"] == "Download":
                        download_url = link["url"]
                        break

                appimage_row = Adw.ExpanderRow(title=name, subtitle=categories)
                download_button = Gtk.Button(
                    label="Github Release",
                    margin_bottom=10,
                    margin_end=10,
                    margin_start=10,
                    margin_top=10,
                    css_classes=["suggested-action"],
                )
                download_button.connect(
                    "clicked", self.on_download_clicked, download_url
                )

                info_box = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL,
                    margin_bottom=10,
                    margin_end=10,
                    margin_start=10,
                    margin_top=10,
                    spacing=10,
                )
                author_label = Gtk.Label(
                    label=f'Author: <a href="{authors_url}">{authors_name}</a>',
                    margin_bottom=10,
                    margin_end=10,
                    margin_start=10,
                    margin_top=10,
                    wrap=True,
                    xalign=0,
                    use_markup=True,
                )
                license_label = Gtk.Label(
                    label=f"License: {license}",
                    margin_bottom=10,
                    margin_end=10,
                    margin_start=10,
                    margin_top=10,
                    wrap=True,
                    xalign=0,
                )
                description_label = Gtk.Label(
                    label=f"Description: {description}",
                    margin_bottom=10,
                    margin_end=10,
                    margin_start=10,
                    margin_top=10,
                    wrap=True,
                    xalign=0,
                )

                info_box.append(download_button)
                info_box.append(author_label)
                info_box.append(license_label)
                info_box.append(description_label)
                info_box.append(screenshot)

                appimage_row.add_row(info_box)

                appimage_row.add_prefix(icon)
                self.download_app_group.add(appimage_row)
                self.download_app_rows.append(appimage_row)

                appimages_count += 1

    def get_icon(self, appimage_io_url, item):
        icon_name = item.get("icons", "")
        icon_name = icon_name[0] if icon_name and len(icon_name) > 0 else None
        icon_url = appimage_io_url + "/" + icon_name if icon_name else None

        icon = Gtk.Image()
        icon.set_pixel_size(50)
        icon.set_from_file("assets/placeholder.png")

        if icon_url is not None:
            thread = threading.Thread(
                target=self.fetch_icon, args=(icon, icon_url), daemon=True
            )
            thread.start()

        return icon

    def fetch_icon(self, icon, icon_url):
        try:
            response = requests.get(icon_url)
            if response.status_code == 200:
                loader = GdkPixbuf.PixbufLoader()
                loader.write(response.content)
                loader.close()
                pixbuf = loader.get_pixbuf()
                if pixbuf is not None:
                    pixbuf = pixbuf.scale_simple(
                        300, 300, GdkPixbuf.InterpType.BILINEAR
                    )
                    GLib.idle_add(self.set_icon, icon, pixbuf)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching image: {e}")
            GLib.idle_add(self.set_icon, icon, None)

    def set_icon(self, icon, pixbuf):
        if pixbuf is not None:
            icon.set_from_pixbuf(pixbuf)
            icon.set_halign(Gtk.Align.CENTER)
            icon.set_valign(Gtk.Align.CENTER)
            icon.set_margin_bottom(10)
            icon.set_margin_end(10)
            icon.set_margin_start(10)
            icon.set_margin_top(10)
        else:
            icon.set_from_file("assets/placeholder.png")

    def get_image(self, appimage_url, name):
        screenshot_url = appimage_url + "/" + name + "/screenshot.png"

        screenshot = Gtk.Image()
        screenshot.set_pixel_size(400)
        screenshot.set_from_file("assets/placeholder.png")

        thread = threading.Thread(
            target=self.fetch_image, args=(screenshot, screenshot_url), daemon=True
        )
        thread.start()

        return screenshot

    def fetch_image(self, screenshot, screenshot_url):
        try:
            response = requests.get(screenshot_url)
            if response.status_code == 200:
                loader = GdkPixbuf.PixbufLoader()
                loader.write(response.content)
                loader.close()
                pixbuf = loader.get_pixbuf()
                if pixbuf is not None:
                    GLib.idle_add(self.set_image, screenshot, pixbuf)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching image: {e}")
            GLib.idle_add(self.set_image, screenshot, None)

    def set_image(self, screenshot, pixbuf):
        if pixbuf is not None:
            screenshot.set_from_pixbuf(pixbuf)
        else:
            screenshot.set_from_file("assets/placeholder.png")

    def on_download_clicked(self, button, download_url):
        Gio.AppInfo.launch_default_for_uri(download_url, None)

