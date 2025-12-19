import subprocess

class SystemOps:
    @staticmethod
    def run_command(command):
        """
        Executes a shell command and returns the output.
        """
        try:
            # Safety check: simplistic, but prevents empty commands
            if not command or not command.strip():
                return "Empty command."

            # Using shell=True to allow complex commands (pipes, &&, etc.)
            # In a production app, this would need strict validation.
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return f"Success:\n{result.stdout}"
            else:
                return f"Error ({result.returncode}):\n{result.stderr}"
        except Exception as e:
            return f"Execution failed: {e}"

    @staticmethod
    def set_dark_mode(enable=True):
        """
        Sets the GNOME color scheme.
        """
        scheme = 'prefer-dark' if enable else 'default'
        cmd = f"gsettings set org.gnome.desktop.interface color-scheme '{scheme}'"
        return SystemOps.run_command(cmd)
