"""
CodeAlpha Language Translation Tool - Translation Engine
=========================================================
Module: translator.py
Author: CodeAlpha AI Intern
Description:
    Production-grade translation service supporting LibreTranslate API
    (as primary configurable provider) and MyMemory API (as fallback/alternative).
    Provides robust HTTP error handling, automatic language detection,
    language caching, input validation, and history management.
"""

from __future__ import annotations

import html
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import requests

# ------------------------------------------------------------------------------
# Safe Environment Configuration Loader
# ------------------------------------------------------------------------------
def load_environment_variables(env_path: str = ".env") -> None:
    """
    Loads environment variables from a .env file.
    Prefers python-dotenv if installed; falls back to native parser.
    """
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(dotenv_path=env_path, override=False)
        return
    except ImportError:
        pass

    # Native fallback parser if python-dotenv is not installed
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key not in os.environ:
                        os.environ[key] = val
        except Exception:
            # Non-fatal error if file reading fails
            pass


# Execute on module import
load_environment_variables()


# ------------------------------------------------------------------------------
# Data Models
# ------------------------------------------------------------------------------
@dataclass
class Language:
    """Represents a supported language."""
    code: str
    name: str
    targets: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"{self.name} ({self.code})"


@dataclass
class TranslationResult:
    """Encapsulates the result of a translation request."""
    success: bool
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    provider: str
    detected_language: Optional[str] = None
    error_message: Optional[str] = None
    response_time_ms: float = 0.0
    status_code: Optional[int] = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


@dataclass
class TranslationHistoryItem:
    """Represents a record in the translation history."""
    id: int
    timestamp: str
    source_language: str
    target_language: str
    original_text: str
    translated_text: str
    provider: str
    response_time_ms: float


# ------------------------------------------------------------------------------
# Custom Exceptions
# ------------------------------------------------------------------------------
class TranslationError(Exception):
    """Base exception for all translation service errors."""
    pass


class APIConnectionError(TranslationError):
    """Raised when the translation service cannot be reached."""
    pass


class APITimeoutError(TranslationError):
    """Raised when an API request times out."""
    pass


class AuthenticationError(TranslationError):
    """Raised when an API key is missing, invalid, or expired."""
    pass


class RateLimitError(TranslationError):
    """Raised when the API rate limit is exceeded."""
    pass


class InvalidLanguageError(TranslationError):
    """Raised when unsupported language codes are supplied."""
    pass


# ------------------------------------------------------------------------------
# LibreTranslate Provider Implementation
# ------------------------------------------------------------------------------
class LibreTranslator:
    """
    Client for LibreTranslate API instances.
    Supports official, self-hosted, and community mirror endpoints.
    """

    # Official baseline languages supported by Argos Translate models
    FALLBACK_LANGUAGES: List[Dict[str, str]] = [
        {"code": "ar", "name": "Arabic"},
        {"code": "az", "name": "Azerbaijani"},
        {"code": "bg", "name": "Bulgarian"},
        {"code": "bn", "name": "Bengali"},
        {"code": "ca", "name": "Catalan"},
        {"code": "cs", "name": "Czech"},
        {"code": "da", "name": "Danish"},
        {"code": "de", "name": "German"},
        {"code": "el", "name": "Greek"},
        {"code": "en", "name": "English"},
        {"code": "eo", "name": "Esperanto"},
        {"code": "es", "name": "Spanish"},
        {"code": "et", "name": "Estonian"},
        {"code": "eu", "name": "Basque"},
        {"code": "fa", "name": "Persian"},
        {"code": "fi", "name": "Finnish"},
        {"code": "fr", "name": "French"},
        {"code": "ga", "name": "Irish"},
        {"code": "gl", "name": "Galician"},
        {"code": "he", "name": "Hebrew"},
        {"code": "hi", "name": "Hindi"},
        {"code": "hu", "name": "Hungarian"},
        {"code": "id", "name": "Indonesian"},
        {"code": "it", "name": "Italian"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "ms", "name": "Malay"},
        {"code": "nb", "name": "Norwegian"},
        {"code": "nl", "name": "Dutch"},
        {"code": "pl", "name": "Polish"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "ro", "name": "Romanian"},
        {"code": "ru", "name": "Russian"},
        {"code": "sk", "name": "Slovak"},
        {"code": "sl", "name": "Slovenian"},
        {"code": "sq", "name": "Albanian"},
        {"code": "sv", "name": "Swedish"},
        {"code": "th", "name": "Thai"},
        {"code": "tl", "name": "Tagalog"},
        {"code": "tr", "name": "Turkish"},
        {"code": "uk", "name": "Ukrainian"},
        {"code": "ur", "name": "Urdu"},
        {"code": "vi", "name": "Vietnamese"},
        {"code": "zh-Hans", "name": "Chinese (Simplified)"},
        {"code": "zh-Hant", "name": "Chinese (Traditional)"},
    ]

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("LIBRETRANSLATE_API_URL")
            or "https://libretranslate.com"
        ).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("LIBRETRANSLATE_API_KEY", "")
        timeout_env = os.getenv("REQUEST_TIMEOUT", "10")
        try:
            self.timeout = float(timeout) if timeout is not None else float(timeout_env)
        except ValueError:
            self.timeout = 10.0

        self._cached_languages: Optional[List[Language]] = None

    def get_languages(self, force_refresh: bool = False) -> List[Language]:
        """
        Dynamically fetches supported languages from the configured LibreTranslate endpoint.
        Returns cached list if already fetched and refresh is not forced.
        """
        if self._cached_languages is not None and not force_refresh:
            return self._cached_languages

        endpoint = f"{self.base_url}/languages"
        try:
            response = requests.get(endpoint, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    languages = [
                        Language(
                            code=item.get("code", ""),
                            name=item.get("name", item.get("code", "")),
                            targets=item.get("targets", [])
                        )
                        for item in data
                        if isinstance(item, dict) and "code" in item
                    ]
                    # Sort alphabetically by language name
                    languages.sort(key=lambda x: x.name.lower())
                    self._cached_languages = languages
                    return languages
        except (requests.exceptions.RequestException, ValueError):
            # Graceful fallback to verified Argos/LibreTranslate language matrix
            pass

        fallback = [
            Language(code=item["code"], name=item["name"])
            for item in self.FALLBACK_LANGUAGES
        ]
        fallback.sort(key=lambda x: x.name.lower())
        self._cached_languages = fallback
        return fallback

    def detect_language(self, text: str) -> Optional[str]:
        """
        Detects the source language of the input text using /detect endpoint.
        Returns the ISO language code if detected, or None.
        """
        if not text or not text.strip():
            return None

        endpoint = f"{self.base_url}/detect"
        payload: Dict[str, Any] = {"q": text.strip()}
        if self.api_key:
            payload["api_key"] = self.api_key

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    return data[0].get("language")
        except requests.exceptions.RequestException:
            pass
        return None

    def translate(
        self,
        text: str,
        source: str,
        target: str,
    ) -> TranslationResult:
        """
        Translates text from source language to target language.
        Performs thorough input validation, error handling, and performance tracking.
        """
        start_time = time.perf_counter()

        # 1. Input Validation: Empty text
        if not text or not text.strip():
            return TranslationResult(
                success=False,
                original_text=text or "",
                translated_text="",
                source_language=source,
                target_language=target,
                provider="LibreTranslate",
                error_message="Input text cannot be empty. Please enter text to translate.",
                response_time_ms=0.0
            )

        # 2. Input Validation: Target language check
        if not target or not target.strip():
            return TranslationResult(
                success=False,
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
                provider="LibreTranslate",
                error_message="Target language must be selected.",
                response_time_ms=0.0
            )

        # 3. Same Language Optimization
        if source != "auto" and source == target:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return TranslationResult(
                success=True,
                original_text=text,
                translated_text=text,
                source_language=source,
                target_language=target,
                provider="LibreTranslate",
                response_time_ms=round(elapsed, 2)
            )

        # 4. Automatic Language Detection if source is 'auto'
        detected_lang: Optional[str] = None
        effective_source = source
        if source == "auto":
            detected_lang = self.detect_language(text)
            if detected_lang:
                effective_source = detected_lang
            else:
                effective_source = "auto"

        # 5. Build HTTP Request Payload
        endpoint = f"{self.base_url}/translate"
        payload: Dict[str, Any] = {
            "q": text.strip(),
            "source": effective_source,
            "target": target,
            "format": "text",
        }
        if self.api_key:
            payload["api_key"] = self.api_key

        headers = {"Content-Type": "application/json"}

        # 6. Execute Request with Robust Exception Handling
        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            elapsed = (time.perf_counter() - start_time) * 1000.0
            status_code = response.status_code

            # Handle 200 OK
            if status_code == 200:
                try:
                    data = response.json()
                except ValueError:
                    return TranslationResult(
                        success=False,
                        original_text=text,
                        translated_text="",
                        source_language=source,
                        target_language=target,
                        provider="LibreTranslate",
                        error_message="Invalid response: Server returned malformed JSON.",
                        response_time_ms=round(elapsed, 2),
                        status_code=status_code
                    )

                translated_text = data.get("translatedText")
                if translated_text is not None:
                    # If auto-detection was handled by API directly
                    if not detected_lang and isinstance(data.get("detectedLanguage"), dict):
                        detected_lang = data["detectedLanguage"].get("language")

                    return TranslationResult(
                        success=True,
                        original_text=text,
                        translated_text=translated_text,
                        source_language=effective_source,
                        target_language=target,
                        provider="LibreTranslate",
                        detected_language=detected_lang,
                        response_time_ms=round(elapsed, 2),
                        status_code=status_code
                    )
                else:
                    return TranslationResult(
                        success=False,
                        original_text=text,
                        translated_text="",
                        source_language=source,
                        target_language=target,
                        provider="LibreTranslate",
                        error_message="API response missing 'translatedText' field.",
                        response_time_ms=round(elapsed, 2),
                        status_code=status_code
                    )

            # Handle Known HTTP Errors with Clear Actionable Explanations
            error_details = ""
            try:
                err_json = response.json()
                if isinstance(err_json, dict) and "error" in err_json:
                    error_details = str(err_json["error"])
            except Exception:
                error_details = response.text[:150]

            if status_code == 400:
                if "API key" in error_details or "Visit https://portal.libretranslate.com" in error_details:
                    msg = (
                        f"Authentication Required (HTTP 400): The configured LibreTranslate endpoint "
                        f"({self.base_url}) requires an API key. "
                        f"Please add your key in the sidebar / .env, or switch to a local instance "
                        f"(e.g., http://localhost:5000) or the Fallback Provider."
                    )
                else:
                    msg = f"Bad Request (HTTP 400): {error_details or 'Invalid parameters or unsupported language pair.'}"
            elif status_code in (401, 403):
                msg = (
                    f"Authentication Error (HTTP {status_code}): Invalid or missing API key. "
                    f"Details: {error_details}"
                )
            elif status_code == 429:
                msg = (
                    f"Rate Limit Exceeded (HTTP 429): You have exceeded the request quota for "
                    f"endpoint {self.base_url}. Please wait a few minutes or provide an API key."
                )
            elif status_code >= 500:
                msg = (
                    f"Server Error (HTTP {status_code}): The translation server at {self.base_url} "
                    f"encountered an internal error. Please check server status or switch endpoints."
                )
            else:
                msg = f"API Error (HTTP {status_code}): {error_details}"

            return TranslationResult(
                success=False,
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
                provider="LibreTranslate",
                error_message=msg,
                response_time_ms=round(elapsed, 2),
                status_code=status_code
            )

        except requests.exceptions.Timeout:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return TranslationResult(
                success=False,
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
                provider="LibreTranslate",
                error_message=(
                    f"Connection Timeout: The request to {self.base_url} timed out after {self.timeout}s. "
                    f"Check your internet connection or verify the endpoint is responsive."
                ),
                response_time_ms=round(elapsed, 2)
            )

        except requests.exceptions.ConnectionError:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return TranslationResult(
                success=False,
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
                provider="LibreTranslate",
                error_message=(
                    f"Connection Failure: Could not reach LibreTranslate server at '{self.base_url}'. "
                    f"Ensure the server is running, the URL is correct, or check your network."
                ),
                response_time_ms=round(elapsed, 2)
            )

        except requests.exceptions.RequestException as e:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return TranslationResult(
                success=False,
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
                provider="LibreTranslate",
                error_message=f"Network Request Error: {str(e)}",
                response_time_ms=round(elapsed, 2)
            )


# ------------------------------------------------------------------------------
# Fallback / Alternative Provider: MyMemory Translation API
# ------------------------------------------------------------------------------
class MyMemoryTranslator:
    """
    Client for MyMemory Translation API.
    Provides instant, zero-key access to 100+ languages including
    Telugu, Tamil, Kannada, Malayalam, Hindi, French, German, Spanish, etc.
    """

    SUPPORTED_LANGUAGES: List[Dict[str, str]] = [
        {"code": "ar", "name": "Arabic"},
        {"code": "zh", "name": "Chinese"},
        {"code": "en", "name": "English"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "hi", "name": "Hindi"},
        {"code": "it", "name": "Italian"},
        {"code": "ja", "name": "Japanese"},
        {"code": "kn", "name": "Kannada"},
        {"code": "ko", "name": "Korean"},
        {"code": "ml", "name": "Malayalam"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "ru", "name": "Russian"},
        {"code": "es", "name": "Spanish"},
        {"code": "ta", "name": "Tamil"},
        {"code": "te", "name": "Telugu"},
        {"code": "tr", "name": "Turkish"},
        {"code": "ur", "name": "Urdu"},
    ]

    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("MYMEMORY_API_URL")
            or "https://api.mymemory.translated.net/get"
        )
        self.email = email if email is not None else os.getenv("MYMEMORY_USER_EMAIL", "")
        timeout_env = os.getenv("REQUEST_TIMEOUT", "10")
        try:
            self.timeout = float(timeout) if timeout is not None else float(timeout_env)
        except ValueError:
            self.timeout = 10.0

    def get_languages(self) -> List[Language]:
        """Returns the list of supported languages for MyMemory."""
        langs = [
            Language(code=item["code"], name=item["name"])
            for item in self.SUPPORTED_LANGUAGES
        ]
        langs.sort(key=lambda x: x.name.lower())
        return langs

    def translate(
        self,
        text: str,
        source: str,
        target: str,
    ) -> TranslationResult:
        """Translates text using the MyMemory API."""
        start_time = time.perf_counter()

        if not text or not text.strip():
            return TranslationResult(
                success=False,
                original_text=text or "",
                translated_text="",
                source_language=source,
                target_language=target,
                provider="MyMemory (Free Fallback)",
                error_message="Input text cannot be empty. Please enter text to translate.",
                response_time_ms=0.0
            )

        if source != "auto" and source == target:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return TranslationResult(
                success=True,
                original_text=text,
                translated_text=text,
                source_language=source,
                target_language=target,
                provider="MyMemory (Free Fallback)",
                response_time_ms=round(elapsed, 2)
            )

        # MyMemory expects 'autodetect' or standard ISO code for source
        src_code = "autodetect" if source == "auto" else source
        langpair = f"{src_code}|{target}"

        params: Dict[str, str] = {
            "q": text.strip(),
            "langpair": langpair
        }
        if self.email:
            params["de"] = self.email

        try:
            response = requests.get(self.base_url, params=params, timeout=self.timeout)
            elapsed = (time.perf_counter() - start_time) * 1000.0
            status_code = response.status_code

            if status_code == 200:
                data = response.json()
                response_data = data.get("responseData", {})
                translated = response_data.get("translatedText")

                # MyMemory can return status 403 in the JSON responseData even with HTTP 200
                res_status = data.get("responseStatus")
                if res_status and int(res_status) != 200:
                    err_details = data.get("responseDetails", "Translation error")
                    return TranslationResult(
                        success=False,
                        original_text=text,
                        translated_text="",
                        source_language=source,
                        target_language=target,
                        provider="MyMemory (Free Fallback)",
                        error_message=f"MyMemory Error ({res_status}): {err_details}",
                        response_time_ms=round(elapsed, 2),
                        status_code=int(res_status)
                    )

                if translated:
                    # Unescape HTML entities (MyMemory sometimes returns &#39; etc.)
                    clean_text = html.unescape(translated)
                    return TranslationResult(
                        success=True,
                        original_text=text,
                        translated_text=clean_text,
                        source_language=source,
                        target_language=target,
                        provider="MyMemory (Free Fallback)",
                        response_time_ms=round(elapsed, 2),
                        status_code=status_code
                    )

            return TranslationResult(
                success=False,
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
                provider="MyMemory (Free Fallback)",
                error_message=f"MyMemory HTTP Error: Status {status_code}",
                response_time_ms=round(elapsed, 2),
                status_code=status_code
            )

        except requests.exceptions.Timeout:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return TranslationResult(
                success=False,
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
                provider="MyMemory (Free Fallback)",
                error_message=f"Connection Timeout: MyMemory request timed out after {self.timeout}s.",
                response_time_ms=round(elapsed, 2)
            )
        except requests.exceptions.ConnectionError:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return TranslationResult(
                success=False,
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
                provider="MyMemory (Free Fallback)",
                error_message="Connection Failure: Could not reach MyMemory server.",
                response_time_ms=round(elapsed, 2)
            )
        except requests.exceptions.RequestException as e:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return TranslationResult(
                success=False,
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
                provider="MyMemory (Free Fallback)",
                error_message=f"Request Error: {str(e)}",
                response_time_ms=round(elapsed, 2)
            )


# ------------------------------------------------------------------------------
# Unified Translation Service & History Manager
# ------------------------------------------------------------------------------
class TranslationService:
    """
    Central controller managing active translation providers,
    language dictionaries, session history, and language swapping.
    """

    def __init__(
        self,
        provider_name: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> None:
        self.provider_name = (
            provider_name
            or os.getenv("TRANSLATION_PROVIDER")
            or "libretranslate"
        ).lower()

        self.libre_client = LibreTranslator(base_url=base_url, api_key=api_key, timeout=timeout)
        self.mymemory_client = MyMemoryTranslator(timeout=timeout)
        self.history: List[TranslationHistoryItem] = []
        self._history_counter = 0

    def set_provider(self, provider_name: str) -> None:
        """Switches active translation provider ('libretranslate' or 'mymemory')."""
        self.provider_name = provider_name.lower()

    def update_libre_config(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> None:
        """Updates LibreTranslate connection configuration."""
        if base_url is not None:
            self.libre_client.base_url = base_url.rstrip("/")
            self.libre_client._cached_languages = None  # Invalidate cache for new URL
        if api_key is not None:
            self.libre_client.api_key = api_key
        if timeout is not None:
            self.libre_client.timeout = float(timeout)
            self.mymemory_client.timeout = float(timeout)

    def get_supported_languages(self, force_refresh: bool = False) -> List[Language]:
        """
        Retrieves actual supported languages from the configured provider.
        Does NOT advertise unsupported languages.
        """
        if self.provider_name == "libretranslate":
            return self.libre_client.get_languages(force_refresh=force_refresh)
        elif self.provider_name == "mymemory":
            return self.mymemory_client.get_languages()
        return self.libre_client.get_languages()

    def translate(
        self,
        text: str,
        source: str,
        target: str,
    ) -> TranslationResult:
        """Executes translation through the active provider and records successful history."""
        if self.provider_name == "libretranslate":
            result = self.libre_client.translate(text, source, target)
        elif self.provider_name == "mymemory":
            result = self.mymemory_client.translate(text, source, target)
        else:
            result = TranslationResult(
                success=False,
                original_text=text,
                translated_text="",
                source_language=source,
                target_language=target,
                provider=self.provider_name,
                error_message=f"Unknown translation provider: {self.provider_name}"
            )

        if result.success:
            self.add_history(result)

        return result

    def add_history(self, result: TranslationResult) -> TranslationHistoryItem:
        """Adds a successful translation result to history."""
        self._history_counter += 1
        item = TranslationHistoryItem(
            id=self._history_counter,
            timestamp=result.timestamp,
            source_language=result.source_language,
            target_language=result.target_language,
            original_text=result.original_text,
            translated_text=result.translated_text,
            provider=result.provider,
            response_time_ms=result.response_time_ms
        )
        self.history.insert(0, item)  # Latest first
        return item

    def clear_history(self) -> None:
        """Clears all session translation history."""
        self.history.clear()

    @staticmethod
    def swap_languages(source: str, target: str) -> Tuple[str, str, Optional[str]]:
        """
        Swaps source and target language codes.
        If source is 'auto', swapping is invalid and returns a helpful warning.
        Returns: (new_source, new_target, warning_message_if_any)
        """
        if source == "auto":
            return source, target, "Cannot swap when source language is set to 'Auto Detect'."
        return target, source, None
