#!/usr/bin/env bash

# Exit on error
set -o errexit

echo "Starting Chrome installation for Render..."

# Install Chrome dependencies
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libwayland-client0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxkbcommon0 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils

# Download and install Chrome
echo "Downloading Google Chrome..."
wget -q -O /tmp/google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
echo "Installing Google Chrome..."
apt-get install -y -qq /tmp/google-chrome-stable_current_amd64.deb
rm /tmp/google-chrome-stable_current_amd64.deb

# Verify installation and show version
if which google-chrome; then
    echo "Chrome installed successfully at: $(which google-chrome)"
    google-chrome --version
elif which google-chrome-stable; then
    echo "Chrome installed successfully at: $(which google-chrome-stable)"
    google-chrome-stable --version
    # Create symlink for easier access
    ln -sf /usr/bin/google-chrome-stable /usr/bin/google-chrome
else
    echo "Warning: Chrome installation verification failed, but continuing..."
fi

# Set environment variable for Render
export RENDER=true

echo "Chrome installation complete."