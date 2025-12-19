import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from ui import MainWindow
from ai_client import AIClient
from system_ops import SystemOps

class UbuntuAIApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(application_id="com.example.UbuntuAI",
                         flags=0, **kwargs)
        self.ai_client = AIClient()
        self.system_ops = SystemOps()

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(self, self.ai_client, self.system_ops)
        win.present()

def main():
    app = UbuntuAIApp()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
