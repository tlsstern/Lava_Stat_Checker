#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Starting Chrome installation..."

# Update apt-get and install dependencies for adding new repositories
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg

# Add Google Chrome GPG key
curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome-archive-keyring.gpg

# Add Google Chrome repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/google-chrome-archive-keyring.gpg] https://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list > /dev/null

# Update apt-get again and install Google Chrome
sudo apt-get update
sudo apt-get install -y google-chrome-stable

echo "Chrome installation finished."

# Your existing Python dependency installation (if any, usually handled by Render automatically)
# pip install -r requirements.txt