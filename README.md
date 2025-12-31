# ⚡ Circular Waveguide Simulator

**TM Mode Analysis on Raspberry Pi Zero 2 W with ST7789 Display**

Interactive electromagnetic waveguide simulator demonstrating Bessel functions, field distributions, and cutoff frequency analysis for circular waveguides operating in TM modes.

## 🎯 Features

- **Real-time Visualization**: Four different display modes
  - Field Distribution (E and H fields)
  - Bessel Functions (J₀, J₁)
  - Cutoff Analysis
  - Radial Field Profile
- **Web Interface**: Control all parameters via browser
- **Physical Accuracy**: Based on Bessel functions and Maxwell's equations
- **Responsive**: Updates display instantly

## 📋 Hardware Requirements

- **Raspberry Pi Zero 2 W** (or any RPi with GPIO)
- **ST7789 240x240 SPI Display**
- **Wiring**: SCLK→GPIO11, MOSI→GPIO10, CS→GPIO8, DC→GPIO24, RST→GPIO25

## 🚀 Installation

```bash
# Enable SPI
sudo raspi-config  # Interface Options → SPI → Enable

# Clone and install
git clone <your-repo>
cd waveguide-pi
pip3 install -r requirements.txt

# Run
python3 main.py
```

## 🎮 Usage

1. Display shows IP address at startup
2. Open browser: `http://<pi-ip>:5000`
3. Adjust parameters:
   - **Radius** (5-50 mm)
   - **Frequency** (1-50 GHz)
   - **εᵣ** (relative permittivity)
   - **μᵣ** (relative permeability)
4. Select visualization mode
5. Click "Apply to Display"

## 📐 Physics

### TM₀₁ Mode

Cutoff wave number: `kc = 2.405 / radius`

Cutoff frequency: `fc = kc × c / (2π√(εᵣμᵣ))`

Propagation constant: `β = √(k² - kc²)`

Wave propagates only when `f > fc`

## 🔧 Configuration

Edit `main.py` for custom GPIO pins or display settings.

## 📝 License

MIT License
