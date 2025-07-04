#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting Chrome installation..."

# Download Google Chrome .deb package
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Install the downloaded package
# dpkg -i attempts to install the package. If dependencies are missing, it will fail.
# apt-get install -f attempts to fix broken dependencies by installing them.
sudo dpkg -i google-chrome-stable_current_amd64.deb || sudo apt-get install -f -y

# Clean up the downloaded .deb file
rm google-chrome-stable_current_amd64.deb

echo "Chrome installation finished."

# Your existing Python dependency installation (if any, usually handled by Render automatically)
# pip install -r requirements.txt