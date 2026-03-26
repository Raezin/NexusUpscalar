# NexusUpscaler - AI-Powered Video Upscaler

## Overview
NexusUpscaler is an AI-powered video upscaling tool that converts 720p game footage to high-quality 1080p using a lightweight neural network trained on real game captures.

## Features
- 🎮 **Game-Optimized**: Trained on actual gameplay footage
- 🚀 **Fast**: 50+ FPS on Intel Iris Xe
- 📦 **Lightweight**: Only 0.09 MB model size
- 🎨 **AI-Powered**: Removes compression artifacts, adds realistic detail
- ⚙️ **Smart Resource Management**: Auto-detects hardware and limits usage
- 📁 **Drag & Drop**: Easy file selection
- 🔧 **Advanced Settings**: Batch size, RAM/CPU limits, engine selection

## System Requirements
- **CPU**: Intel Core i5 or better
- **GPU**: Intel Iris Xe (or any OpenCL-compatible GPU)
- **RAM**: 8GB recommended
- **Storage**: 100MB for model + output videos

## Installation

### Windows
1. Download or clone this repository
2. Double-click `launch.bat` to setup and run

### Manual Setup
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py