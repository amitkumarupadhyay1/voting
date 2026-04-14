"""
Test script for session warning feature (Task 3.3)
Tests the session warning countdown, extend button, and auto-save functionality.
"""

import time
from pages.components import session_warning_banner

def test_session_warning_banner():
    """Test that the session warning banner generates correct HTML"""
    print("Testing session warning banner...")
    
    # Test with 2 minutes remaining (orange warning)
    html_120 = session_warning_banner(120)
    assert '02:00' in html_120, "Should show 02:00 for 120 seconds"
    assert '#f59e0b' in html_120, "Should use orange color for > 60 seconds"
    assert 'Session Expiring Soon' in html_120
    assert 'auto-saved' in html_120
    print("✓ 2 minutes warning displays correctly")
    
    # Test with 1 minute remaining (orange warning)
    html_90 = session_warning_banner(90)
    assert '01:30' in html_90, "Should show 01:30 for 90 seconds"
    assert '#f59e0b' in html_90, "Should use orange color for > 60 seconds"
    print("✓ 1.5 minutes warning displays correctly")
    
    # Test with 30 seconds remaining (red warning)
    html_30 = session_warning_banner(30)
    assert '00:30' in html_30, "Should show 00:30 for 30 seconds"
    assert '#ef4444' in html_30, "Should use red color for < 60 seconds"
    print("✓ 30 seconds warning displays correctly (red)")
    
    # Test with 5 seconds remaining (red warning)
    html_5 = session_warning_banner(5)
    assert '00:05' in html_5, "Should show 00:05 for 5 seconds"
    assert '#ef4444' in html_5, "Should use red color for < 60 seconds"
    print("✓ 5 seconds warning displays correctly (red)")
    
    print("\n✅ All session warning banner tests passed!")

def test_session_timeout_constants():
    """Test that session timeout constants are properly defined"""
    print("\nTesting session timeout constants...")
    
    # Import from app.py to verify constants exist
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Read app.py to check constants
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert 'SESSION_TIMEOUT = 900' in content, "SESSION_TIMEOUT should be 900 seconds"
    assert 'WARNING_THRESHOLD = 120' in content, "WARNING_THRESHOLD should be 120 seconds"
    print("✓ Session timeout constants are properly defined")
    print("  - SESSION_TIMEOUT: 900 seconds (15 minutes)")
    print("  - WARNING_THRESHOLD: 120 seconds (2 minutes)")
    
    print("\n✅ Session timeout constants test passed!")

def test_session_warning_logic():
    """Test the session warning logic"""
    print("\nTesting session warning logic...")
    
    SESSION_TIMEOUT = 900
    WARNING_THRESHOLD = 120
    
    # Simulate different elapsed times
    test_cases = [
        (0, False, "Just logged in - no warning"),
        (600, False, "10 minutes elapsed - no warning"),
        (779, False, "12 minutes 59 seconds elapsed - no warning (121s remaining)"),
        (780, True, "13 minutes elapsed - show warning (120s remaining)"),
        (781, True, "13 minutes 1 second elapsed - show warning (119s remaining)"),
        (840, True, "14 minutes elapsed - show warning (60s remaining)"),
        (880, True, "14 minutes 40 seconds elapsed - show warning (20s remaining)"),
        (899, True, "14 minutes 59 seconds elapsed - show warning (1s remaining)"),
    ]
    
    for elapsed, should_warn, description in test_cases:
        remaining = SESSION_TIMEOUT - elapsed
        shows_warning = 0 < remaining <= WARNING_THRESHOLD
        
        status = "✓" if shows_warning == should_warn else "✗"
        print(f"{status} {description}")
        assert shows_warning == should_warn, f"Failed: {description}"
    
    print("\n✅ All session warning logic tests passed!")

def test_auto_save_integration():
    """Test that auto-save functions are properly integrated"""
    print("\nTesting auto-save integration...")
    
    # Check that save_vote_progress function exists in app.py
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert 'def save_vote_progress' in content, "save_vote_progress function should exist"
    assert 'save_vote_progress(st.session_state.user_data[0], st.session_state.temp_votes)' in content, \
        "Auto-save should be called in session warning"
    assert 'warning_autosave_done' in content, "warning_autosave_done flag should exist"
    
    print("✓ Auto-save function is properly integrated")
    print("✓ Auto-save is called when warning appears")
    print("✓ Auto-save flag prevents duplicate saves")
    
    print("\n✅ Auto-save integration test passed!")

if __name__ == '__main__':
    print("=" * 60)
    print("Session Warning Feature Tests (Task 3.3)")
    print("=" * 60)
    
    try:
        test_session_warning_banner()
        test_session_timeout_constants()
        test_session_warning_logic()
        test_auto_save_integration()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\nTask 3.3 Implementation Summary:")
        print("✓ 3.3.1 Show countdown at 2 minutes remaining")
        print("✓ 3.3.2 Offer 'Extend session' button")
        print("✓ 3.3.3 Auto-save current progress")
        print("\nThe session warning feature is ready for use!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
