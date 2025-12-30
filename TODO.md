# 📋 Project TODO & Notes

## ✅ Completed

- [x] Complete diffusion simulation engine (1D & 2D)
- [x] ST7789 display driver integration
- [x] Multi-threaded architecture (Flask, Display, Network)
- [x] Network monitoring with exponential backoff
- [x] IP address display with QR code generation
- [x] Modern gradient web interface
- [x] Real-time parameter updates
- [x] Systemd service configuration
- [x] Comprehensive documentation

## 📝 Notes for Deployment

### Before Copying to Raspberry Pi

1. **Make install.sh executable:**
   ```bash
   chmod +x install.sh
   ```

2. **GPIO Configuration:**
   - Verify your ST7789 display pins match the defaults
   - Default: DC=GPIO9, RST=GPIO25, CS=GPIO8
   - Edit `main.py` if your wiring is different

3. **SPI Must Be Enabled:**
   - Use `sudo raspi-config`
   - Interface Options → SPI → Enable
   - Reboot required

### Known Configuration Points

**Display Settings (main.py):**
```python
display_instance = ST7789.ST7789(
    height=240,
    width=240,
    rotation=0,      # Rotate if display is upside down
    port=0,          # SPI port
    cs=1,            # CS pin
    dc=9,            # DC pin (GPIO 9)
    backlight=None,  # Or GPIO pin number for dimming
    spi_speed_hz=80 * 1000 * 1000
)
```

**Network Timing (main.py):**
```python
IP_DISPLAY_DURATION = 10  # How long to show IP on boot
IP_REFRESH_INTERVAL = 30  # How often to refresh IP
```

**Web Port (main.py):**
```python
WEB_PORT = 5000  # Change if port conflict
```

## 🎨 Customization Ideas

### Color Schemes

**Current:** Cyan gradient (#22d3ee to #3b82f6)

**Alternative palettes:**
- **Warm:** `#f59e0b` to `#ef4444` (Orange to Red)
- **Cool:** `#06b6d4` to `#8b5cf6` (Cyan to Purple)
- **Green:** `#10b981` to `#059669` (Emerald gradient)

### Simulation Extensions

1. **Add 3D projections** (isometric view of 2D data)
2. **Time-series plotting** (show evolution over time)
3. **Custom initial conditions** (Gaussian, step function, etc.)
4. **Multi-species diffusion** (coupled equations)
5. **Reaction-diffusion** (e.g., Gray-Scott patterns)

### Display Enhancements

1. **FPS counter** (overlay in corner)
2. **Parameter overlay** (show current L, M, D on screen)
3. **Touch input** (if using resistive/capacitive overlay)
4. **Button controls** (GPIO buttons for mode switching)

### Web Interface

1. **Real-time plotting** (Chart.js visualization)
2. **Parameter presets** (save/load configurations)
3. **Screenshot capture** (download display as PNG)
4. **Animation controls** (pause/play/speed)
5. **Multiple theme support** (light/dark/custom)

## 🐛 Testing Checklist

### On Raspberry Pi

- [ ] Display shows IP address on boot
- [ ] QR code is scannable
- [ ] Web interface accessible
- [ ] 1D simulation renders correctly
- [ ] 2D simulation renders correctly
- [ ] Parameter changes apply instantly
- [ ] Network reconnection works
- [ ] Service auto-starts on reboot
- [ ] Logs are clean (no errors)

### Testing Commands

```bash
# Manual run test
python3 main.py

# Service test
sudo systemctl start diffusion.service
sudo systemctl status diffusion.service
sudo journalctl -u diffusion.service -f

# Reboot test
sudo reboot
# Wait and check display shows IP
```

## 📊 Performance Notes

- **Display refresh:** ~20 FPS target
- **SPI speed:** 80 MHz (adjust if flickering)
- **Simulation:** NumPy vectorized (very fast)
- **Web requests:** <100ms typical response
- **Memory:** ~50-100 MB typical usage

## 🔒 Security Notes

**For Production Use:**

1. **Add authentication** to web interface
2. **Use HTTPS** with self-signed cert
3. **Firewall rules** to limit access
4. **Change default port** from 5000
5. **Rate limiting** on API endpoints

**Example nginx config** (optional):
```nginx
server {
    listen 80;
    location / {
        proxy_pass http://127.0.0.1:5000;
        auth_basic "Diffusion Sim";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

## 📦 Backup Script

```bash
#!/bin/bash
# Save to: ~/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
tar -czf ~/diffusion-backup-$DATE.tar.gz ~/diffusion-pi/
echo "Backup created: ~/diffusion-backup-$DATE.tar.gz"
```

## 🔄 Update Workflow

1. Edit files on development machine
2. Test locally (if possible)
3. Stop service: `sudo systemctl stop diffusion.service`
4. Copy files: `scp -r diffusion-pi/ pi@<ip>:~/`
5. Start service: `sudo systemctl start diffusion.service`
6. Check logs: `sudo journalctl -u diffusion.service -f`

## 📞 Support Resources

- **Raspberry Pi Docs:** https://www.raspberrypi.com/documentation/
- **ST7789 Library:** https://github.com/pimoroni/st7789-python
- **Flask Docs:** https://flask.palletsprojects.com/
- **NumPy Docs:** https://numpy.org/doc/

---

**Last Updated:** 2025-12-30
