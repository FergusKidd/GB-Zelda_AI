#!/usr/bin/env python3
"""
Test script to verify Zelda AI Player setup.
"""
import os
import sys
import logging
from pathlib import Path

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test if all modules can be imported."""
    print("Testing imports...")
    
    try:
        from pyboy_client import PyBoyClient
        print("✓ PyBoyClient imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import PyBoyClient: {e}")
        return False
    
    try:
        from azure_client import AzureOpenAIClient
        print("✓ AzureOpenAIClient imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import AzureOpenAIClient: {e}")
        return False
    
    try:
        from screen_capture import ScreenCapture
        print("✓ ScreenCapture imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ScreenCapture: {e}")
        return False
    
    try:
        from local_controller import LocalController
        print("✓ LocalController imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import LocalController: {e}")
        return False
    
    try:
        from config import Config
        print("✓ Config imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Config: {e}")
        return False
    
    return True

def test_dependencies():
    """Test if required dependencies are installed."""
    print("\nTesting dependencies...")
    
    dependencies = [
        ('pyboy', 'PyBoy'),
        ('openai', 'OpenAI'),
        ('azure.identity', 'Azure Identity'),
        ('PIL', 'Pillow'),
        ('numpy', 'NumPy'),
        ('cv2', 'OpenCV'),
        ('dotenv', 'python-dotenv')
    ]
    
    all_good = True
    
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"✓ {name} is installed")
        except ImportError:
            print(f"✗ {name} is not installed")
            all_good = False
    
    return all_good

def test_configuration():
    """Test configuration."""
    print("\nTesting configuration...")
    
    try:
        from config import Config
        
        # Test configuration validation
        is_valid = Config.validate()
        if is_valid:
            print("✓ Configuration is valid")
        else:
            print("✗ Configuration has errors")
        
        # Print current config
        Config.print_config()
        
        return is_valid
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_directories():
    """Test if required directories exist."""
    print("\nTesting directories...")
    
    required_dirs = ['src', 'logs', 'roms', 'models']
    all_good = True
    
    for directory in required_dirs:
        if Path(directory).exists():
            print(f"✓ Directory exists: {directory}")
        else:
            print(f"✗ Directory missing: {directory}")
            all_good = False
    
    return all_good

def test_files():
    """Test if required files exist."""
    print("\nTesting files...")
    
    required_files = [
        'requirements.txt',
        'main.py',
        'setup.py',
        'env.example',
        'README.md'
    ]
    
    all_good = True
    
    for file in required_files:
        if Path(file).exists():
            print(f"✓ File exists: {file}")
        else:
            print(f"✗ File missing: {file}")
            all_good = False
    
    return all_good

def main():
    """Main test function."""
    print("Zelda AI Player - Setup Test")
    print("=" * 40)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Files", test_files),
        ("Directories", test_directories),
        ("Imports", test_imports),
        ("Configuration", test_configuration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name} Test:")
        print("-" * 20)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 40)
    print("Test Results:")
    print("=" * 40)
    
    all_passed = True
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Setup is complete.")
        print("\nYou can now run: python main.py")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        print("\nTry running: python setup.py")

if __name__ == "__main__":
    main()
