import threading
import gi
import requests

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, GdkPixbuf


class Download_Page(Adw.Application):
    """
    This class represents the download page of the AppsToGo application.
    It inherits from Adw.Application and contains methods to retrieve and display data
    about available AppImages from the appimage.github.io feed.json file.
    """

    download_app_rows = []

    def __init__(self, ui) -> None:
        """
        Initializes the Download_Page object.

        :param ui: The user interface object.
        """
        super().__init__()
        self.ui = ui

        self.data = self.getData()
        self.category_filter = None
        self.download_app_rows = []
        self.ui.category_combo.connect("changed", self.on_category_changed)
        self.populate_categories()
        self.ui.search_entry.connect("activate", self.on_search_activated)
        self.showData(self.category_filter)
        self.ui.category_combo.set_active(0)

    def getData(self, selected_category=None):
        """
        Retrieves data from the appimage.github.io feed.json file.

        :param selected_category: The selected category to filter the data by.
        :return: The retrieved data.
        """
        url = "https://appimage.github.io/feed.json"
        response = requests.get(url)
        data = response.json()
        return data

    def showData(self, selected_category):
        """
        Displays the retrieved data.

        :param selected_category: The selected category to filter the data by.
        """
        for row in self.download_app_rows:
            self.ui.download_app_group.remove(row)
        self.download_app_rows = []
        thread = threading.Thread(
            target=self.load_data_and_images, args=(selected_category,), daemon=True
        )
        thread.start()

    def on_search_activated(self, entry):
        """
        Activates the search functionality.

        :param entry: The search entry object.
        """
        search_query = entry.get_text()
        self.ui.category_combo.set_active(0)
        active_item = self.ui.category_combo.get_active_iter()
        if active_item:
            selected_category = self.ui.category_combo.get_model().get_value(
                active_item, 0
            )
        else:
            selected_category = None
        if not search_query:
            self.showData(selected_category)
        else:
            self.searchData(search_query)

    def searchData(self, search_query):
        """
        Searches for data based on the search query.

        :param search_query: The search query.
        """
        for row in self.download_app_rows:
            self.ui.download_app_group.remove(row)
        self.download_app_rows = []
        thread = threading.Thread(
            target=self.load_search_data_and_images, args=(search_query,), daemon=True
        )
        thread.start()

    def load_search_data_and_images(self, search_query):
        """
        Loads the search data and images.

        :param search_query: The search query.
        """
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
            self.ui.download_app_group.set_title,
            f"Search Results - {len(search_results)}",
        )

    def load_data_and_images(self, selected_category):
        """
        Loads the data and images.

        :param selected_category: The selected category to filter the data by.
        """
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
            self.ui.download_app_group.set_title, f"Appimages - {appimages_count}"
        )

    def on_category_changed(self, combo):
        """
        Handles the category change event.

        :param combo: The category combo object.
        """
        active_item = combo.get_active_iter()
        if active_item:
            selected_category = combo.get_model().get_value(active_item, 0)
            self.showData(selected_category)

    def populate_categories(self):
        """
        Populates the categories combo box.
        """
        categories = set()
        for item in self.data["items"]:
            if "categories" in item:
                categories.update(item["categories"])
        categories = [category for category in categories if category is not None]
        self.ui.category_combo.append_text("Categories")

        for category in sorted(categories):
            self.ui.category_combo.append_text(category)

    def setup_download_row(
        self, selected_category, items, appimages_count, appimage_io_url
    ):
        """
        Sets up the download row.

        :param selected_category: The selected category to filter the data by.
        :param items: The items to display.
        :param appimages_count: The number of appimages to display.
        :param appimage_io_url: The appimage.io url.
        """
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

                appimage_row = Adw.ExpanderRow(title=name, subtitle=authors_name)
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
                self.ui.download_app_group.add(appimage_row)
                self.download_app_rows.append(appimage_row)

                appimages_count += 1

    def get_icon(self, appimage_io_url, item):
        """
        Gets the icon.

        :param appimage_io_url: The appimage.io url.
        :param item: The item to get the icon for.
        :return: The icon.
        """
        icon_name = item.get("icons", "")
        icon_name = icon_name[0] if icon_name and len(icon_name) > 0 else None
        icon_url = appimage_io_url + "/" + icon_name if icon_name else None

        icon = Gtk.Image()
        icon.set_pixel_size(50)
        icon.set_from_icon_name("image-missing")
        icon.set_halign(Gtk.Align.CENTER)
        icon.set_valign(Gtk.Align.CENTER)
        icon.set_margin_bottom(10)
        icon.set_margin_end(10)
        icon.set_margin_start(10)
        icon.set_margin_top(10)

        if icon_url is not None:
            thread = threading.Thread(
                target=self.fetch_icon, args=(icon, icon_url), daemon=True
            )
            thread.start()

        return icon

    def fetch_icon(self, icon, icon_url):
        """
        Fetches the icon.

        :param icon: The icon object.
        :param icon_url: The icon url.
        """
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
        """
        Sets the icon.

        :param icon: The icon object.
        :param pixbuf: The pixbuf object.
        """
        if pixbuf is not None:
            icon.set_from_pixbuf(pixbuf)

        else:
            icon.set_from_icon_name("image-missing")

    def get_image(self, appimage_url, name):
        """
        Gets the image.

        :param appimage_url: The appimage url.
        :param name: The name of the appimage.
        :return: The image.
        """
        screenshot_url = appimage_url + "/" + name + "/screenshot.png"

        screenshot = Gtk.Image()
        screenshot.set_pixel_size(400)
        screenshot.set_from_icon_name("image-missing")

        thread = threading.Thread(
            target=self.fetch_image, args=(screenshot, screenshot_url), daemon=True
        )
        thread.start()

        return screenshot

    def fetch_image(self, screenshot, screenshot_url):
        """
        Fetches the image.

        :param screenshot: The screenshot object.
        :param screenshot_url: The screenshot url.
        """
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
        """
        Sets the image.

        :param screenshot: The screenshot object.
        :param pixbuf: The pixbuf object.
        """
        if pixbuf is not None:
            screenshot.set_from_pixbuf(pixbuf)
        else:
            screenshot.set_from_icon_name("image-missing")

    def on_download_clicked(self, button, download_url):
        """
        Handles the download click event.

        :param button: The download button object.
        :param download_url: The download url.
        """
        Gio.AppInfo.launch_default_for_uri(download_url, None)
