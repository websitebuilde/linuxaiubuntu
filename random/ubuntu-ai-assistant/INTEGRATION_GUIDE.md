# Ubuntu AI Assistant Integration Guide

This guide details how to set up, run, and integrate the Ubuntu AI Assistant into your Ubuntu 25 desktop environment.

## 1. System Requirements

The assistant relies on GTK4 and LibAdwaita, which interact with Python via PyGObject. You must install the system-level dependencies first.

Open a terminal and run:

```bash
sudo apt update
sudo apt install -y python3-venv python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 libcairo2-dev
```

*Note: For AI features, you must have [Ollama](https://ollama.com/) installed and running locally with the `llama3` model (or configure the code to use another model).*

## 2. Python Environment Setup

It is recommended to use a virtual environment. **Crucially**, you must enable access to system site packages so the environment can find the apt-installed `gi` module.

```bash
cd /path/to/ubuntu-ai-assistant

# Create venv with system site packages access
python3 -m venv venv --system-site-packages

# Activate the environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

## 3. Running the Assistant

To start the application:

```bash
# Ensure venv is activated
source venv/bin/activate
python3 main.py
```

## 4. Desktop Integration

To make the assistant appear in your application grid and dock, create a `.desktop` entry.

1.  **Create the desktop file**:

    Open `~/.local/share/applications/ubuntu-ai.desktop` in a text editor (create the directory if it doesn't exist):

    ```bash
    mkdir -p ~/.local/share/applications
    nano ~/.local/share/applications/ubuntu-ai.desktop
    ```

2.  **Paste the following content**:

    *Make sure to replace `/path/to/ubuntu-ai-assistant` with the actual path to your project folder.*

    ```ini
    [Desktop Entry]
    Type=Application
    Name=Ubuntu AI Assistant
    Comment=AI-powered system assistant
    # Point Exec to the python in your venv and then the main script
    Exec=/path/to/ubuntu-ai-assistant/venv/bin/python3 /path/to/ubuntu-ai-assistant/main.py
    # Working directory is important for relative paths (if any)
    Path=/path/to/ubuntu-ai-assistant/
    Icon=utilities-terminal
    Terminal=false
    Categories=Utility;GTK;
    StartupNotify=true
    ```

3.  **Update the database** (usually automatic, but good to ensure):

    ```bash
    update-desktop-database ~/.local/share/applications
    ```

Now you should be able to search for "Ubuntu AI Assistant" in the Activities overview.

## 5. Troubleshooting

-   **"ModuleNotFoundError: No module named 'gi'"**: Ensure you created the venv with `--system-site-packages`.
-   **UI freezes on command**: Ensure you are running the latest version of `ui.py` which includes threading fixes.
-   **Connection Error**: Ensure `ollama serve` is running in a background terminal.
