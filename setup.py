#!/usr/bin/env python3
"""
Setup script for Zelda AI Player.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        sys.exit(1)
    print(f"Python version: {sys.version}")

def install_dependencies():
    """Install required dependencies."""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

def create_directories():
    """Create necessary directories."""
    directories = ['logs', 'roms', 'models']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"Created directory: {directory}")

def create_env_file():
    """Create .env file from template if it doesn't exist."""
    env_file = Path('.env')
    env_example = Path('env.example')
    
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        print("Created .env file from template")
        print("Please edit .env file with your Azure OpenAI credentials")
    elif env_file.exists():
        print(".env file already exists")
    else:
        print("Warning: No .env.example file found")

def check_rom_file():
    """Check if ROM file exists."""
    rom_path = Path('roms/zelda.gb')
    if not rom_path.exists():
        print("Warning: ROM file not found at roms/zelda.gb")
        print("Please place your Zelda ROM file in the roms/ directory")
    else:
        print(f"ROM file found: {rom_path}")

def main():
    """Main setup function."""
    print("Setting up Zelda AI Player...")
    print("=" * 50)
    
    check_python_version()
    create_directories()
    install_dependencies()
    create_env_file()
    check_rom_file()
    
    print("=" * 50)
    print("Setup completed!")
    print("\nNext steps:")
    print("1. Edit .env file with your Azure OpenAI credentials")
    print("2. Place your Zelda ROM file in roms/zelda.gb")
    print("3. Run: python main.py")

if __name__ == "__main__":
    main()
