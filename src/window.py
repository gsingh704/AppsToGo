import os
import json
import shutil
import subprocess
import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio


class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("activate", self.on_activate)
        self.portable_home_path = ""
        self.appimage_list = []
        self.appimage_rows = []

    def on_activate(self, app):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay = Adw.ToastOverlay(child=box)

        self.win = Adw.ApplicationWindow(
            application=self,
            title="Apps To Go",
            default_height=400,
            default_width=600,
            content=self.toast_overlay,
        )
        self.win.add_css_class("devel")
        self.win.present()

        adw_header = Adw.HeaderBar(
            css_classes=["flat"],
        )

        self.header_menu_button = Gtk.MenuButton(
            icon_name="open-menu-symbolic",
            menu_model=self.header_menu(),
        )
        adw_header.pack_end(self.header_menu_button)

        box2 = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
        )

        self.portable_home_button_content = Adw.ButtonContent(
            icon_name="user-home-symbolic", label="Home"
        )
        self.set_portable_home_button = Adw.SplitButton(
            css_classes=["accent"],
            margin_bottom=10,
            margin_end=10,
            margin_start=10,
            margin_top=10,
            tooltip_text="Portable Home",
            menu_model=self.set_portable_home_menu(),
            child=self.portable_home_button_content,
        )

        select_appimage_button = Adw.SplitButton(
            icon_name="list-add-symbolic",
            tooltip_text="Add AppImage",
            menu_model=self.split_button_menu(),
        )
        select_appimage_button.connect("clicked", self.select_appimage)

        self.appimage_group = Adw.PreferencesGroup(
            title="Appimages",
            margin_bottom=10,
            margin_end=10,
            margin_start=10,
            margin_top=10,
            header_suffix=select_appimage_button,
        )

        box.append(adw_header)
        box.append(Adw.Clamp(child=box2))

        box2.append(self.set_portable_home_button)
        box2.append(self.appimage_group)

        self.load_portable_home_path_config()
        self.load_appimage_list_from_config()

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
        # rename appimage and home folder
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
                # Get the original position of the appimage_name in the list
                index = appimage_list.index(appimage_name)
                # Replace the old name with the new name at the same position
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
                    json.dump(appimage_list, f)  # Save the updated appimage list

                self.appimage_group.remove(appimage_row)

                # Remove the row from the tracking list
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

                # Reload appimage list and remove rows not in the new config
                self.reload_appimage_list()

        except GLib.Error as error:
            print(f"Error selecting folder: {error.message}")
            Gtk.AppChooserDialog.new()

    def reload_appimage_list(self):
        # Clear the existing appimage rows
        for row in self.appimage_rows:
            self.appimage_group.remove(row)
        self.appimage_rows = []

        # Load the appimage list from the new config
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
                self.appimage_list = (
                    []
                )  # Initialize the list if the config file doesn't exist
        else:
            with open(config_file, "r") as f:
                self.appimage_list = json.load(f)  # Load the existing appimage list

        if (
            appimage_name not in self.appimage_list
        ):  # Check if the appimage is already in the list
            self.appimage_list.append(appimage_name)

        with open(config_file, "w") as f:
            json.dump(self.appimage_list, f)  # Save the updated appimage list

    def load_appimage_list_from_config(self):
        portable_home_path = self.portable_home_path
        config_file = os.path.join(portable_home_path, ".config")
        if not os.path.exists(config_file):
            self.appimage_list = []
            return []  # Return an empty list if the config file doesn't exist
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
            version="0.1",
            comments="A portable app manager",
            website="github.com/gsingh704/AppsToGo",
            developers=["Gurjant Singh"],
            license_type=Gtk.License.GPL_3_0,
            # application_icon="folder",
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


if __name__ == "__main__":
    app = MyApp(application_id="org.gurji.AppsToGo")
    app.run(sys.argv)
