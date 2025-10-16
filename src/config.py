"""
Configuration management for Zelda AI Player.
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for Zelda AI Player."""
    
    # PyBoy Configuration
    ROM_PATH = os.getenv('ROM_PATH', 'roms/zelda.gb')
    GAME_SPEED = float(os.getenv('GAME_SPEED', '1.0'))
    WINDOW_TYPE = os.getenv('WINDOW_TYPE', 'SDL2')  # SDL2, headless, or OpenGL
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
    AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
    AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
    AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')
    
    # Game Loop Configuration
    MAX_FRAMES = int(os.getenv('MAX_FRAMES', '10000'))
    DECISION_INTERVAL = int(os.getenv('DECISION_INTERVAL', '5'))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/zelda_ai.log')
    
    # Screen Capture Configuration
    SCREEN_TARGET_SIZE = (320, 288)  # 2x scale of original 160x144
    
    # Controller Configuration
    BUTTON_PRESS_DURATION = float(os.getenv('BUTTON_PRESS_DURATION', '0.1'))
    ACTION_COOLDOWN = float(os.getenv('ACTION_COOLDOWN', '0.05'))
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        errors = []
        
        # Check required Azure OpenAI settings
        if not cls.AZURE_OPENAI_ENDPOINT:
            errors.append("AZURE_OPENAI_ENDPOINT not set")
        if not cls.AZURE_OPENAI_API_KEY:
            errors.append("AZURE_OPENAI_API_KEY not set")
        if not cls.AZURE_OPENAI_DEPLOYMENT_NAME:
            errors.append("AZURE_OPENAI_DEPLOYMENT_NAME not set")
        
        # Check ROM file exists
        if not os.path.exists(cls.ROM_PATH):
            errors.append(f"ROM file not found: {cls.ROM_PATH}")
        
        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    @classmethod
    def print_config(cls):
        """Print current configuration."""
        print("Current Configuration:")
        print(f"  ROM Path: {cls.ROM_PATH}")
        print(f"  Game Speed: {cls.GAME_SPEED}")
        print(f"  Max Frames: {cls.MAX_FRAMES}")
        print(f"  Decision Interval: {cls.DECISION_INTERVAL}")
        print(f"  Azure Endpoint: {cls.AZURE_OPENAI_ENDPOINT}")
        print(f"  Azure Deployment: {cls.AZURE_OPENAI_DEPLOYMENT_NAME}")
        print(f"  Log Level: {cls.LOG_LEVEL}")
        print(f"  Button Press Duration: {cls.BUTTON_PRESS_DURATION}s")
        print(f"  Action Cooldown: {cls.ACTION_COOLDOWN}s")
