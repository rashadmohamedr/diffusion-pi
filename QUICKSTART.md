# 🚀 Quick Start Guide

## On Raspberry Pi

### 1. Copy Project
```bash
# From your computer (where you have this folder)
scp -r diffusion-pi/ pi@<raspberry-pi-ip>:~/
```

### 2. SSH to Pi
```bash
ssh pi@<raspberry-pi-ip>
cd ~/diffusion-pi
```

### 3. Make install script executable
```bash
chmod +x install.sh
```

### 4. Run installer
```bash
./install.sh
```

### 5. Test
```bash
python3 main.py
```

### 6. Enable auto-start
```bash
sudo cp diffusion.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable diffusion.service
sudo systemctl start diffusion.service
```

## GPIO Wiring (ST7789)

| Display Pin | GPIO Pin | Physical Pin |
|-------------|----------|--------------|
| VCC         | 3.3V     | Pin 1        |
| GND         | GND      | Pin 6        |
| SCL (SCLK)  | GPIO 11  | Pin 23       |
| SDA (MOSI)  | GPIO 10  | Pin 19       |
| RES (RST)   | GPIO 25  | Pin 22       |
| DC          | GPIO 9   | Pin 21       |
| CS          | GPIO 8   | Pin 24       |
| BL          | 3.3V     | Pin 1        |

## Web Access

1. Check IP on display (shows for 10 seconds on boot)
2. Open browser: `http://<ip>:5000`

## Common Commands

```bash
# View logs
sudo journalctl -u diffusion.service -f

# Restart service
sudo systemctl restart diffusion.service

# Stop service
sudo systemctl stop diffusion.service

# Check status
sudo systemctl status diffusion.service
```

## Troubleshooting

**Display not working?**
```bash
# Enable SPI
sudo raspi-config
# → Interface Options → SPI → Enable → Reboot
```

**Can't access web?**
```bash
# Check if service is running
sudo systemctl status diffusion.service

# Check IP address
hostname -I
```

**Service won't start?**
```bash
# Check logs
sudo journalctl -u diffusion.service -n 50
```

---

**For full documentation, see [README.md](README.md)**
