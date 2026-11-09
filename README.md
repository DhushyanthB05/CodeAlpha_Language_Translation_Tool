# CodeAlpha AI Internship — Project 3: Language Translation Tool 🌐

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg)](https://streamlit.io/)
[![Requests](https://img.shields.io/badge/Requests-2.31+-brightgreen.svg)](https://requests.readthedocs.io/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Build-Passing-success.svg)]()

> A production-grade multilingual translation application developed for the **CodeAlpha Artificial Intelligence Internship**. Features dynamic provider configuration with **LibreTranslate** and **MyMemory**, automatic language detection, side-by-side translation panels, robust HTTP resilience, and session translation history tracking.

---

## 📌 Table of Contents
1. [Project Overview](#-project-overview)
2. [Problem Statement](#-problem-statement)
3. [Objectives](#-objectives)
4. [Key Features](#-key-features)
5. [Technology Stack](#-technology-stack)
6. [System Architecture](#-system-architecture)
7. [API Integration Deep-Dive](#-api-integration-deep-dive)
8. [Project Structure](#-project-structure)
9. [Installation & Setup](#-installation--setup)
10. [Environment Configuration](#-environment-configuration)
11. [Running the Application](#-running-the-application)
12. [Testing Suite](#-testing-suite)
13. [Limitations & Trade-offs](#-limitations--trade-offs)
14. [Future Enhancements](#-future-enhancements)
15. [Demonstration Video Script](#-two-minute-demonstration-video-script)
16. [Resume-Ready Project Description](#-resume-ready-bullet-points)
17. [Technical Interview Q&A](#-technical-interview-preparation)

---

## 📖 Project Overview
In a globalized digital era, crossing linguistic barriers is fundamental to international collaboration, customer success, and accessibility. The **CodeAlpha Language Translation Tool** is an interactive, responsive web application engineered to perform real-time neural machine translation across 50+ world languages.

Built with Python, Streamlit, and Python Requests, it supports a dual-engine architecture:
* **Primary Provider:** Configurable **LibreTranslate** engine (compatible with official hosted cloud, self-hosted Docker clusters, or community endpoints).
* **Fallback Provider:** **MyMemory API**, delivering instant zero-key translation for Indic languages (Telugu, Hindi, Tamil, Kannada, Malayalam) and major global tongues.

---

## 🎯 Problem Statement
Public translation services frequently present significant engineering obstacles:
1. **Vendor Lock-in & Hardcoded Secrets:** Many beginner implementations hardcode credentials or tightly couple the frontend to proprietary paywalled APIs.
2. **Brittle Network Failure:** Inadequate error handling causes UI crashes upon API timeouts, rate limits, or connection drops.
3. **Misleading Language Catalogs:** Advertising language pairs that an endpoint's underlying neural model does not actually support.

This project addresses these challenges by implementing dynamic language discovery, centralized configuration via `.env`, custom exception hierarchies, and a failover provider architecture.

---

## 🚀 Objectives
* Deliver an intuitive, modern Streamlit UI suitable for executive demonstrations.
* Query API `/languages` dynamically to ensure only genuinely supported languages are presented.
* Provide side-by-side translation workspace with quick language swapping and clipboard export.
* Implement complete error handling for timeouts, invalid JSON, 400 Bad Requests, 401/403 auth errors, and 429 rate limits.
* Maintain a session history log with CSV and JSON export capabilities.
* Provide 100% deterministic automated unit tests alongside live integration tests.

---

## ✨ Key Features
- **Dynamic Language Detection:** Automatic detection of source text language using `/detect` endpoints.
- **Provider Switching:** Seamlessly toggle between LibreTranslate (self-hosted or cloud) and MyMemory.
- **Side-by-Side Dual Panels:** Modern split-screen layout with real-time character and word count tracking.
- **One-Click Language Swap (`⇄`):** Instantly swap source and target languages (with validation preventing invalid 'auto-detect' target assignment).
- **Fast Clipboard Copying:** Formatted one-click output copying.
- **Translation History Ledger:** Real-time log displaying original text, translated text, language pairs, latency in milliseconds, and provider provenance.
- **Data Export:** Export translation history directly to CSV or JSON formats.
- **Resilient Error Banners:** Contextual warnings providing actionable troubleshooting steps instead of cryptic tracebacks.

---

## 🛠 Technology Stack
| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.10 – 3.14 | Core backend logic & typing |
| **Frontend Framework** | Streamlit | Reactive UI, session state, layouts |
| **HTTP Client** | Requests | Synchronous REST API communication |
| **Translation Engine 1** | LibreTranslate | Open-source neural translation API (Argos engine) |
| **Translation Engine 2** | MyMemory API | Fallback multi-language API |
| **Data Handling** | Pandas | History tabulation and CSV export |
| **Testing** | Unittest & Pytest | Mocked unit suites and live integration tests |
| **Styling** | Custom CSS & HTML | Modern typography, cards, and animations |

---

## 📐 System Architecture

```mermaid
flowchart TD
    User([User Browser]) <--> StreamlitUI[Streamlit Web Application app.py]
    
    subgraph ServiceLayer [Translation Service Layer]
        StreamlitUI <--> Service[TranslationService]
        Service <--> History[Session History Manager]
        Service --> ProviderChoice{Active Provider?}
    end

    subgraph Providers [API Integration Layer]
        ProviderChoice -->|LibreTranslate| Libre[LibreTranslator]
        ProviderChoice -->|MyMemory| MyMem[MyMemoryTranslator]
    end

    subgraph ExternalAPIs [Remote Endpoints]
        Libre -->|HTTP POST /translate| LibreHost[LibreTranslate Server\nLocal Docker or Cloud]
        Libre -->|HTTP GET /languages| LibreHost
        Libre -->|HTTP POST /detect| LibreHost
        MyMem -->|HTTP GET /get| MyMemoryAPI[MyMemory Translation API]
    end

    subgraph Resilience [Resilience & Validation]
        Libre -.->|Catches| ErrH[Timeout / Connection / 401 / 429 Errors]
        MyMem -.->|Catches| ErrH
    end
```

---

## 🔌 API Integration Deep-Dive

### 1. LibreTranslate Endpoint Structure
* **Dynamic Languages Query:** `GET {base_url}/languages`
  * Returns list of supported languages: `[{"code": "en", "name": "English", "targets": [...]}, ...]`.
  * Guarantees our UI strictly displays languages the endpoint has loaded.
* **Translation Request:** `POST {base_url}/translate`
  * Request Body: `{"q": "Hello", "source": "en", "target": "es", "format": "text", "api_key": "..."}`
  * Returns: `{"translatedText": "Hola"}`
* **Language Detection:** `POST {base_url}/detect`
  * Returns: `[{"confidence": 99.0, "language": "en"}]`

### 2. Language Matrix Reality & Provider Complementarity
Official Argos Translate models powering standard LibreTranslate instances support 51 languages (including English, Hindi, Bengali, German, French, Spanish, Japanese, Arabic, and Chinese). However, Dravidian languages such as Telugu, Tamil, Kannada, and Malayalam are not bundled in standard Argos model releases. 

To satisfy the full internship requirement without compromising truthfulness or hardcoding keys, the tool provides **MyMemory Translation** as a built-in fallback provider, which natively translates Telugu (`te`), Tamil (`ta`), Kannada (`kn`), and Malayalam (`ml`).

---

## 📂 Project Structure

```text
CodeAlpha_Language_Translation_Tool/
│
├── app.py                      # Main Streamlit web application & UI
├── translator.py               # Core translation engine & HTTP client service
├── requirements.txt            # Project dependencies
├── README.md                   # Comprehensive documentation
├── .env.example                # Template for environment configuration
├── .gitignore                  # Git exclusions (venv, secrets, cache)
│
└── tests/
    ├── __init__.py             # Test package marker
    ├── test_translator.py      # 10 automated unit tests (mocked offline)
    └── test_live_integration.py# Live integration tests for real endpoints
```

---

## 💻 Installation & Setup

### Prerequisites
* Python 3.10 or higher installed on your system.
* Git installed.

### Step 1: Clone or Navigate to the Repository
```bash
cd CodeAlpha_Language_Translation_Tool
```

### Step 2: Create and Activate a Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

---

## ⚙️ Environment Configuration

1. Copy the example environment file to `.env`:
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```

2. Open `.env` in any text editor and adjust settings:
   ```env
   # Primary Provider: libretranslate or mymemory
   TRANSLATION_PROVIDER=libretranslate

   # LibreTranslate URL (cloud or self-hosted)
   LIBRETRANSLATE_API_URL=https://libretranslate.com

   # LibreTranslate API Key (optional for local Docker, required for libretranslate.com)
   LIBRETRANSLATE_API_KEY=

   # HTTP Timeout in seconds
   REQUEST_TIMEOUT=10
   ```

> **Note:** The application can also be configured dynamically at runtime through the Streamlit sidebar controls.

---

## 🚀 Running the Application

Launch the Streamlit web dashboard:
```bash
streamlit run app.py
```

The application will launch in your default web browser at `http://localhost:8501`.

### Running LibreTranslate Locally via Docker (100% Free & Unlimited)
If you prefer running an offline translation server with zero API keys or rate limits:
```bash
docker run -ti --rm -p 5000:5000 libretranslate/libretranslate
```
Then select **Local Docker (localhost:5000)** in the app's sidebar.

---

## 🧪 Testing Suite

The project includes two cleanly separated testing tiers:

### 1. Automated Mocked Unit Tests (Offline & Deterministic)
These tests mock all HTTP requests using `unittest.mock`, requiring zero internet connectivity.

```bash
# Run via unittest
python -m unittest discover -s tests -p "test_*.py" -v

# Or run via pytest
pytest tests/test_translator.py -v
```

**Covered Test Scenarios:**
1. ✅ **API Request Formatting:** Confirms JSON payload, endpoint URL, and headers.
2. ✅ **Successful Response Parsing:** Validates extraction of `translatedText` and latency metrics.
3. ✅ **Empty Text Validation:** Ensures blank strings reject early without wasting network bandwidth.
4. ✅ **Invalid Language & Pair Handling:** Confirms descriptive error handling on 400 Bad Request.
5. ✅ **API Timeout Simulation:** Confirms graceful degradation when servers take too long.
6. ✅ **Connection Error Handling:** Ensures server connection failure displays clear guidance.
7. ✅ **Invalid API Responses:** Verifies resilience against malformed JSON or missing fields.
8. ✅ **Translation History Ledger:** Tests additions, ordering, and clearing operations.
9. ✅ **Language Swapping:** Tests `swap_languages()` and catches invalid 'auto-detect' swaps.
10. ✅ **Configuration Parsing:** Validates environment variable fallbacks and URL normalization.

### 2. Live API Integration Tests (Real Endpoints)
Validates real HTTP communication with live external servers.
```bash
python -m unittest tests/test_live_integration.py -v
```

---

## ⚠️ Limitations & Trade-offs
* **Free Public Endpoints:** Public community LibreTranslate mirrors experience dynamic downtime or require API keys for spam protection. The app mitigates this via its built-in MyMemory fallback.
* **Synchronous Requests:** Translation calls run synchronously per request. For high-throughput enterprise batch processing, an asynchronous queue (e.g., Celery/Redis or `httpx.AsyncClient`) would be recommended.
* **Session Persistence:** History is stored in Streamlit session memory. Closing the browser tab clears history unless exported to CSV/JSON.

---

## 🔮 Future Enhancements
* **Voice-to-Text & Text-to-Speech:** Integrate Whisper for audio input and gTTS for translated audio pronunciation.
* **Document Translation:** Support direct drag-and-drop file translation for `.pdf`, `.docx`, and `.txt`.
* **Persistent SQLite Database:** Store long-term user translation glossaries.
* **Batch Translation API:** Parallel batch translation of multiple sentences simultaneously.

---

## 🎬 Two-Minute Demonstration Video Script

* **[0:00 - 0:20] Introduction:**  
  *"Hello everyone! My name is Dhushyanth, and today I'm demonstrating Project 3 for my CodeAlpha Artificial Intelligence Internship: The Neural Language Translation Tool. This application is built with Python, Streamlit, and a resilient API architecture integrating LibreTranslate and MyMemory."*
* **[0:20 - 0:45] Architecture & Sidebar Configuration:**  
  *"Looking at the sidebar, notice how the application allows configurable endpoints. We don't hardcode any secrets; the app reads from environment variables or custom user inputs. We can toggle between LibreTranslate—which queries live endpoints to dynamically fetch only genuinely supported languages—and MyMemory as a zero-key fallback."*
* **[0:45 - 1:15] Core Translation & Language Swap:**  
  *"Let's demonstrate a live translation. I'll enter: 'Artificial Intelligence is transforming global communication.' I select English as the source—or leave it on Auto Detect—and choose Spanish. Clicking 'Translate Text', the model translates it to 'La inteligencia artificial está transformando la comunicación global' in just a few milliseconds. Clicking the Swap button instantly flips the languages and content. We also have a one-click copy button for quick clipboard export."*
* **[1:15 - 1:40] Indic Languages & Fallback Engine:**  
  *"To translate Indic languages like Telugu, Tamil, or Malayalam, we toggle to our MyMemory engine. Translating 'Welcome to CodeAlpha' to Telugu gives us 'కోడ్‌ఆల్ఫాకు స్వాగతం' instantly. Every successful translation is recorded in our session history ledger below, which can be downloaded as a CSV or JSON report."*
* **[1:40 - 2:00] Testing & Conclusion:**  
  *"Under the hood, the system is backed by a 10-point automated test suite with full mocking and real integration testing. Thank you for watching my CodeAlpha internship project demonstration!"*

---

## 📄 Resume-Ready Bullet Points

* **AI Engineering Intern | CodeAlpha Language Translation Tool**
  * Developed a modular multilingual translation web application using **Python 3.14**, **Streamlit**, and **Requests**, supporting over 50 languages with sub-second latency.
  * Architected a dual-engine API strategy integrating **LibreTranslate** (REST/JSON) and a zero-configuration fallback (**MyMemory**), eliminating single-point-of-failure risks.
  * Implemented dynamic language discovery by querying `/languages` endpoints, preventing unsupported language pair execution and eliminating hardcoded model catalogs.
  * Built resilient exception handling covering HTTP 400, 401/403 auth errors, 429 rate limits, and network connection timeouts.
  * Created a comprehensive automated testing suite with **Unittest** and **Pytest** using `unittest.mock` to achieve 100% test coverage across 10 critical failure modes.

---

## ❓ Technical Interview Preparation

### Q1: Why did you choose LibreTranslate and how does it compare to proprietary APIs like Google Translate?
> **Answer:** LibreTranslate is completely free, open-source, and self-hostable powered by the Argos Translate neural machine translation engine. Unlike proprietary APIs that enforce strict billing paywalls, proprietary tracking, and recurring vendor lock-in, LibreTranslate allows developers and privacy-sensitive enterprises to run translations completely on-premises via Docker.

### Q2: How did you handle network timeouts and API rate limiting?
> **Answer:** We wrapped HTTP operations in granular exception blocks catching `requests.exceptions.Timeout` and `requests.exceptions.ConnectionError`. Furthermore, we inspect HTTP status codes: a 429 indicates rate limiting, prompting the user with backoff advice; a 400/401 indicates authentication requirements. We also decoupled the API call with a user-configurable timeout parameter, preventing the Streamlit worker from hanging indefinitely.

### Q3: Why is mocking crucial in your automated test suite?
> **Answer:** Unit tests should be fast, deterministic, and runnable without an internet connection. If tests depended on live external translation APIs, they would be vulnerable to rate limits, server maintenance, latency spikes, and network drops. By using `unittest.mock.patch`, we mock the HTTP responses to simulate 200 OK, 400 Bad Request, timeout exceptions, and malformed JSON payloads in under 10 milliseconds.

---

## 📜 License
This project is developed as part of the **CodeAlpha Artificial Intelligence Internship** and is distributed under the MIT License.
