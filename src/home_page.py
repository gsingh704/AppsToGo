import os
import json
import shutil
import subprocess
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio


class Home_page(Adw.Application):
    """
    A class representing the home page of the AppsToGo application.

    """

    def __init__(self, ui) -> None:
        """
        Initializes the Home_page object.

        :param ui: the Ui file
        """
        super().__init__()
        self.ui = ui
        self.portable_home_path = ""
        self.appimage_list = []
        self.appimage_rows = []

        self.ui.select_appimage_button.connect("clicked", self.select_appimage)
        self.ui.set_portable_home_button.connect("clicked", self.set_portable_home)
        self.load_portable_home_path_config()
        self.load_appimage_list_from_config()

    def scan_folder(self, action, param):
        """
        Opens a file dialog to select a folder to scan for appimages.

        :param action: the action that triggered the scan_folder method
        :param param: the parameter of the action that triggered the scan_folder method
        """
        Gtk.FileDialog.select_folder(
            Gtk.FileDialog.new(), None, None, self.scan_folder_callback
        )

    def scan_folder_callback(self, dialog, result):
        """
        Callback function for the scan_folder method.

        :param dialog: the dialog that triggered the scan_folder_callback method
        :param result: the result of the dialog that triggered the scan_folder_callback method
        """
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
        """
        Creates a new appimage row in the UI.

        :param file: the path to the appimage file
        """
        appimage_name = os.path.basename(file)

        appimage_name = self.copy_appimage(file)
        if appimage_name is not None:
            self.create_appimage_row(appimage_name, self.portable_home_path)
            self.save_appimage_list_to_config(appimage_name)

    def copy_appimage(self, appimage_origin):
        """
        Copies the appimage file to the portable home directory and creates a data folder for the appimage.

        :param appimage_origin: the path to the appimage file
        """
        appimage_name = os.path.splitext(os.path.basename(appimage_origin))[0]
        appimage_destination = os.path.join(
            self.portable_home_path, appimage_name, appimage_name + ".AppImage"
        )
        if os.path.exists(appimage_destination):
            self.ui.show_toast(appimage_name + " already exists", 3000)
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
        """
        Creates a new appimage row in the UI.

        :param appimage_name: the name of the appimage file
        :param portable_home_path: the path to the portable home directory
        """
        appimage_group = self.ui.appimage_group

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
        """
        Opens a dialog to edit the name of the appimage.

        :param button: the button that triggered the edit_appimage method
        :param appimage_name: the name of the appimage file
        :param portable_home_path: the path to the portable home directory
        :param appimage_group: the appimage group
        :param appimage_row: the appimage row
        """

        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            margin_bottom=10,
            margin_end=10,
            margin_start=10,
            margin_top=10,
            spacing=10,
        )
        dialog = Adw.MessageDialog(
            transient_for=self.ui.win,
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
        appimage_row,
        dialog,
    ):
        """
        Saves the new name of the appimage.

        :param button: the button that triggered the save_edit method
        :param entry: the entry field of the dialog
        :param appimage_name: the name of the appimage file
        :param portable_home_path: the path to the portable home directory
        :param appimage_row: the appimage row
        :param dialog: the dialog
        """
        new_appimage_name = entry.get_text()
        if new_appimage_name == "":
            self.ui.show_toast("Name cannot be empty", 3000)
            return
        if new_appimage_name == appimage_name:
            dialog.close()
            return
        new_appimage_folder = os.path.join(portable_home_path, new_appimage_name)
        if os.path.exists(new_appimage_folder):
            self.ui.show_toast(new_appimage_name + " already exists", 3000)
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
        """
        Closes the dialog.
        """
        dialog.close()

    def confirm_remove(self, button, appimage_name, portable_home_path, appimage_row):
        """
        Opens a dialog to confirm the removal of the appimage.

        :param button: the button that triggered the confirm_remove method
        :param appimage_name: the name of the appimage file
        :param portable_home_path: the path to the portable home directory
        :param appimage_row: the appimage row
        """
        dialog = Adw.MessageDialog(
            heading="Are you sure you want to remove " + appimage_name + "?",
            transient_for=self.ui.win,
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
        """
        Handles the user's response to the remove dialog.

        :param dialog: the dialog that triggered the handle_remove_response method
        :param response_id: the response id of the dialog that triggered the handle_remove_response method
        :param appimage_name: the name of the appimage file
        :param portable_home_path: the path to the portable home directory
        :param appimage_row: the appimage row
        """
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
                self.ui.appimage_group.remove(appimage_row)

                if appimage_row in self.appimage_rows:
                    self.appimage_rows.remove(appimage_row)

                self.ui.show_toast(appimage_name + " removed", 3000)

    def open_appimage_folder(self, button, appimage_path):
        """
        Opens the folder containing the AppImage.

        :param button: the button that triggered the open_appimage_folder method
        :param appimage_path: the path to the appimage file
        """
        appimage_data_folder = os.path.join(os.path.dirname(appimage_path))
        subprocess.Popen(["xdg-open", appimage_data_folder])

    def run_appimage(self, button, appimage_path):
        """
        Runs the AppImage.

        :param button: the button that triggered the run_appimage method
        :param appimage_path: the path to the appimage file
        """
        subprocess.Popen([appimage_path])

    def set_portable_home(self, button):
        """
        Opens a file dialog to select the portable home directory.
        """
        Gtk.FileDialog.select_folder(
            Gtk.FileDialog.new(), None, None, self.set_portable_home_callback
        )

    def set_portable_home_callback(self, dialog, result):
        """
        Callback function for the portable home directory file dialog.

        :param dialog (Gtk.FileChooserDialog): The file dialog.
        :param result (int): The result of the file dialog.
        """
        try:
            folder = dialog.select_folder_finish(result)
            if folder is not None:
                selected_path = folder.get_path()
                self.portable_home_path = os.path.join(selected_path, "AppsToGo")
                os.makedirs(self.portable_home_path, exist_ok=True)

                self.ui.portable_home_button_content.set_label(self.portable_home_path)

                config_path = os.path.join(os.path.expanduser("~/.config/AppsToGo"))
                os.makedirs(config_path, exist_ok=True)
                config_file = os.path.join(config_path, "config.json")
                with open(config_file, "w") as f:
                    f.write(self.portable_home_path)
                self.reload_appimage_list()
                self.download_latest()

        except GLib.Error as error:
            print(f"Error selecting folder: {error.message}")
            Gtk.AppChooserDialog.new()

    def download_latest(self):
        dialog = Adw.MessageDialog(
            heading="Download AppsToGo?",
            transient_for=self.ui.win,
            body="Do you want to download the latest version of AppsToGo?",
            close_response="No",
            default_response="No",
        )
        dialog.add_response("No", "No")
        dialog.add_response("Yes", "Yes")

        dialog.set_response_appearance("Yes", Adw.ResponseAppearance.DESTRUCTIVE)

        dialog.connect(
            "response",
            self.handle_download_response,
        )
        dialog.present()

    def handle_download_response(self, dialog, response_id):
        """
        Handles the user's response to the download dialog.

        :param dialog: the dialog that triggered the handle_download_response method
        :param response_id: the response id of the dialog that triggered the handle_download_response method
        """
        if response_id == "Yes":
            try:
                url = "https://github.com/gsingh704/AppsToGo/releases/download/v0.0.2/AppsToGo-0.0.2-x86_64.AppImage"
                subprocess.run(["wget", url, "-P", self.portable_home_path])
                subprocess.run(
                    [
                        "chmod",
                        "a+x",
                        os.path.join(
                            self.portable_home_path, "AppsToGo-0.0.2-x86_64.AppImage"
                        ),
                    ]
                )
                self.ui.show_toast("Downloaded AppsToGo", 3000)
            except Exception as e:
                print(e)
                self.ui.show_toast("Error downloading AppsToGo", 3000)
        dialog.close()

    def reload_appimage_list(self):
        """
        Reloads the list of AppImages.
        """
        for row in self.appimage_rows:
            self.ui.appimage_group.remove(row)
        self.appimage_rows = []
        self.load_appimage_list_from_config()

    def select_appimage(self, button):
        """
        Opens a file dialog to select an AppImage.
        """
        select_appimage_dialog = Gtk.FileDialog.new()
        filter_appimage = Gtk.FileFilter()
        filter_appimage.set_name("AppImage files")
        filter_appimage.add_pattern("*.AppImage")
        filter_appimage.add_pattern("*.appimage")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_appimage)
        select_appimage_dialog.set_filters(filters)
        select_appimage_dialog.set_default_filter(filter_appimage)
        select_appimage_dialog.open(self.ui.win, None, self.select_appimage_callback)

    def select_appimage_callback(self, dialog, result):
        """
        Callback function for the AppImage file dialog.

        :param dialog (Gtk.FileChooserDialog): The file dialog.
        :param result (int): The result of the file dialog.
        """
        try:
            file = dialog.open_finish(result)
            if file is not None:
                file_origin = file.get_path()
                self.create_copy_appimage_row(file_origin)

        except GLib.Error as error:
            print(f"Error selecting file: {error.message}")
            Gtk.AppChooserDialog.new()

    def load_portable_home_path_config(self):
        """
        Loads the portable home directory path from the config file.
        """
        try:
            config_file = os.path.join(
                os.path.expanduser("~/.config/AppsToGo/config.json")
            )
            with open(config_file, "r") as f:
                self.portable_home_path = f.read()
        except FileNotFoundError:
            self.portable_home_path = "Not set"
        self.ui.portable_home_button_content.set_label(self.portable_home_path)

    def save_appimage_list_to_config(self, appimage_name):
        """
        Saves the list of AppImages to the config file.

        :param appimage_name: the name of the appimage file
        """
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
        """
        Loads the list of AppImages from the config file.
        """
        portable_home_path = self.portable_home_path
        config_file = os.path.join(portable_home_path, ".config")
        if not os.path.exists(config_file):
            self.appimage_list = []
            return []
        with open(config_file, "r") as f:
            self.appimage_list = json.load(f)
        for appimage in self.appimage_list:
            self.create_appimage_row(appimage, portable_home_path)

    def open_portable_home(self, action, param):
        """
        Opens the portable home directory.
        """
        subprocess.Popen(["xdg-open", self.portable_home_path])

    def export_all(self, action, param):
        """
        Exports all the portable home folder as zip, ask the user where to save it.
        """

        Gtk.FileDialog.select_folder(
            Gtk.FileDialog.new(), None, None, self.export_all_callback
        )

    def export_all_callback(self, dialog, result):
        """
        Callback function for the export all method.

        :param dialog (Gtk.FileChooserDialog): The file dialog.
        :param result (int): The result of the file dialog.
        """
        try:
            folder = dialog.select_folder_finish(result)
            if folder is not None:
                selected_path = folder.get_path()
                shutil.make_archive(
                    selected_path + "/AppsToGo", "zip", self.portable_home_path
                )
                self.ui.show_toast("Exported", 3000)
        except GLib.Error as error:
            print(f"Error selecting folder: {error.message}")
            Gtk.AppChooserDialog.new()
