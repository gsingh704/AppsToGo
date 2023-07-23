import gi
import sys

from myapp import MyApp

if __name__ == "__main__":
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    app = MyApp()
    app.run(sys.argv)