#!/usr/bin/env python3
"""Basic functionality test for AI-Maga."""

import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_imports():
    """Test that all modules can be imported."""
    try:
        from app.settings import settings
        print("[OK] Settings imported successfully")

        from app.schemas import HealthResponse, UserMode
        print("[OK] Schemas imported successfully")

        from app.services.yandex_llm import complete_text
        print("[OK] Yandex LLM imported successfully")

        from app.services.yandex_tts import synthesize_speech
        print("[OK] Yandex TTS imported successfully")

        from app.services.mode import mode_manager
        print("[OK] Mode manager imported successfully")

        from app.services.tg_utils import send_text_message
        print("[OK] Telegram utils imported successfully")

        print("\n[SUCCESS] All imports successful!")
        return True

    except Exception as e:
        print(f"[ERROR] Import error: {e}")
        return False

def test_settings():
    """Test settings loading."""
    try:
        from app.settings import settings
        print(f"[OK] Webhook path: {settings.webhook_path}")
        print(f"[OK] Port: {settings.port}")
        print(f"[OK] Log level: {settings.log_level}")
        return True
    except Exception as e:
        print(f"[ERROR] Settings error: {e}")
        return False

def test_mode_manager():
    """Test mode manager functionality."""
    try:
        from app.services.mode import mode_manager, determine_response_mode

        # Test mode setting
        mode_manager.set_user_mode(123, "voice")
        mode = mode_manager.get_user_mode(123)
        assert mode == "voice", f"Expected 'voice', got {mode}"

        # Test response mode determination
        response_mode = determine_response_mode(123, "text", "Hello world")
        assert response_mode == "voice", f"Expected 'voice', got {response_mode}"

        response_mode = determine_response_mode(456, "text", "Hello world")
        assert response_mode == "text", f"Expected 'text', got {response_mode}"

        print("[OK] Mode manager works correctly")
        return True
    except Exception as e:
        print(f"[ERROR] Mode manager error: {e}")
        return False

if __name__ == "__main__":
    print("[TEST] Running basic functionality tests...\n")

    results = []
    results.append(("Imports", test_imports()))
    results.append(("Settings", test_settings()))
    results.append(("Mode Manager", test_mode_manager()))

    print("\n[RESULTS] Test Results:")
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {test_name}: {status}")

    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n[SUCCESS] All basic tests passed!")
        sys.exit(0)
    else:
        print("\n[ERROR] Some tests failed!")
        sys.exit(1)
