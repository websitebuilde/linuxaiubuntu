import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GObject, GLib
from concurrent.futures import ThreadPoolExecutor

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app, ai_client, system_ops):
        super().__init__(application=app, title="Ubuntu AI Assistant")
        self.ai_client = ai_client
        self.system_ops = system_ops
        self.executor = ThreadPoolExecutor(max_workers=1)

        # Main layout
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_content(content)

        # Header Bar
        header = Adw.HeaderBar()
        content.append(header)

        # Chat Area
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.chat_box.set_margin_top(10)
        self.chat_box.set_margin_bottom(10)
        self.chat_box.set_margin_start(10)
        self.chat_box.set_margin_end(10)
        self.scrolled.set_child(self.chat_box)
        content.append(self.scrolled)

        # Input Area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        input_box.set_margin_start(10)
        input_box.set_margin_end(10)
        input_box.set_margin_bottom(10)
        
        self.entry = Gtk.Entry()
        self.entry.set_hexpand(True)
        self.entry.set_placeholder_text("Ask me anything or tell me to do something...")
        self.entry.connect("activate", self.on_send_clicked)
        input_box.append(self.entry)

        send_btn = Gtk.Button(label="Send")
        send_btn.connect("clicked", self.on_send_clicked)
        input_box.append(send_btn)

        content.append(input_box)

    def add_message(self, text, is_user=False):
        """Adds a message bubble to the chat."""
        align = Gtk.Align.END if is_user else Gtk.Align.START
        style = "suggested-action" if is_user else "card"
        
        label = Gtk.Label(label=text, wrap=True, max_width_chars=50, xalign=0)
        label.set_selectable(True)
        
        # Wrap in a frame/box for styling
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(label)
        box.set_halign(align)
        box.add_css_class(style)
        box.set_margin_start(5)
        box.set_margin_end(5)
        box.set_margin_top(2)
        box.set_margin_bottom(2)
        
        # Add padding inside the bubble
        padding_box = Gtk.Box()
        padding_box.set_margin_top(8)
        padding_box.set_margin_bottom(8)
        padding_box.set_margin_start(12)
        padding_box.set_margin_end(12)
        padding_box.append(box)

        self.chat_box.append(padding_box)
        
        # Auto-scroll to bottom
        adj = self.scrolled.get_vadjustment()
        adj.set_value(adj.get_upper())

    def on_send_clicked(self, widget):
        text = self.entry.get_text()
        if not text:
            return
        
        self.add_message(text, is_user=True)
        self.entry.set_text("")
        
        # Process in background using thread pool
        self.executor.submit(self.process_input, text)

    def process_input(self, text):
        # Simple heuristic to detect command intent
        # In a real app, the LLM would classify the intent first.
        lower_text = text.lower()
        if "command" in lower_text or "run" in lower_text or "install" in lower_text or "update" in lower_text:
            response = self.ai_client.generate_command(text)
            GLib.idle_add(self.show_command_confirmation, response)
        elif "dark mode" in lower_text:
             # Direct action example
             GLib.idle_add(self.handle_dark_mode, text)
        else:
            response = self.ai_client.chat(text)
            GLib.idle_add(self.add_message, response, False)

    def show_command_confirmation(self, command):
        self.add_message(f"Proposed Command: {command}", False)
        
        # Create a button to run it
        btn = Gtk.Button(label="Run Command")
        btn.set_halign(Gtk.Align.START)
        btn.set_margin_start(20)
        btn.connect("clicked", lambda x: self.execute_command(command))
        self.chat_box.append(btn)

    def execute_command(self, command):
        # Run in background to avoid freezing UI
        self.executor.submit(self._execute_command_thread, command)

    def _execute_command_thread(self, command):
        output = self.system_ops.run_command(command)
        GLib.idle_add(self.add_message, f"Output:\n{output}", False)

    def handle_dark_mode(self, text):
        if "on" in text or "enable" in text:
            self.system_ops.set_dark_mode(True)
            self.add_message("Dark mode enabled.", False)
        elif "off" in text or "disable" in text:
            self.system_ops.set_dark_mode(False)
            self.add_message("Dark mode disabled.", False)
        else:
            self.add_message("I'm not sure if you want dark mode on or off.", False)
