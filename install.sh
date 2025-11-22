#!/bin/bash

# ============================================================================
# ROBOT CONTROL SYSTEM - INSTALLATION SCRIPT FOR RASPBERRY PI
# ============================================================================

set -e  # Exit on error

echo "========================================================================"
echo "ROBOT CONTROL SYSTEM - Installation Script"
echo "========================================================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Step 1: Updating system packages..."
sudo apt-get update

# Install system dependencies
echo ""
echo "Step 2: Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-opencv \
    python3-picamera2 \
    python3-numpy \
    python3-pil \
    libcamera-dev \
    git

# Add user to dialout group for serial access
echo ""
echo "Step 3: Adding user to dialout group..."
sudo usermod -a -G dialout $USER

# Create virtual environment WITH system site packages
echo ""
echo "Step 4: Creating virtual environment..."
if [ -d "venv" ]; then
    echo "Removing old venv..."
    rm -rf venv
fi

python3 -m venv --system-site-packages venv

# Activate virtual environment
echo ""
echo "Step 5: Installing Python packages..."
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Flask and dependencies
pip install Flask==3.0.0
pip install flask-socketio==5.3.5
pip install python-socketio==5.10.0
pip install python-engineio==4.8.0
pip install eventlet==0.33.3
pip install pyserial==3.5

echo ""
echo "========================================================================"
echo "Installation complete!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "  1. Connect both Arduino boards via USB"
echo "  2. Connect Pi Camera to CSI port"
echo "  3. Enable camera: sudo raspi-config → Interface Options → Camera"
echo "  4. Reboot if needed: sudo reboot"
echo "  5. Run: source venv/bin/activate && python app.py"
echo ""
echo "Note: You need to log out and back in for dialout group to take effect"
echo "========================================================================"
