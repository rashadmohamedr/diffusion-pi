#!/usr/bin/env python3
"""
Circular Waveguide Simulator
Raspberry Pi Zero 2 W + ST7789 Display
TM Mode Analysis with Bessel Functions
"""

import os
import sys
import time
import threading
import socket
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, jsonify
from scipy.special import jn, yn, jn_zeros  # Bessel functions

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

# Physical constants
C_LIGHT = 3e8  # Speed of light in m/s

# Simulation defaults
DEFAULT_PARAMS = {
    'field_view': 'e_only',  # 'e_only', 'h_only'
    'radius': 20.0,          # Waveguide radius in mm
    'frequency': 10.0,       # Frequency in GHz
    'epsilon_r': 1.0,        # Relative permittivity
    'mu_r': 1.0,             # Relative permeability
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
# Waveguide Calculations
# ============================================================================

def calculate_waveguide_params(radius_mm, frequency_GHz, epsilon_r, mu_r):
    """
    Calculate waveguide parameters
    Returns: dict with wavelength, k, kc, beta, fc, etc.
    """
    radius = radius_mm / 1000  # Convert to meters
    frequency = frequency_GHz * 1e9  # Convert to Hz
    
    # Basic parameters
    wavelength = C_LIGHT / frequency
    k = 2 * np.pi / wavelength
    kc = 2.405 / radius  # First TM01 mode cutoff wave number
    fc = kc * C_LIGHT / (2 * np.pi * np.sqrt(epsilon_r * mu_r))  # Cutoff frequency
    
    # Propagation constant
    beta_squared = k**2 - kc**2
    beta = np.sqrt(max(0, beta_squared))
    
    # Check if above cutoff
    above_cutoff = frequency >= fc
    
    return {
        'wavelength': wavelength,
        'k': k,
        'kc': kc,
        'fc': fc,
        'beta': beta,
        'above_cutoff': above_cutoff,
        'radius': radius
    }

def calculate_field_distribution(params_dict, resolution=240):
    """
    Calculate TM01 mode field distribution
    Returns: theta, E_r, H_r arrays
    """
    theta = np.linspace(0, 2 * np.pi, resolution)
    k = params_dict['k']
    beta = params_dict['beta']
    radius = params_dict['radius']
    
    # Electric and magnetic field patterns (simplified TM01)
    E_r = (1 / (k + 1e-10)) * np.cos(beta * radius + 1e-10) * np.cos(theta)
    H_r = (1 / (k + 1e-10)) * np.sin(beta * radius + 1e-10) * np.cos(theta)
    
    return theta, E_r, H_r

def calculate_bessel_functions(x_max=15, resolution=500):
    """
    Calculate Bessel functions of first and second kind
    """
    x = np.linspace(0.01, x_max, resolution)
    
    J0 = jn(0, x)
    J1 = jn(1, x)
    Y0 = yn(0, x)
    Y1 = yn(1, x)
    
    # Get zeros of J0 (cutoff points)
    j0_zeros = jn_zeros(0, 5)
    
    return x, J0, J1, Y0, Y1, j0_zeros

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
    draw.text((120, 60), "Waveguide Sim", fill=(148, 163, 184), anchor="mm", font=font_medium)
    
    # IP Address
    if ip_address:
        draw.text((120, 120), ip_address, fill=(34, 211, 238), anchor="mm", font=font_large)
        draw.text((120, 160), f"http://{ip_address}:{WEB_PORT}", fill=(148, 163, 184), anchor="mm", font=font_small)
    else:
        draw.text((120, 120), "No Network", fill=(239, 68, 68), anchor="mm", font=font_medium)
    
    return img

def render_field_distribution(theta, E_r, H_r, wg_params, field_view='e_only'):
    """Render electric and magnetic field distributions in polar form"""
    img = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except:
        font_small = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_tiny = ImageFont.load_default()
    
    # Title
    above_cutoff = wg_params['above_cutoff']
    status = "✓" if above_cutoff else "✗"
    color = (34, 211, 238) if above_cutoff else (239, 68, 68)
    
    # Single larger plot
    field_name = "|E|" if field_view == 'e_only' else "|H|"
    draw.text((120, 5), f"{status} {field_name}", fill=color, anchor="mt", font=font_title)
    center_y1 = 120
    center_x = 120
    max_radius = 85
    
    # Normalize fields
    E_norm = np.abs(E_r)
    H_norm = np.abs(H_r)
    E_max = E_norm.max() if E_norm.max() > 1e-10 else 1.0
    H_max = H_norm.max() if H_norm.max() > 1e-10 else 1.0
    
    grid_color = (148, 163, 184, 80)
    axis_color = (148, 163, 184)
    cy = center_y1
    
    # Draw circular grid
    for r_frac in [0.5, 1.0]:
        r_grid = int(max_radius * r_frac)
        draw.ellipse([(center_x - r_grid, cy - r_grid), 
                      (center_x + r_grid, cy + r_grid)], 
                     outline=grid_color, width=1)
    
    # Draw Cartesian axes (X and Y)
    # Horizontal axis
    draw.line([(center_x - max_radius - 10, cy), (center_x + max_radius + 10, cy)], 
              fill=axis_color, width=2)
    # Vertical axis
    draw.line([(center_x, cy - max_radius - 10), (center_x, cy + max_radius + 10)], 
              fill=axis_color, width=2)
    
    # Add axis labels
    draw.text((center_x + max_radius + 15, cy), "x", fill=axis_color, anchor="lm", font=font_small)
    draw.text((center_x, cy - max_radius - 15), "y", fill=axis_color, anchor="mb", font=font_small)
    
    # Add tick marks and values on axes
    for i, frac in enumerate([0.5, 1.0]):
        tick_val = frac
        tick_pos = int(max_radius * frac)
        # Right side
        draw.line([(center_x + tick_pos, cy - 3), (center_x + tick_pos, cy + 3)], 
                  fill=axis_color, width=1)
        draw.text((center_x + tick_pos, cy + 8), f"{tick_val:.1f}", 
                  fill=axis_color, anchor="mt", font=font_tiny)
        # Left side
        draw.line([(center_x - tick_pos, cy - 3), (center_x - tick_pos, cy + 3)], 
                  fill=axis_color, width=1)
        draw.text((center_x - tick_pos, cy + 8), f"{-tick_val:.1f}", 
                  fill=axis_color, anchor="mt", font=font_tiny)
        # Top
        draw.line([(center_x - 3, cy - tick_pos), (center_x + 3, cy - tick_pos)], 
                  fill=axis_color, width=1)
        draw.text((center_x - 8, cy - tick_pos), f"{tick_val:.1f}", 
                  fill=axis_color, anchor="rm", font=font_tiny)
        # Bottom
        draw.line([(center_x - 3, cy + tick_pos), (center_x + 3, cy + tick_pos)], 
                  fill=axis_color, width=1)
        draw.text((center_x - 8, cy + tick_pos), f"{-tick_val:.1f}", 
                  fill=axis_color, anchor="rm", font=font_tiny)
    
    # Plot field based on view
    if field_view == 'e_only':
        field_color = (34, 211, 238)
        field_norm = E_norm
        field_max = E_max
    else:  # h_only
        field_color = (239, 68, 68)
        field_norm = H_norm
        field_max = H_max
    
    # Plot field
    points = []
    for i, t in enumerate(theta):
        r = (field_norm[i] / field_max) * max_radius
        x = center_x + r * np.cos(t)
        y = cy - r * np.sin(t)
        points.append((x, y))
    
    if len(points) > 1:
        draw.polygon(points, fill=(*field_color, 50), outline=field_color, width=2)
    
    return img

def render_bessel_functions():
    """Render Bessel functions J0 and J1"""
    img = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except:
        font_small = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_tiny = ImageFont.load_default()
    
    # Title
    draw.text((120, 5), "Bessel Functions", fill=(255, 255, 255), anchor="mt", font=font_title)
    
    # Calculate Bessel functions
    x, J0, J1, Y0, Y1, j0_zeros = calculate_bessel_functions(x_max=12, resolution=300)
    
    # Plot area
    margin = 30
    plot_width = DISPLAY_WIDTH - 2 * margin
    plot_height = (DISPLAY_HEIGHT - 60) // 2
    
    # Top plot: J0 and J1
    y_top = 35
    
    # Normalize and plot
    j_max = 1.2
    j_min = -0.6
    
    # Draw axes
    axis_y = y_top + int(plot_height * 0.6 / (j_max - j_min))
    draw.line([(margin, axis_y), (DISPLAY_WIDTH - margin, axis_y)], 
              fill=(148, 163, 184), width=1)
    # Y-axis
    draw.line([(margin, y_top), (margin, y_top + plot_height)], 
              fill=(148, 163, 184), width=1)
    
    # X-axis labels
    for x_val in [0, 3, 6, 9, 12]:
        x_pos = margin + (x_val / 12) * plot_width
        draw.line([(x_pos, axis_y), (x_pos, axis_y + 3)], fill=(148, 163, 184), width=1)
        draw.text((x_pos, axis_y + 5), str(x_val), fill=(148, 163, 184), anchor="mt", font=font_tiny)
    
    # Y-axis labels
    for y_val in [-0.5, 0, 0.5, 1.0]:
        y_pos = axis_y - ((y_val - 0) / (j_max - j_min)) * plot_height
        if y_top <= y_pos <= y_top + plot_height:
            draw.line([(margin - 3, y_pos), (margin, y_pos)], fill=(148, 163, 184), width=1)
            draw.text((margin - 5, y_pos), f"{y_val:.1f}", fill=(148, 163, 184), anchor="rm", font=font_tiny)
    
    # Plot J0 (blue)
    points_j0 = []
    for i, x_val in enumerate(x):
        x_pos = margin + (x_val / 12) * plot_width
        y_pos = axis_y - ((J0[i] - 0) / (j_max - j_min)) * plot_height
        points_j0.append((x_pos, y_pos))
    if len(points_j0) > 1:
        draw.line(points_j0, fill=(34, 211, 238), width=2)
    
    # Plot J1 (green)
    points_j1 = []
    for i, x_val in enumerate(x):
        x_pos = margin + (x_val / 12) * plot_width
        y_pos = axis_y - ((J1[i] - 0) / (j_max - j_min)) * plot_height
        points_j1.append((x_pos, y_pos))
    if len(points_j1) > 1:
        draw.line(points_j1, fill=(34, 197, 94), width=2)
    
    # Mark first zero
    if len(j0_zeros) > 0:
        zero_x = margin + (j0_zeros[0] / 12) * plot_width
        # Draw dashed line manually (PIL doesn't support linestyle)
        dash_length = 5
        y = y_top
        while y < y_top + plot_height:
            draw.line([(zero_x, y), (zero_x, min(y + dash_length, y_top + plot_height))], 
                      fill=(239, 68, 68), width=1)
            y += dash_length * 2
    
    # Labels
    draw.text((40, axis_y - 10), "J₀", fill=(34, 211, 238), anchor="mm", font=font_small)
    draw.text((40, axis_y + 10), "J₁", fill=(34, 197, 94), anchor="mm", font=font_small)
    
    # Bottom plot info
    y_bottom = y_top + plot_height + 30
    info_text = f"TM₀₁ cutoff: p₀₁ = {j0_zeros[0]:.3f}"
    draw.text((120, y_bottom), info_text, fill=(148, 163, 184), anchor="mt", font=font_small)
    
    return img

def render_cutoff_analysis(wg_params):
    """Render cutoff frequency analysis"""
    img = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    except:
        font_small = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_tiny = ImageFont.load_default()
    
    # Title
    draw.text((120, 5), "Cutoff Analysis", fill=(255, 255, 255), anchor="mt", font=font_title)
    
    # Get parameters
    fc_GHz = wg_params['fc'] / 1e9
    k = wg_params['k']
    kc = wg_params['kc']
    beta = wg_params['beta']
    above_cutoff = wg_params['above_cutoff']
    
    # Status display
    y_pos = 35
    status_color = (34, 211, 238) if above_cutoff else (239, 68, 68)
    status_text = "ABOVE CUTOFF" if above_cutoff else "BELOW CUTOFF"
    draw.text((120, y_pos), status_text, fill=status_color, anchor="mt", font=font_title)
    
    # Parameters display
    y_pos += 30
    params_text = [
        f"fc = {fc_GHz:.2f} GHz",
        f"k = {k:.2e} m⁻¹",
        f"kc = {kc:.2e} m⁻¹",
        f"β = {beta:.2e} m⁻¹"
    ]
    
    for text in params_text:
        draw.text((120, y_pos), text, fill=(148, 163, 184), anchor="mt", font=font_small)
        y_pos += 18
    
    # Simple dispersion diagram
    y_pos += 20
    draw.text((120, y_pos), "Dispersion Relation:", fill=(255, 255, 255), anchor="mt", font=font_small)
    
    # Draw k vs beta relationship
    margin = 40
    plot_width = DISPLAY_WIDTH - 2 * margin
    plot_height = 60
    y_plot = y_pos + 20
    
    # Draw axes
    draw.line([(margin, y_plot + plot_height), (DISPLAY_WIDTH - margin, y_plot + plot_height)], 
              fill=(148, 163, 184), width=1)
    draw.line([(margin, y_plot), (margin, y_plot + plot_height)], 
              fill=(148, 163, 184), width=1)
    
    # Draw kc line (cutoff)
    kc_x = margin + plot_width * 0.3
    draw.line([(kc_x, y_plot), (kc_x, y_plot + plot_height)], 
              fill=(239, 68, 68), width=2)
    draw.text((kc_x, y_plot + plot_height + 5), "kc", fill=(239, 68, 68), anchor="mt", font=font_tiny)
    
    # Draw current k
    k_ratio = min(k / (kc * 2), 1.0)
    k_x = margin + plot_width * k_ratio
    draw.line([(k_x, y_plot), (k_x, y_plot + plot_height)], 
              fill=status_color, width=2)
    draw.text((k_x, y_plot + plot_height + 5), "k", fill=status_color, anchor="mt", font=font_tiny)
    
    return img

def render_radial_profile(wg_params):
    """Render radial field profile"""
    img = Image.new('RGB', (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)
    
    try:
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        font_tiny = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
    except:
        font_small = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_tiny = ImageFont.load_default()
    
    # Title
    draw.text((120, 5), "Radial Profile", fill=(255, 255, 255), anchor="mt", font=font_title)
    
    # Calculate radial profile
    radius = wg_params['radius']
    k = wg_params['k']
    beta = wg_params['beta']
    
    rho = np.linspace(0.001, radius, 200)
    E_r_profile = (1 / (k + 1e-10)) * np.cos(beta * rho + 1e-10)
    
    # Plot area
    margin_left = 35
    margin_right = 15
    margin_bottom = 30
    margin_top = 35
    
    plot_width = DISPLAY_WIDTH - margin_left - margin_right
    plot_height = DISPLAY_HEIGHT - margin_top - margin_bottom
    
    # Normalize
    E_max = np.abs(E_r_profile).max()
    if E_max > 1e-10:
        E_norm = np.abs(E_r_profile) / E_max
    else:
        E_norm = np.zeros_like(E_r_profile)
    
    # Plot
    points = []
    for i, r in enumerate(rho):
        x_pos = margin_left + (r / radius) * plot_width
        y_pos = DISPLAY_HEIGHT - margin_bottom - E_norm[i] * plot_height
        points.append((x_pos, y_pos))
    
    # Fill under curve
    if len(points) > 1:
        fill_points = [(margin_left, DISPLAY_HEIGHT - margin_bottom)]
        fill_points.extend(points)
        fill_points.append((margin_left + plot_width, DISPLAY_HEIGHT - margin_bottom))
        draw.polygon(fill_points, fill=(34, 211, 238, 50))
        draw.line(points, fill=(34, 211, 238), width=2)
    
    # Axes
    axis_color = (148, 163, 184)
    draw.line([(margin_left, DISPLAY_HEIGHT - margin_bottom), 
               (DISPLAY_WIDTH - margin_right, DISPLAY_HEIGHT - margin_bottom)], 
              fill=axis_color, width=1)
    draw.line([(margin_left, margin_top), (margin_left, DISPLAY_HEIGHT - margin_bottom)], 
              fill=axis_color, width=1)
    
    # X-axis tick marks and labels (radial position)
    radius_mm = wg_params['radius'] * 1000  # Convert to mm
    num_ticks = 4
    for i in range(num_ticks + 1):
        r_val = (radius_mm * i / num_ticks)
        x_pos = margin_left + (i / num_ticks) * plot_width
        draw.line([(x_pos, DISPLAY_HEIGHT - margin_bottom), 
                   (x_pos, DISPLAY_HEIGHT - margin_bottom + 3)], fill=axis_color, width=1)
        label = f"{r_val:.0f}" if r_val >= 1 else f"{r_val:.1f}"
        draw.text((x_pos, DISPLAY_HEIGHT - margin_bottom + 5), label, 
                  fill=axis_color, anchor="mt", font=font_tiny)
    
    # Y-axis tick marks
    for i in range(5):
        y_pos = margin_top + (plot_height * i / 4)
        draw.line([(margin_left - 3, y_pos), (margin_left, y_pos)], fill=axis_color, width=1)
    
    # Labels
    draw.text((120, DISPLAY_HEIGHT - 5), "ρ (mm)", fill=axis_color, anchor="mb", font=font_small)
    draw.text((10, 120), "|E|", fill=axis_color, anchor="mm", font=font_small)
    
    # Mark boundary
    bound_x = margin_left + plot_width
    draw.line([(bound_x, margin_top), (bound_x, DISPLAY_HEIGHT - margin_bottom)], 
              fill=(239, 68, 68), width=2)
    draw.text((bound_x - 3, margin_top - 5), "a", fill=(239, 68, 68), anchor="rb", font=font_small)
    
    return img
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
    
    while not shutdown_event.is_set():
        current_time = time.time()
        
        # Show IP address at startup
        if current_time < ip_show_until:
            img = create_ip_display(current_ip)
        else:
            # Get waveguide parameters
            with state_lock:
                params = simulation_state.copy()
            
            # Calculate waveguide parameters
            wg_params = calculate_waveguide_params(
                params['radius'], params['frequency'],
                params['epsilon_r'], params['mu_r']
            )
            
            # Render field distribution with specified view
            theta, E_r, H_r = calculate_field_distribution(wg_params)
            img = render_field_distribution(theta, E_r, H_r, wg_params, params.get('field_view', 'both'))
        
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
            if 'field_view' in data:
                simulation_state['field_view'] = data['field_view']
            if 'radius' in data:
                simulation_state['radius'] = float(data['radius'])
            if 'frequency' in data:
                simulation_state['frequency'] = float(data['frequency'])
            if 'epsilon_r' in data:
                simulation_state['epsilon_r'] = float(data['epsilon_r'])
            if 'mu_r' in data:
                simulation_state['mu_r'] = float(data['mu_r'])
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
    print("Circular Waveguide Simulator - TM Mode Analysis")
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
