# Custom Ubuntu ISO Build Guide using Cubic

This guide provides step-by-step instructions for building a custom Ubuntu 22.04 LTS ISO with the AI System Assistant pre-installed and configured.

## Prerequisites

### Host System Requirements
- Ubuntu 20.04 LTS or later (for running Cubic)
- Minimum 20GB free disk space
- 4GB RAM minimum (8GB recommended)
- Internet connection (for downloading base ISO and Ollama)

### Required Downloads
1. **Ubuntu 22.04 LTS Desktop ISO**
   ```bash
   wget https://releases.ubuntu.com/22.04/ubuntu-22.04.3-desktop-amd64.iso
   ```

2. **Cubic (Custom Ubuntu ISO Creator)**
   ```bash
   sudo apt-add-repository ppa:cubic-wizard/release
   sudo apt update
   sudo apt install cubic
   ```

---

## Step 1: Create Cubic Project

1. **Launch Cubic**
   ```bash
   cubic
   ```

2. **Select Project Directory**
   - Click "Select" and choose or create a directory for your project
   - Example: `/home/user/cubic-projects/ai-ubuntu`

3. **Select Source ISO**
   - Click "Select" next to "Original ISO"
   - Choose the downloaded Ubuntu 22.04 ISO

4. **Configure Custom ISO Details**
   - **Custom ISO Filename**: `ai-ubuntu-22.04-amd64.iso`
   - **Volume ID**: `AI-Ubuntu-22.04`
   - **Version Number**: `1.0`
   - **Description**: `Ubuntu 22.04 with AI System Assistant`

5. Click **Next** to extract the ISO and enter the chroot environment.

---

## Step 2: Install Ollama in Chroot

Once in the Cubic terminal (chroot environment), execute:

```bash
# Update package lists
apt update && apt upgrade -y

# Install required packages
apt install -y curl wget python3 python3-pip git

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify Ollama installation
ollama --version
```

---

## Step 3: Pre-pull the LLM Model

The llama3 model must be pulled during ISO build, not at runtime.

```bash
# Start Ollama service temporarily
ollama serve &
sleep 5

# Pull the llama3 model (this will take several minutes, ~4.7GB)
ollama pull llama3

# Verify model is available
ollama list

# Stop Ollama service
pkill ollama
```

**Note**: The model will be stored in `/usr/share/ollama/.ollama/models/` and included in the ISO.

---

## Step 4: Install AI System Assistant

### Option A: Install from .deb Package (Recommended)

Copy the pre-built .deb package into the chroot:

```bash
# From OUTSIDE the chroot (in another terminal), copy the package:
# sudo cp /path/to/ai-system-assistant_1.0.0_amd64.deb /path/to/cubic/project/custom-root/tmp/

# Inside the chroot:
dpkg -i /tmp/ai-system-assistant_1.0.0_amd64.deb
apt-get install -f -y  # Fix any dependencies
```

### Option B: Install from Source

```bash
# Create installation directory
mkdir -p /opt/ai-system-assistant
cd /opt/ai-system-assistant

# Copy source files (you'll need to copy these into the chroot first)
# From outside chroot: sudo cp -r /path/to/ai-system-assistant/* /path/to/cubic/project/custom-root/opt/ai-system-assistant/

# Install Python dependencies
pip3 install pydantic

# Create wrapper script
mkdir -p /opt/ai-system-assistant/bin
cat > /opt/ai-system-assistant/bin/ai-assistant << 'EOF'
#!/bin/bash
cd /opt/ai-system-assistant
exec /usr/bin/python3 -m src.cli "$@"
EOF
chmod +x /opt/ai-system-assistant/bin/ai-assistant

# Create global symlink
ln -sf /opt/ai-system-assistant/bin/ai-assistant /usr/local/bin/ai-assistant

# Create log file
touch /var/log/ai-assistant.log
chmod 640 /var/log/ai-assistant.log
```

---

## Step 5: Configure Systemd Services

```bash
# Copy systemd service file
cp /opt/ai-system-assistant/systemd/ai-assistant.service /etc/systemd/system/

# Create Ollama systemd service
cat > /etc/systemd/system/ollama.service << 'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=root
Group=root
Restart=always
RestartSec=3
Environment="HOME=/usr/share/ollama"

[Install]
WantedBy=multi-user.target
EOF

# Enable services to start on boot
systemctl enable ollama.service
systemctl enable ai-assistant.service
```

---

## Step 6: Create Desktop Integration (Optional)

Create a desktop shortcut for the AI Assistant:

```bash
cat > /usr/share/applications/ai-assistant.desktop << 'EOF'
[Desktop Entry]
Name=AI System Assistant
Comment=Local AI for system management
Exec=gnome-terminal -- ai-assistant
Icon=utilities-terminal
Terminal=false
Type=Application
Categories=System;Utility;
Keywords=ai;assistant;system;
EOF
```

---

## Step 7: Configure Auto-start Script

Create a first-boot configuration script:

```bash
cat > /etc/profile.d/ai-assistant-welcome.sh << 'EOF'
#!/bin/bash
# Show welcome message on first login

if [ ! -f "$HOME/.ai-assistant-welcomed" ]; then
    echo ""
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║     AI System Assistant is ready!                     ║"
    echo "║                                                       ║"
    echo "║     Type 'ai-assistant' to start                      ║"
    echo "║     or use: ai-assistant \"your command\"               ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo ""
    touch "$HOME/.ai-assistant-welcomed"
fi
EOF
chmod +x /etc/profile.d/ai-assistant-welcome.sh
```

---

## Step 8: Clean Up Chroot

Before exiting the chroot, clean up to reduce ISO size:

```bash
# Clear apt cache
apt clean
apt autoclean
apt autoremove -y

# Clear temp files
rm -rf /tmp/*
rm -rf /var/tmp/*

# Clear bash history
history -c
> ~/.bash_history
```

---

## Step 9: Finalize ISO in Cubic

1. Click **Next** in Cubic to exit the chroot environment

2. **Boot Configuration** (optional)
   - Modify the boot menu if desired
   - Default settings work fine

3. **Compression** Tab
   - Select compression level (default: gzip)
   - Higher compression = smaller ISO but slower build

4. **Generate ISO**
   - Click **Generate** to build the ISO
   - This may take 15-30 minutes depending on your system

5. **Output Location**
   - The ISO will be saved to your project directory
   - Example: `/home/user/cubic-projects/ai-ubuntu/ai-ubuntu-22.04-amd64.iso`

---

## Step 10: Test the ISO

### Using VirtualBox

```bash
# Create a new VM
VBoxManage createvm --name "AI-Ubuntu-Test" --ostype "Ubuntu_64" --register
VBoxManage modifyvm "AI-Ubuntu-Test" --memory 4096 --cpus 2 --vram 128
VBoxManage createhd --filename "AI-Ubuntu-Test.vdi" --size 40000
VBoxManage storagectl "AI-Ubuntu-Test" --name "SATA" --add sata
VBoxManage storageattach "AI-Ubuntu-Test" --storagectl "SATA" --port 0 --device 0 --type hdd --medium "AI-Ubuntu-Test.vdi"
VBoxManage storageattach "AI-Ubuntu-Test" --storagectl "SATA" --port 1 --device 0 --type dvddrive --medium "/path/to/ai-ubuntu-22.04-amd64.iso"

# Start the VM
VBoxManage startvm "AI-Ubuntu-Test"
```

### Using QEMU

```bash
# Create disk image
qemu-img create -f qcow2 ai-ubuntu-test.qcow2 40G

# Run the ISO
qemu-system-x86_64 \
    -enable-kvm \
    -m 4096 \
    -smp 2 \
    -cdrom /path/to/ai-ubuntu-22.04-amd64.iso \
    -drive file=ai-ubuntu-test.qcow2,format=qcow2 \
    -boot d
```

---

## Verification After Installation

After booting the installed system, verify everything works:

```bash
# Check Ollama is running
systemctl status ollama

# Check AI Assistant service
systemctl status ai-assistant

# Verify llama3 model is available
ollama list

# Test AI Assistant
ai-assistant "list running processes"
ai-assistant "start firefox"
ai-assistant --health
```

---

## Troubleshooting

### Ollama Not Starting
```bash
# Check logs
journalctl -u ollama -f

# Manually start
sudo ollama serve
```

### Model Not Found
```bash
# Re-pull the model
ollama pull llama3
```

### AI Assistant Command Not Found
```bash
# Check symlink
ls -la /usr/local/bin/ai-assistant

# Recreate if needed
sudo ln -sf /opt/ai-system-assistant/bin/ai-assistant /usr/local/bin/ai-assistant
```

### Permission Denied on Log File
```bash
sudo touch /var/log/ai-assistant.log
sudo chmod 640 /var/log/ai-assistant.log
```

---

## ISO Specifications

| Property | Value |
|----------|-------|
| Base ISO | Ubuntu 22.04.3 LTS Desktop |
| Architecture | amd64 (x86_64) |
| Expected Size | ~7-8 GB (with llama3 model) |
| Ollama Version | Latest |
| LLM Model | llama3 (4.7GB) |
| Python Version | 3.10+ |

---

## File Manifest

The custom ISO includes:

```
/opt/ai-system-assistant/
├── bin/
│   └── ai-assistant
├── src/
│   ├── __init__.py
│   ├── ai.py
│   ├── cli.py
│   ├── commands.py
│   ├── config.py
│   ├── executor.py
│   ├── main.py
│   └── policy.py
├── systemd/
│   └── ai-assistant.service
├── requirements.txt
└── README.md

/usr/local/bin/ai-assistant -> /opt/ai-system-assistant/bin/ai-assistant
/etc/systemd/system/ai-assistant.service
/etc/systemd/system/ollama.service
/var/log/ai-assistant.log
/usr/share/ollama/.ollama/models/ (llama3 model data)
```
