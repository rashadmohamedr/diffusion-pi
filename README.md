# 🎯 Embedded Diffusion Simulation System

A standalone embedded system for Raspberry Pi Zero 2 W that runs real-time diffusion simulations with live display output and web-based control.

## 📦 Hardware Requirements

- **Raspberry Pi Zero 2 W**
- **1.54" ST7789 SPI Display (240×240)**
  - SPI enabled
  - GPIO connections: DC, RST
  - Backlight: tied to 3.3V or optional GPIO control

## 🚀 Features

### ✨ Core Capabilities

- **1D & 2D Diffusion Simulations** - Real-time numerical solutions using analytical formulas
- **ST7789 Display Output** - Direct SPI rendering with beautiful visualizations
- **Web Interface** - Modern, responsive control panel accessible from any device
- **Headless Operation** - No HDMI, keyboard, or mouse required
- **Auto-Start on Boot** - Systemd service with automatic recovery
- **Network Aware** - Displays IP address and QR code for easy access

### 🎨 Display Behavior

**On Boot:**
1. Shows device IP address (large, readable font)
2. Displays QR code pointing to `http://<ip>:5000`
3. Duration: 10 seconds (configurable)
4. Refreshes IP display every 30 seconds

**During Operation:**
- **1D Mode:** Animated line plot showing concentration profile
- **2D Mode:** Color-mapped heatmap with gradient visualization
- **Network Lost:** Shows "Reconnecting..." with retry counter

### 🌐 Web Interface

Access at: `http://<device-ip>:5000`

**Controls:**
- Switch between 1D/2D simulation modes
- Adjust domain length (L)
- Modify mass/amplitude (M)
- Change diffusion coefficient (D)
- All changes apply instantly to the display

**Design:**
- Modern gradient UI with dark theme
- Smooth animations and transitions
- Real-time parameter feedback
- Responsive mobile-friendly layout

## 📐 Physics

### 1D Diffusion
```
u(x,t) = (2M/L) × sin(πx/L) × exp(-π²Dt/L²)
```

### 2D Diffusion
```
u(x,y,t) = (2M/L) × sin(πx/L) × sin(πy/L) × exp(-π²Dt/L²)
```

**Parameters:**
- `L` - Domain length (spatial scale)
- `M` - Initial amplitude/mass
- `D` - Diffusion coefficient (spreading rate)
- `t` - Time (automatically animated)

## 🛠️ Installation

### 1️⃣ System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python dependencies
sudo apt install -y python3-pip python3-pil python3-numpy

# Enable SPI
sudo raspi-config
# → Interface Options → SPI → Enable
```

### 2️⃣ Project Installation

```bash
# Copy project to Raspberry Pi
scp -r diffusion-pi/ pi@<raspberry-pi-ip>:~/

# SSH into Raspberry Pi
ssh pi@<raspberry-pi-ip>

# Navigate to project
cd ~/diffusion-pi

# Install Python packages
pip3 install -r requirements.txt
```

### 3️⃣ Configure ST7789 Display

**Default GPIO Pins:**
- **MOSI:** GPIO 10 (Pin 19)
- **SCLK:** GPIO 11 (Pin 23)
- **CS:** GPIO 8 (Pin 24) or GPIO 7 (Pin 26)
- **DC:** GPIO 9 (Pin 21)
- **RST:** GPIO 25 (Pin 22)
- **Backlight:** 3.3V (Pin 1) or GPIO

If your wiring differs, edit `main.py`:

```python
display_instance = ST7789.ST7789(
    height=240,
    width=240,
    rotation=0,
    port=0,
    cs=1,        # Change CS pin if needed
    dc=9,        # Change DC pin if needed
    backlight=None,
    spi_speed_hz=80 * 1000 * 1000
)
```

### 4️⃣ Test Run

```bash
# Manual test (should show display output)
python3 main.py

# Press Ctrl+C to stop
```

### 5️⃣ Enable Auto-Start

```bash
# Copy service file
sudo cp diffusion.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable diffusion.service

# Start service now
sudo systemctl start diffusion.service

# Check status
sudo systemctl status diffusion.service
```

## 📊 Usage

### Accessing Web Interface

**Method 1: Scan QR Code**
1. Power on Raspberry Pi
2. Wait for display to show QR code
3. Scan with phone camera
4. Opens web interface automatically

**Method 2: Direct URL**
1. Check IP address on display
2. Open browser on any device (same network)
3. Navigate to `http://<ip>:5000`

### Controlling Simulation

1. **Select Mode:** Click "1D Diffusion" or "2D Diffusion"
2. **Adjust Parameters:** Use sliders for L, M, D
3. **Apply Changes:** Click "Apply Changes" button
4. **Watch Display:** ST7789 shows updated simulation in real-time

### Monitoring

```bash
# View logs
sudo journalctl -u diffusion.service -f

# Restart service
sudo systemctl restart diffusion.service

# Stop service
sudo systemctl stop diffusion.service
```

## 🔧 Troubleshooting

### Display Not Working

```bash
# Check SPI is enabled
lsmod | grep spi

# Should show: spi_bcm2835

# Test GPIO access
gpio readall

# Verify ST7789 library
python3 -c "import ST7789; print('OK')"
```

### Web Server Not Accessible

```bash
# Check if Flask is running
sudo netstat -tulpn | grep 5000

# Check firewall (if enabled)
sudo ufw allow 5000

# Verify network connection
hostname -I
```

### Service Won't Start

```bash
# Check service logs
sudo journalctl -u diffusion.service -n 50

# Check permissions
ls -la ~/diffusion-pi/

# Test manual run
cd ~/diffusion-pi
python3 main.py
```

### Display Shows Wrong IP

```bash
# Check network interfaces
ip addr show

# Verify routing
ip route show default
```

## 📁 Project Structure

```
diffusion-pi/
├── main.py               # Main application
│   ├── Diffusion engine (1D/2D)
│   ├── ST7789 display driver
│   ├── Network monitor
│   ├── QR code generator
│   └── Flask web server
│
├── templates/
│   └── index.html        # Web UI (modern gradient design)
│
├── requirements.txt      # Python dependencies
├── diffusion.service     # Systemd service file
└── README.md            # This file
```

## 🧵 Architecture

### Multi-Threading

- **Thread 1:** Flask web server (`0.0.0.0:5000`)
- **Thread 2:** Display update loop (~20 FPS)
- **Thread 3:** Network monitor (30s refresh)
- **Main Thread:** Coordination & cleanup

### Thread Safety

- Shared state protected by `threading.Lock()`
- SPI access serialized (single display instance)
- Graceful shutdown on SIGINT/SIGTERM

## 🎛️ Configuration

Edit `main.py` constants:

```python
# Display settings
DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240

# Network settings
WEB_PORT = 5000
IP_DISPLAY_DURATION = 10      # seconds
IP_REFRESH_INTERVAL = 30      # seconds

# Retry backoff
NETWORK_RETRY_BACKOFF = [1, 2, 5, 10, 30, 60]

# Default simulation parameters
DEFAULT_PARAMS = {
    'mode': '2D',
    'L': 1.0,
    'M': 1.0,
    'D': 0.1,
}
```

## 🔬 Customization

### Change Color Scheme

Edit rendering functions in `main.py`:

```python
# 1D plot color
draw.line(points, fill=(34, 211, 238), width=2)  # Cyan

# 2D heatmap gradient
r = int(val * 34 / 255)   # Red component
g = int(val * 211 / 255)  # Green component
b = int(val * 238 / 255)  # Blue component
```

### Add New Simulation Modes

1. Implement new simulation function
2. Add rendering method
3. Update web UI options
4. Modify display thread logic

## 📚 Dependencies

- **numpy** - Numerical computations
- **Pillow** - Image rendering
- **st7789** - SPI display driver (libgpiod-based)
- **Flask** - Web server
- **qrcode** - QR code generation

## 🐛 Known Limitations

- **Single User:** Web interface doesn't support multiple simultaneous users modifying parameters
- **No Persistence:** Parameter changes don't persist across reboots
- **Fixed Resolution:** Display output fixed at 240×240
- **SPI Bandwidth:** ~20 FPS maximum for smooth animation

## 📝 Future Enhancements

- [ ] Save/load parameter presets
- [ ] Historical plot/data logging
- [ ] Custom initial conditions
- [ ] Screenshot capture via web
- [ ] Performance profiling display
- [ ] Multi-language support

## 📄 License

This project is provided as-is for educational purposes.

## 🙏 Credits

- **Physics:** Classical diffusion equations
- **Hardware:** Raspberry Pi Foundation
- **Display:** Pimoroni ST7789 library
- **Design:** Modern gradient web aesthetics

---

**Built with ❤️ for embedded systems education**

*Last updated: 2025*
