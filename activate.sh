#!/bin/bash
# Activation script for Zelda AI Player virtual environment

echo "🎮 Activating Zelda AI Player virtual environment..."
source venv/bin/activate

echo "✅ Virtual environment activated!"
echo "📦 Installed packages:"
pip list | grep -E "(pyboy|openai|azure|pillow|numpy|opencv|dotenv|aiohttp)"

echo ""
echo "🚀 Ready to play! You can now run:"
echo "   python main.py"
echo ""
echo "📝 To deactivate later, run: deactivate"
