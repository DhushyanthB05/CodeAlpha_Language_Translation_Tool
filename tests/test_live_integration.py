"""
CodeAlpha Language Translation Tool - Live API Integration Tests
================================================================
Module: tests/test_live_integration.py
Description:
    Live integration tests against REAL translation API endpoints.
    IMPORTANT: This test suite makes ACTUAL external network requests.
    It does not mock responses, allowing validation against live servers.
    
    Distinction:
    - Mocked tests (test_translator.py): Deterministic, offline, runs anywhere.
    - Live tests (test_live_integration.py): Validates real-world API connectivity,
      real error messages, and live translation outputs.
"""

import os
import sys
import unittest

from translator import LibreTranslator, MyMemoryTranslator, TranslationService

# Ensure stdout handles Unicode in terminal output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class TestLiveAPIIntegration(unittest.TestCase):
    """Real live integration tests against remote translation endpoints."""

    def test_live_01_libretranslate_languages_endpoint(self) -> None:
        """Verifies real HTTP GET request to LibreTranslate /languages endpoint."""
        client = LibreTranslator(base_url="https://libretranslate.com", timeout=8.0)
        langs = client.get_languages(force_refresh=True)

        self.assertIsInstance(langs, list)
        self.assertGreater(len(langs), 0, "LibreTranslate should return supported languages")
        codes = [l.code for l in langs]
        self.assertIn("en", codes, "English must be in the supported languages list")
        self.assertIn("es", codes, "Spanish must be in the supported languages list")
        self.assertIn("fr", codes, "French must be in the supported languages list")
        print(f"\n[LIVE TEST] LibreTranslate /languages returned {len(langs)} live languages.")

    def test_live_02_libretranslate_auth_enforcement(self) -> None:
        """
        Verifies real response behavior when calling official LibreTranslate without an API key.
        LibreTranslate.com enforces API keys and returns HTTP 400.
        Our translator must catch this cleanly and return an informative error message.
        """
        client = LibreTranslator(
            base_url="https://libretranslate.com",
            api_key="",  # Deliberately empty
            timeout=8.0
        )
        result = client.translate("Hello world", "en", "es")

        self.assertFalse(result.success, "Translation without API key on libretranslate.com should fail")
        self.assertEqual(result.status_code, 400)
        self.assertIn("Authentication Required", result.error_message)
        print(f"[LIVE TEST] LibreTranslate properly rejected unauthenticated request: {result.error_message[:80]}...")

    def test_live_03_mymemory_live_translation(self) -> None:
        """
        Verifies real live translation via MyMemory API.
        Tests real translation to French and Telugu.
        """
        client = MyMemoryTranslator(timeout=8.0)

        # English to French
        res_fr = client.translate("Hello world", "en", "fr")
        self.assertTrue(res_fr.success, f"MyMemory translation to French failed: {res_fr.error_message}")
        self.assertTrue(len(res_fr.translated_text) > 0)
        print(f"[LIVE TEST] MyMemory 'Hello world' [en -> fr] = '{res_fr.translated_text}' (Response time: {res_fr.response_time_ms}ms)")

        # English to Telugu
        res_te = client.translate("Hello world", "en", "te")
        self.assertTrue(res_te.success, f"MyMemory translation to Telugu failed: {res_te.error_message}")
        self.assertTrue(len(res_te.translated_text) > 0)
        print(f"[LIVE TEST] MyMemory 'Hello world' [en -> te] = '{res_te.translated_text}' (Response time: {res_te.response_time_ms}ms)")


if __name__ == "__main__":
    unittest.main()
