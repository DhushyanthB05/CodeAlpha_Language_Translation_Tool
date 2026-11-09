"""
CodeAlpha Language Translation Tool - Automated Unit Tests
===========================================================
Module: tests/test_translator.py
Description:
    Comprehensive unit tests for the Translation Engine.
    Uses unittest.mock to deterministically test API request formatting,
    response parsing, error conditions, history tracking, and configuration.
    
    All external network calls are mocked to ensure 100% deterministic,
    offline, and reproducible testing.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import requests

from translator import (
    Language,
    LibreTranslator,
    MyMemoryTranslator,
    TranslationResult,
    TranslationService,
)


class TestLibreTranslatorMocked(unittest.TestCase):
    """Automated unit test suite verifying translation client with mocked HTTP responses."""

    def setUp(self) -> None:
        """Sets up a clean test client instance before each test."""
        self.client = LibreTranslator(
            base_url="https://mock-translate.example.com",
            api_key="mock_secret_key",
            timeout=5.0
        )

    # --------------------------------------------------------------------------
    # Test 1: API Request Formatting
    # --------------------------------------------------------------------------
    @patch("requests.post")
    def test_01_api_request_formatting(self, mock_post: MagicMock) -> None:
        """Verifies that API request payload, headers, and endpoints are properly formatted."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"translatedText": "Hola Mundo"}
        mock_post.return_value = mock_response

        result = self.client.translate("Hello World", "en", "es")

        # Verify requests.post was called with exact URL and JSON payload
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://mock-translate.example.com/translate")
        self.assertEqual(kwargs["json"]["q"], "Hello World")
        self.assertEqual(kwargs["json"]["source"], "en")
        self.assertEqual(kwargs["json"]["target"], "es")
        self.assertEqual(kwargs["json"]["format"], "text")
        self.assertEqual(kwargs["json"]["api_key"], "mock_secret_key")
        self.assertEqual(kwargs["timeout"], 5.0)
        self.assertTrue(result.success)

    # --------------------------------------------------------------------------
    # Test 2: Successful Translation Response Parsing
    # --------------------------------------------------------------------------
    @patch("requests.post")
    def test_02_successful_translation_response_parsing(self, mock_post: MagicMock) -> None:
        """Verifies that 200 OK responses with translated text are correctly parsed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "translatedText": "Bonjour le monde",
            "detectedLanguage": {"confidence": 99, "language": "en"}
        }
        mock_post.return_value = mock_response

        result = self.client.translate("Hello world", "auto", "fr")

        self.assertTrue(result.success)
        self.assertEqual(result.translated_text, "Bonjour le monde")
        self.assertEqual(result.target_language, "fr")
        self.assertEqual(result.status_code, 200)
        self.assertGreaterEqual(result.response_time_ms, 0.0)
        self.assertIsNone(result.error_message)

    # --------------------------------------------------------------------------
    # Test 3: Empty Text Handling
    # --------------------------------------------------------------------------
    @patch("requests.post")
    def test_03_empty_text_handling(self, mock_post: MagicMock) -> None:
        """Verifies that empty strings or whitespace-only inputs are rejected without API calls."""
        # Test completely empty text
        result_empty = self.client.translate("", "en", "es")
        self.assertFalse(result_empty.success)
        self.assertIn("cannot be empty", result_empty.error_message.lower())

        # Test whitespace-only text
        result_whitespace = self.client.translate("    \n\t  ", "en", "es")
        self.assertFalse(result_whitespace.success)
        self.assertIn("cannot be empty", result_whitespace.error_message.lower())

        # Crucial: No HTTP request should have been made
        mock_post.assert_not_called()

    # --------------------------------------------------------------------------
    # Test 4: Invalid Language / Target Handling
    # --------------------------------------------------------------------------
    @patch("requests.post")
    def test_04_invalid_language_handling(self, mock_post: MagicMock) -> None:
        """Verifies handling of missing target language or 400 Bad Request from API."""
        # Empty target language
        result = self.client.translate("Hello", "en", "")
        self.assertFalse(result.success)
        self.assertIn("target language must be selected", result.error_message.lower())
        mock_post.assert_not_called()

        # Simulated 400 Bad Request for unsupported pair
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Language pair 'xx' to 'yy' is not supported"}
        mock_post.return_value = mock_response

        result_unsupported = self.client.translate("Test", "xx", "yy")
        self.assertFalse(result_unsupported.success)
        self.assertEqual(result_unsupported.status_code, 400)
        self.assertIn("Language pair 'xx' to 'yy' is not supported", result_unsupported.error_message)

    # --------------------------------------------------------------------------
    # Test 5: API Timeout Handling
    # --------------------------------------------------------------------------
    @patch("requests.post", side_effect=requests.exceptions.Timeout("Read timed out"))
    def test_05_api_timeout(self, mock_post: MagicMock) -> None:
        """Verifies graceful handling when the translation API request times out."""
        result = self.client.translate("Long text to translate", "en", "de")

        self.assertFalse(result.success)
        self.assertIn("Connection Timeout", result.error_message)
        self.assertIn("timed out after 5.0s", result.error_message)
        self.assertEqual(result.translated_text, "")

    # --------------------------------------------------------------------------
    # Test 6: Connection Error Handling
    # --------------------------------------------------------------------------
    @patch("requests.post", side_effect=requests.exceptions.ConnectionError("Failed to resolve host"))
    def test_06_connection_errors(self, mock_post: MagicMock) -> None:
        """Verifies graceful handling when the host is unreachable or down."""
        result = self.client.translate("Hello", "en", "es")

        self.assertFalse(result.success)
        self.assertIn("Connection Failure", result.error_message)
        self.assertIn("Could not reach LibreTranslate server", result.error_message)

    # --------------------------------------------------------------------------
    # Test 7: Invalid API Responses
    # --------------------------------------------------------------------------
    @patch("requests.post")
    def test_07_invalid_api_responses(self, mock_post: MagicMock) -> None:
        """Verifies handling of malformed JSON or missing fields in 200 responses."""
        # 1. Non-JSON response (e.g. proxy returned raw HTML on 200)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON format")
        mock_post.return_value = mock_response

        result_malformed = self.client.translate("Hello", "en", "es")
        self.assertFalse(result_malformed.success)
        self.assertIn("malformed JSON", result_malformed.error_message)

        # 2. JSON without 'translatedText'
        mock_response.json.side_effect = None
        mock_response.json.return_value = {"otherKey": "Value"}
        result_missing_field = self.client.translate("Hello", "en", "es")
        self.assertFalse(result_missing_field.success)
        self.assertIn("missing 'translatedText'", result_missing_field.error_message)

    # --------------------------------------------------------------------------
    # Test 8: Translation History
    # --------------------------------------------------------------------------
    def test_08_translation_history(self) -> None:
        """Verifies translation history records additions, ordering, and clearing."""
        service = TranslationService()

        # Add two mocked results
        res1 = TranslationResult(
            success=True,
            original_text="Hello",
            translated_text="Hola",
            source_language="en",
            target_language="es",
            provider="LibreTranslate",
            response_time_ms=120.0
        )
        res2 = TranslationResult(
            success=True,
            original_text="Good morning",
            translated_text="Guten Morgen",
            source_language="en",
            target_language="de",
            provider="LibreTranslate",
            response_time_ms=110.0
        )

        service.add_history(res1)
        service.add_history(res2)

        history = service.history
        self.assertEqual(len(history), 2)
        # Latest first
        self.assertEqual(history[0].original_text, "Good morning")
        self.assertEqual(history[0].translated_text, "Guten Morgen")
        self.assertEqual(history[1].original_text, "Hello")

        # Test clear
        service.clear_history()
        self.assertEqual(len(service.history), 0)

    # --------------------------------------------------------------------------
    # Test 9: Language Swapping
    # --------------------------------------------------------------------------
    def test_09_language_swapping(self) -> None:
        """Verifies swapping source and target languages and detecting invalid 'auto' swap."""
        # Valid swap: en <-> es
        new_src, new_tgt, warn = TranslationService.swap_languages("en", "es")
        self.assertEqual(new_src, "es")
        self.assertEqual(new_tgt, "en")
        self.assertIsNone(warn)

        # Invalid swap: auto -> es (cannot swap auto to target)
        src_auto, tgt, warn_auto = TranslationService.swap_languages("auto", "es")
        self.assertEqual(src_auto, "auto")
        self.assertEqual(tgt, "es")
        self.assertIsNotNone(warn_auto)
        self.assertIn("Cannot swap when source language is set to 'Auto Detect'", warn_auto)

    # --------------------------------------------------------------------------
    # Test 10: Configuration Validation
    # --------------------------------------------------------------------------
    def test_10_configuration_validation(self) -> None:
        """Verifies configuration parsing, URL normalization, and fallback defaults."""
        # Test trailing slash strip
        client = LibreTranslator(base_url="https://translate.example.com///")
        self.assertEqual(client.base_url, "https://translate.example.com")

        # Test custom timeout
        client_custom = LibreTranslator(timeout=25.5)
        self.assertEqual(client_custom.timeout, 25.5)

        # Test service configuration updates
        service = TranslationService(provider_name="libretranslate")
        self.assertEqual(service.provider_name, "libretranslate")

        service.update_libre_config(
            base_url="http://localhost:5000/",
            api_key="new_key",
            timeout=15.0
        )
        self.assertEqual(service.libre_client.base_url, "http://localhost:5000")
        self.assertEqual(service.libre_client.api_key, "new_key")
        self.assertEqual(service.libre_client.timeout, 15.0)


if __name__ == "__main__":
    unittest.main()
