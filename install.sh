#!/bin/bash
#
# Installation script for Diffusion Simulation System
# Run this on your Raspberry Pi Zero 2 W
#

set -e

echo "=========================================="
echo "Diffusion Simulation - Setup Script"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "⚠️  Warning: This doesn't look like a Raspberry Pi"
    echo "   Continuing anyway..."
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt install -y python3-pip python3-pil python3-numpy git

# Check SPI
echo "🔌 Checking SPI configuration..."
if lsmod | grep -q spi_bcm2835; then
    echo "✅ SPI is enabled"
else
    echo "❌ SPI is NOT enabled"
    echo ""
    echo "Please enable SPI:"
    echo "  1. Run: sudo raspi-config"
    echo "  2. Go to: Interface Options → SPI"
    echo "  3. Select: Yes"
    echo "  4. Reboot and run this script again"
    exit 1
fi

# Install Python dependencies
echo "🐍 Installing Python packages..."
pip3 install -r requirements.txt

# Test imports
echo "🧪 Testing Python imports..."
python3 -c "import numpy; print('  ✓ numpy')"
python3 -c "from PIL import Image; print('  ✓ Pillow')"
python3 -c "import flask; print('  ✓ Flask')"
python3 -c "import qrcode; print('  ✓ qrcode')"

# Optional: Test ST7789 (may fail if display not connected)
if python3 -c "import ST7789" 2>/dev/null; then
    echo "  ✓ ST7789"
else
    echo "  ⚠️  ST7789 not available (install will continue)"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Test the application:"
echo "     python3 main.py"
echo ""
echo "  2. Install systemd service (auto-start on boot):"
echo "     sudo cp diffusion.service /etc/systemd/system/"
echo "     sudo systemctl daemon-reload"
echo "     sudo systemctl enable diffusion.service"
echo "     sudo systemctl start diffusion.service"
echo ""
echo "  3. Check service status:"
echo "     sudo systemctl status diffusion.service"
echo ""
echo "  4. View logs:"
echo "     sudo journalctl -u diffusion.service -f"
echo ""
echo "🎉 Happy simulating!"
