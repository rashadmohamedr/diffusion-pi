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

# Import ST7789 display driver (try lowercase first, then uppercase for compatibility)
try:
    import st7789 as ST7789
    DISPLAY_AVAILABLE = True
except ImportError:
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
    """Render 1D simulation as a line plot with axis labels"""
    img = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    # Try to load font for axis labels
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except:
        font_small = ImageFont.load_default()
        font_title = ImageFont.load_default()
    
    # Define margins to make room for labels
    margin_left = 38
    margin_bottom = 32
    margin_top = 28
    margin_right = 15
    
    plot_width = DISPLAY_WIDTH - margin_left - margin_right
    plot_height = DISPLAY_HEIGHT - margin_top - margin_bottom
    
    # Get actual max value for Y-axis
    u_max = u.max() if u.max() > 1e-10 else 1.0
    u_norm = u / u_max if u_max > 1e-10 else np.zeros_like(u)
    
    # Scale to display coordinates
    points = []
    for i, val in enumerate(u_norm):
        x_pos = margin_left + i * plot_width / len(u_norm)
        y_pos = DISPLAY_HEIGHT - margin_bottom - val * plot_height
        points.append((x_pos, y_pos))
    
    # Fill area under curve
    if len(points) > 1:
        fill_points = [(margin_left, DISPLAY_HEIGHT - margin_bottom)]
        fill_points.extend(points)
        fill_points.append((margin_left + plot_width, DISPLAY_HEIGHT - margin_bottom))
        draw.polygon(fill_points, fill=(34, 211, 238, 50))
    
    # Draw line plot
    if len(points) > 1:
        draw.line(points, fill=(34, 211, 238), width=2)
    
    # Draw axes
    axis_color = (148, 163, 184)
    # X-axis
    draw.line([(margin_left, DISPLAY_HEIGHT - margin_bottom), 
               (DISPLAY_WIDTH - margin_right, DISPLAY_HEIGHT - margin_bottom)], 
              fill=axis_color, width=1)
    # Y-axis
    draw.line([(margin_left, margin_top), (margin_left, DISPLAY_HEIGHT - margin_bottom)], 
              fill=axis_color, width=1)
    
    # X-axis tick marks and labels
    L = x[-1] if len(x) > 0 else 1.0
    num_x_ticks = 5
    for i in range(num_x_ticks + 1):
        x_val = L * i / num_x_ticks
        x_pos = margin_left + plot_width * i / num_x_ticks
        # Tick mark
        draw.line([(x_pos, DISPLAY_HEIGHT - margin_bottom), 
                   (x_pos, DISPLAY_HEIGHT - margin_bottom + 3)], fill=axis_color, width=1)
        # Label - format based on value magnitude
        if x_val == 0:
            label = "0"
        elif x_val >= 10:
            label = f"{int(x_val)}"
        elif x_val >= 1:
            label = f"{x_val:.1f}"
        else:
            label = f"{x_val:.2f}"
        draw.text((x_pos, DISPLAY_HEIGHT - margin_bottom + 5), label, 
                  fill=axis_color, anchor="mt", font=font_small)
    
    # Y-axis tick marks and labels
    num_y_ticks = 4
    for i in range(num_y_ticks + 1):
        y_val = u_max * i / num_y_ticks
        y_pos = DISPLAY_HEIGHT - margin_bottom - plot_height * i / num_y_ticks
        # Tick mark
        draw.line([(margin_left - 3, y_pos), (margin_left, y_pos)], fill=axis_color, width=1)
        # Label - format based on value magnitude
        if y_val == 0:
            label = "0"
        elif y_val >= 10:
            label = f"{int(y_val)}"
        elif y_val >= 1:
            label = f"{y_val:.1f}"
        else:
            label = f"{y_val:.2f}"
        draw.text((margin_left - 5, y_pos), label, fill=axis_color, anchor="rm", font=font_small)
    
    # Axis labels
    draw.text((DISPLAY_WIDTH // 2, DISPLAY_HEIGHT - 5), "x", fill=axis_color, anchor="mb", font=font_small)
    draw.text((8, DISPLAY_HEIGHT // 2), "U", fill=axis_color, anchor="mm", font=font_small)
    
    # Title
    draw.text((DISPLAY_WIDTH // 2, 8), "1D Diffusion", fill=(255, 255, 255), anchor="mt", font=font_title)
    
    return img

def render_2d_simulation(u, L=1.0):
    """Render 2D simulation as a heatmap with axis labels"""
    # Try to load font for axis labels
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except:
        font_small = ImageFont.load_default()
        font_title = ImageFont.load_default()
    
    # Define margins to make room for labels
    margin_left = 35
    margin_bottom = 30
    margin_top = 26
    margin_right = 10
    
    plot_width = DISPLAY_WIDTH - margin_left - margin_right
    plot_height = DISPLAY_HEIGHT - margin_top - margin_bottom
    
    # Normalize to 0-255 range
    u_min, u_max = u.min(), u.max()
    if u_max - u_min > 1e-10:
        u_norm = ((u - u_min) / (u_max - u_min) * 255).astype(np.uint8)
    else:
        u_norm = np.zeros_like(u, dtype=np.uint8)
    
    # Create grayscale image
    img_heat = Image.fromarray(u_norm, mode='L')
    
    # Convert to RGB with color map (cyan gradient)
    img_heat_rgb = Image.new('RGB', img_heat.size)
    pixels = img_heat.load()
    pixels_rgb = img_heat_rgb.load()
    
    for i in range(img_heat.size[0]):
        for j in range(img_heat.size[1]):
            val = pixels[i, j]
            # Gradient from dark blue to cyan
            r = int(val * 34 / 255)
            g = int(val * 211 / 255)
            b = int(val * 238 / 255 + (255 - val) * 15 / 255)
            pixels_rgb[i, j] = (r, g, b)
    
    # Resize heatmap to fit in plot area
    img_heat_rgb = img_heat_rgb.resize((plot_width, plot_height))
    
    # Create final image with margins for labels
    img = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(15, 23, 42))
    img.paste(img_heat_rgb, (margin_left, margin_top))
    
    draw = ImageDraw.Draw(img)
    axis_color = (148, 163, 184)
    
    # Draw border around heatmap
    draw.rectangle([(margin_left, margin_top), 
                    (margin_left + plot_width, margin_top + plot_height)], 
                   outline=axis_color, width=1)
    
    # X-axis tick marks and labels
    num_x_ticks = 4
    for i in range(num_x_ticks + 1):
        x_val = L * i / num_x_ticks
        x_pos = margin_left + plot_width * i / num_x_ticks
        # Tick mark
        draw.line([(x_pos, margin_top + plot_height), 
                   (x_pos, margin_top + plot_height + 3)], fill=axis_color, width=1)
        # Label - format based on value magnitude
        if x_val == 0:
            label = "0"
        elif x_val >= 10:
            label = f"{int(x_val)}"
        elif x_val >= 1:
            label = f"{x_val:.1f}"
        else:
            label = f"{x_val:.2f}"
        draw.text((x_pos, margin_top + plot_height + 5), label, 
                  fill=axis_color, anchor="mt", font=font_small)
    
    # Y-axis tick marks and labels
    num_y_ticks = 4
    for i in range(num_y_ticks + 1):
        y_val = L * i / num_y_ticks
        y_pos = margin_top + plot_height - plot_height * i / num_y_ticks
        # Tick mark
        draw.line([(margin_left - 3, y_pos), (margin_left, y_pos)], fill=axis_color, width=1)
        # Label - format based on value magnitude
        if y_val == 0:
            label = "0"
        elif y_val >= 10:
            label = f"{int(y_val)}"
        elif y_val >= 1:
            label = f"{y_val:.1f}"
        else:
            label = f"{y_val:.2f}"
        draw.text((margin_left - 5, y_pos), label, fill=axis_color, anchor="rm", font=font_small)
    
    # Axis labels
    draw.text((margin_left + plot_width // 2, DISPLAY_HEIGHT - 3), "x", 
              fill=axis_color, anchor="mb", font=font_small)
    draw.text((5, margin_top + plot_height // 2), "y", 
              fill=axis_color, anchor="mm", font=font_small)
    
    # Title
    draw.text((DISPLAY_WIDTH // 2, 5), "2D Diffusion", fill=(255, 255, 255), anchor="mt", font=font_title)
    
    return img

# ============================================================================
# Display Thread
# ============================================================================

def display_thread():
    """Main display loop"""
    global display_instance
    
    # Initialize display
    if DISPLAY_AVAILABLE:
        try:
            display_instance = ST7789.ST7789(
                height=DISPLAY_HEIGHT,
                width=DISPLAY_WIDTH,
                rotation=0,
                port=0,
                cs=0,                        # CE0 = 0, CE1 = 1
                dc=24,                       # DC pin (GPIO24)
                backlight=18,                # GPIO18 for PWM control
                spi_speed_hz=40 * 1000 * 1000  # Reduced speed for stability
            )
            # Explicitly turn on backlight if the method exists
            if hasattr(display_instance, 'set_backlight'):
                display_instance.set_backlight(True)
            print("✓ Display initialized successfully")
        except Exception as e:
            print(f"✗ Display initialization failed: {e}")
            display_instance = None
    
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
                img = render_2d_simulation(u, params['L'])
        
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
