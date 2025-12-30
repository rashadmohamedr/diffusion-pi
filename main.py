#!/usr/bin/env python3
"""
Embedded Diffusion Simulation System
Raspberry Pi Zero 2 W + ST7789 Display
"""

import os
import sys
import time
import threading
import socket
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, jsonify

# Import ST7789 display driver
try:
    import ST7789
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False
    print("WARNING: ST7789 not available. Running in simulation mode.")

# ============================================================================
# Configuration
# ============================================================================

DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 240
WEB_PORT = 5000
IP_DISPLAY_DURATION = 10  # seconds

# Simulation defaults
DEFAULT_PARAMS = {
    'mode': '2D',  # '1D' or '2D'
    'L': 1.0,      # Domain length
    'M': 1.0,      # Mass/Amplitude
    'D': 0.1,      # Diffusion coefficient
    'running': True
}

# ============================================================================
# Global State (Thread-Safe)
# ============================================================================

state_lock = threading.Lock()
simulation_state = DEFAULT_PARAMS.copy()
display_instance = None
shutdown_event = threading.Event()

# ============================================================================
# Network Utilities
# ============================================================================

def get_ip_address():
    """Get local IP address using UDP socket method"""
    try:
        # Create a socket to detect the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # Connect to a public DNS server (doesn't actually send data)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

# ============================================================================
# Diffusion Simulation Engine
# ============================================================================

def simulate_1d(L, M, D, t, num_points=240):
    """
    1D Diffusion: u(x,t) = (2M/L) * sin(πx/L) * exp(-π²Dt/L²)
    """
    x = np.linspace(0, L, num_points)
    u = (2 * M / L) * np.sin(np.pi * x / L) * np.exp(-np.pi**2 * D * t / L**2)
    return x, u

def simulate_2d(L, M, D, t, resolution=240):
    """
    2D Diffusion: u(x,y,t) = (2M/L) * sin(πx/L) * sin(πy/L) * exp(-π²Dt/L²)
    """
    x = np.linspace(0, L, resolution)
    y = np.linspace(0, L, resolution)
    X, Y = np.meshgrid(x, y)
    
    u = (2 * M / L) * np.sin(np.pi * X / L) * np.sin(np.pi * Y / L) * \
        np.exp(-np.pi**2 * D * t / L**2)
    
    return u

# ============================================================================
# Display Rendering
# ============================================================================

def create_ip_display(ip_address):
    """Create image showing IP address"""
    img = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(15, 23, 42))  # Dark slate
    draw = ImageDraw.Draw(img)
    
    try:
        # Try to load a nice font
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Title
    draw.text((120, 60), "Diffusion Sim", fill=(148, 163, 184), anchor="mm", font=font_medium)
    
    # IP Address
    if ip_address:
        draw.text((120, 120), ip_address, fill=(34, 211, 238), anchor="mm", font=font_large)
        draw.text((120, 160), f"http://{ip_address}:{WEB_PORT}", fill=(148, 163, 184), anchor="mm", font=font_small)
    else:
        draw.text((120, 120), "No Network", fill=(239, 68, 68), anchor="mm", font=font_medium)
    
    return img

def render_1d_simulation(x, u):
    """Render 1D simulation as a line plot"""
    img = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    # Normalize u to display range
    u_min, u_max = u.min(), u.max()
    if u_max - u_min > 1e-10:
        u_norm = (u - u_min) / (u_max - u_min)
    else:
        u_norm = np.zeros_like(u)
    
    # Scale to display coordinates
    margin = 20
    plot_height = DISPLAY_HEIGHT - 2 * margin
    
    points = []
    for i, val in enumerate(u_norm):
        x_pos = margin + i * (DISPLAY_WIDTH - 2 * margin) / len(u_norm)
        y_pos = DISPLAY_HEIGHT - margin - val * plot_height
        points.append((x_pos, y_pos))
    
    # Draw line plot
    if len(points) > 1:
        draw.line(points, fill=(34, 211, 238), width=2)
    
    # Draw axes
    draw.line([(margin, DISPLAY_HEIGHT - margin), 
               (DISPLAY_WIDTH - margin, DISPLAY_HEIGHT - margin)], 
              fill=(148, 163, 184), width=1)
    draw.line([(margin, margin), (margin, DISPLAY_HEIGHT - margin)], 
              fill=(148, 163, 184), width=1)
    
    return img

def render_2d_simulation(u):
    """Render 2D simulation as a heatmap"""
    # Normalize to 0-255 range
    u_min, u_max = u.min(), u.max()
    if u_max - u_min > 1e-10:
        u_norm = ((u - u_min) / (u_max - u_min) * 255).astype(np.uint8)
    else:
        u_norm = np.zeros_like(u, dtype=np.uint8)
    
    # Create grayscale image
    img = Image.fromarray(u_norm, mode='L')
    
    # Convert to RGB with color map (cyan gradient)
    img_rgb = Image.new('RGB', img.size)
    pixels = img.load()
    pixels_rgb = img_rgb.load()
    
    for i in range(img.size[0]):
        for j in range(img.size[1]):
            val = pixels[i, j]
            # Gradient from dark blue to cyan
            r = int(val * 34 / 255)
            g = int(val * 211 / 255)
            b = int(val * 238 / 255 + (255 - val) * 15 / 255)
            pixels_rgb[i, j] = (r, g, b)
    
    # Resize to display size
    img_rgb = img_rgb.resize((DISPLAY_WIDTH, DISPLAY_HEIGHT))
    
    return img_rgb

# ============================================================================
# Display Thread
# ============================================================================

def display_thread():
    """Main display loop"""
    global display_instance
    
    # Initialize display
    if DISPLAY_AVAILABLE:
        display_instance = ST7789.ST7789(
            height=DISPLAY_HEIGHT,
            width=DISPLAY_WIDTH,
            rotation=0,
            port=0,
            cs=ST7789.BG_SPI_CS_FRONT,  # GPIO8 (CE0)
            dc=24,                       # DC pin (GPIO24)
            backlight=18,                # GPIO18 for PWM control
            spi_speed_hz=80 * 1000 * 1000
        )
    
    # Get IP address once at startup
    current_ip = get_ip_address()
    print(f"IP Address: {current_ip if current_ip else 'Not available'}")
    
    # Show IP for configured duration
    ip_show_until = time.time() + IP_DISPLAY_DURATION
    t_start = time.time()
    
    while not shutdown_event.is_set():
        current_time = time.time()
        
        # Show IP address at startup
        if current_time < ip_show_until:
            img = create_ip_display(current_ip)
        else:
            # Run simulation
            with state_lock:
                params = simulation_state.copy()
            
            t_sim = (current_time - t_start) % 10  # Loop every 10 seconds
            
            if params['mode'] == '1D':
                x, u = simulate_1d(params['L'], params['M'], params['D'], t_sim)
                img = render_1d_simulation(x, u)
            else:  # 2D
                u = simulate_2d(params['L'], params['M'], params['D'], t_sim)
                img = render_2d_simulation(u)
        
        # Display image
        if DISPLAY_AVAILABLE and display_instance:
            display_instance.display(img)
        
        time.sleep(0.05)  # ~20 FPS

# ============================================================================
# Flask Web Interface
# ============================================================================

app = Flask(__name__)

@app.route('/')
def index():
    """Serve main web interface"""
    with state_lock:
        params = simulation_state.copy()
    return render_template('index.html', params=params, ip=get_ip_address())

@app.route('/api/params', methods=['GET', 'POST'])
def api_params():
    """Get or update simulation parameters"""
    global simulation_state
    
    if request.method == 'POST':
        data = request.json
        with state_lock:
            if 'mode' in data:
                simulation_state['mode'] = data['mode']
            if 'L' in data:
                simulation_state['L'] = float(data['L'])
            if 'M' in data:
                simulation_state['M'] = float(data['M'])
            if 'D' in data:
                simulation_state['D'] = float(data['D'])
        return jsonify({'status': 'ok', 'params': simulation_state})
    else:
        with state_lock:
            params = simulation_state.copy()
        return jsonify(params)

def run_flask():
    """Run Flask in a separate thread"""
    app.run(host='0.0.0.0', port=WEB_PORT, debug=False, use_reloader=False)

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main application entry point"""
    print("=" * 60)
    print("Embedded Diffusion Simulation System")
    print("=" * 60)
    
    # Start display thread
    display_thread_obj = threading.Thread(target=display_thread, daemon=True)
    display_thread_obj.start()
    print("✓ Display thread started")
    
    # Start Flask web server
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✓ Web server started on port", WEB_PORT)
    
    print("\nSystem ready!")
    print("Access web interface at: http://<device-ip>:5000")
    print("\nPress Ctrl+C to exit")
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        shutdown_event.set()
        time.sleep(1)
        print("Goodbye!")

if __name__ == '__main__':
    main()
