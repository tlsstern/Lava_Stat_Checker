#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting Chrome installation for Render..."

# Update package list
apt-get update

# Install required dependencies
apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb

# Add Google Chrome repository and key
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list

# Update and install Chrome
apt-get update
apt-get install -y google-chrome-stable

# Install ChromeDriver
CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1)
echo "Chrome version: $CHROME_VERSION"

# Clean up
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "Chrome installation finished."

# Python dependencies are handled by Render automatically via requirements.txt