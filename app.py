"""
CodeAlpha Language Translation Tool - Streamlit Web Application
================================================================
Application: app.py
Author: CodeAlpha AI Intern
Description:
    A modern, professional language translation web application built with Streamlit
    and Python. Integrates with LibreTranslate (primary configurable endpoint) and
    MyMemory (free fallback provider supporting Indic languages).
"""

from __future__ import annotations

import json
import os
import time
from typing import List, Tuple
import pandas as pd
import streamlit as st

from translator import (
    Language,
    LibreTranslator,
    TranslationResult,
    TranslationService,
)

# ------------------------------------------------------------------------------
# Page Configuration & Metadata
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="CodeAlpha Language Translation Tool",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------------------
# Modern Custom CSS Styling
# ------------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
    /* Font and General Layout */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main Container Padding */
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    /* Header Banner Styling */
    .header-banner {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border-radius: 12px;
        padding: 24px 30px;
        margin-bottom: 24px;
        color: #F8FAFC;
        border: 1px solid #334155;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
    }
    
    .header-title {
        font-size: 1.85rem;
        font-weight: 700;
        margin-bottom: 6px;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .header-subtitle {
        font-size: 0.95rem;
        color: #94A3B8;
        margin: 0;
    }

    .badge-internship {
        display: inline-block;
        background: rgba(59, 130, 246, 0.2);
        color: #60A5FA;
        border: 1px solid rgba(59, 130, 246, 0.4);
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
    }

    /* Panel Cards */
    .translation-panel {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }

    /* Status Pill */
    .status-pill-ok {
        background-color: #DCFCE7;
        color: #166534;
        border: 1px solid #86EFAC;
        padding: 4px 10px;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .status-pill-warn {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FCD34D;
        padding: 4px 10px;
        border-radius: 16px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Metadata Info Bar */
    .metadata-bar {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px 14px;
        margin-top: 10px;
        font-size: 0.85rem;
        color: #475569;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
    }

    /* Output Card */
    .output-box {
        background-color: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 16px;
        min-height: 180px;
        font-size: 1.05rem;
        line-height: 1.6;
        color: #0F172A;
        white-space: pre-wrap;
        word-break: break-word;
    }

    .output-placeholder {
        color: #94A3B8;
        font-style: italic;
    }

    /* Footer */
    .footer-container {
        text-align: center;
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #E2E8F0;
        color: #64748B;
        font-size: 0.85rem;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Session State Initialization
# ------------------------------------------------------------------------------
if "service" not in st.session_state:
    st.session_state.service = TranslationService()

if "source_text_val" not in st.session_state:
    st.session_state.source_text_val = "Welcome to the CodeAlpha AI Internship Language Translation Tool!"

if "translated_result" not in st.session_state:
    st.session_state.translated_result = None

if "source_lang_code" not in st.session_state:
    st.session_state.source_lang_code = "en"

if "target_lang_code" not in st.session_state:
    st.session_state.target_lang_code = "es"

service: TranslationService = st.session_state.service

# ------------------------------------------------------------------------------
# Sidebar: Provider & Connection Configuration
# ------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ API Configuration")
    st.caption("Configure translation endpoints, credentials, and parameters.")

    provider_choice = st.selectbox(
        "Translation Provider",
        options=["LibreTranslate", "MyMemory (Free Fallback)"],
        index=0 if service.provider_name == "libretranslate" else 1,
        help=(
            "LibreTranslate: Primary provider (configurable self-hosted or official cloud).\n"
            "MyMemory: Free open API supporting Telugu, Tamil, Kannada, Malayalam, etc. without API key."
        ),
    )

    is_libre = provider_choice == "LibreTranslate"
    service.set_provider("libretranslate" if is_libre else "mymemory")

    if is_libre:
        st.markdown("---")
        st.markdown("##### 🔌 LibreTranslate Connection")

        # Preset Endpoints
        endpoint_preset = st.radio(
            "Endpoint Preset",
            options=["Official Cloud (libretranslate.com)", "Local Docker (localhost:5000)", "Custom Endpoint"],
            index=0,
            horizontal=False
        )

        default_url = "https://libretranslate.com"
        if endpoint_preset == "Local Docker (localhost:5000)":
            default_url = "http://localhost:5000"
        elif endpoint_preset == "Official Cloud (libretranslate.com)":
            default_url = "https://libretranslate.com"

        api_url = st.text_input(
            "Endpoint URL",
            value=default_url,
            help="Base URL of the LibreTranslate instance."
        )

        api_key = st.text_input(
            "API Key (Optional / If required)",
            value=os.getenv("LIBRETRANSLATE_API_KEY", ""),
            type="password",
            help="Required for hosted libretranslate.com. Not needed for local Docker instance."
        )

        timeout_val = st.slider(
            "Request Timeout (seconds)",
            min_value=3,
            max_value=30,
            value=int(service.libre_client.timeout),
            step=1
        )

        service.update_libre_config(base_url=api_url, api_key=api_key, timeout=timeout_val)

        # Connection Probe Button
        if st.button("🔍 Probe Endpoint Health", use_container_width=True):
            with st.spinner("Checking endpoint..."):
                start_p = time.perf_counter()
                try:
                    langs = service.libre_client.get_languages(force_refresh=True)
                    latency = round((time.perf_counter() - start_p) * 1000.0, 1)
                    st.success(f"Connected! {len(langs)} languages available ({latency}ms).")
                except Exception as e:
                    st.error(f"Endpoint unreachable: {str(e)}")

        with st.expander("🐳 How to Run Free Offline LibreTranslate"):
            st.markdown(
                """
                **Run 100% Free Locally with Docker:**
                ```bash
                docker run -ti --rm -p 5000:5000 libretranslate/libretranslate
                ```
                Then set the endpoint above to `http://localhost:5000`. No API keys or rate limits!
                """
            )
    else:
        st.markdown("---")
        st.markdown("##### 🌐 MyMemory Settings")
        st.info(
            "MyMemory provides free, unauthenticated access with 100+ language support "
            "including Telugu, Tamil, Kannada, Malayalam, Hindi, and European languages."
        )
        my_email = st.text_input(
            "Optional User Email",
            value=os.getenv("MYMEMORY_USER_EMAIL", ""),
            help="Providing an email raises the free quota from 50k to 500k chars/day."
        )
        service.mymemory_client.email = my_email

    st.markdown("---")
    st.markdown("##### 📊 Session Summary")
    st.metric("Total Translations", len(service.history))

# ------------------------------------------------------------------------------
# Main Header Banner
# ------------------------------------------------------------------------------
st.markdown(
    """
    <div class="header-banner">
        <span class="badge-internship">CodeAlpha Artificial Intelligence Internship • Project 3</span>
        <div class="header-title">
            <span>🌐</span> Neural Language Translation Tool
        </div>
        <p class="header-subtitle">
            Enterprise-ready multilingual translation system with configurable API endpoints,
            automatic language detection, and session history tracking.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------------------
# Fetch Provider Supported Languages
# ------------------------------------------------------------------------------
try:
    available_languages: List[Language] = service.get_supported_languages()
except Exception:
    available_languages = service.libre_client.FALLBACK_LANGUAGES

# Build lookup dictionaries
lang_dict = {lang.code: lang.name for lang in available_languages}
sorted_lang_codes = sorted(lang_dict.keys(), key=lambda c: lang_dict[c].lower())

# Source languages include 'auto' (Auto-detect)
source_options = ["auto"] + sorted_lang_codes
source_format = lambda c: "✨ Auto Detect" if c == "auto" else f"{lang_dict.get(c, c)} ({c})"
target_format = lambda c: f"{lang_dict.get(c, c)} ({c})"

# Safe indices
if st.session_state.source_lang_code not in source_options:
    st.session_state.source_lang_code = "auto"
if st.session_state.target_lang_code not in sorted_lang_codes:
    st.session_state.target_lang_code = sorted_lang_codes[0] if sorted_lang_codes else "es"

source_idx = source_options.index(st.session_state.source_lang_code)
target_idx = sorted_lang_codes.index(st.session_state.target_lang_code)

# ------------------------------------------------------------------------------
# Controls & Language Selection Bar
# ------------------------------------------------------------------------------
col_src_select, col_swap, col_tgt_select = st.columns([5, 1, 5], vertical_alignment="bottom")

with col_src_select:
    selected_source = st.selectbox(
        "Source Language",
        options=source_options,
        index=source_idx,
        format_func=source_format,
        key="source_lang_selector"
    )
    st.session_state.source_lang_code = selected_source

with col_swap:
    if st.button("⇄", help="Swap Source and Target Languages", use_container_width=True):
        new_src, new_tgt, warning = TranslationService.swap_languages(
            st.session_state.source_lang_code,
            st.session_state.target_lang_code
        )
        if warning:
            st.toast(f"⚠️ {warning}", icon="⚠️")
        else:
            st.session_state.source_lang_code = new_src
            st.session_state.target_lang_code = new_tgt
            # Also swap text if both exist
            if st.session_state.translated_result and st.session_state.translated_result.success:
                st.session_state.source_text_val = st.session_state.translated_result.translated_text
            st.rerun()

with col_tgt_select:
    selected_target = st.selectbox(
        "Target Language",
        options=sorted_lang_codes,
        index=target_idx,
        format_func=target_format,
        key="target_lang_selector"
    )
    st.session_state.target_lang_code = selected_target

# ------------------------------------------------------------------------------
# Side-by-Side Translation Panels
# ------------------------------------------------------------------------------
col_input, col_output = st.columns(2, gap="large")

with col_input:
    st.markdown("##### 📝 Source Text")
    input_text = st.text_area(
        label="Source Text Input",
        value=st.session_state.source_text_val,
        height=220,
        placeholder="Type, paste, or load sample text here to translate...",
        label_visibility="collapsed",
        key="source_text_area",
    )
    st.session_state.source_text_val = input_text

    # Character and word metrics
    char_count = len(input_text)
    word_count = len(input_text.split()) if input_text.strip() else 0
    st.caption(f"📊 Words: **{word_count}** | Characters: **{char_count}**")

with col_output:
    st.markdown("##### 🎯 Translated Text")
    
    # Display translated text card
    result_obj: TranslationResult | None = st.session_state.translated_result
    
    if result_obj and result_obj.success:
        st.markdown(
            f'<div class="output-box">{html.escape(result_obj.translated_text)}</div>',
            unsafe_allow_html=True
        )
        # Metadata bar
        st.markdown(
            f"""
            <div class="metadata-bar">
                <span>⚡ Latency: <b>{result_obj.response_time_ms} ms</b></span>
                <span>⚙️ Provider: <b>{result_obj.provider}</b></span>
                {f'<span>🔍 Detected: <b>{result_obj.detected_language}</b></span>' if result_obj.detected_language else ''}
            </div>
            """,
            unsafe_allow_html=True
        )
    elif result_obj and not result_obj.success:
        st.error(result_obj.error_message)
        if "Authentication Required" in (result_obj.error_message or ""):
            st.info(
                "💡 **Quick Fix:** Switch provider to **MyMemory (Free Fallback)** in the sidebar "
                "to translate instantly with zero keys, or provide a LibreTranslate API key."
            )
    else:
        st.markdown(
            '<div class="output-box output-placeholder">Translation will appear here after clicking "Translate Text"...</div>',
            unsafe_allow_html=True
        )

# ------------------------------------------------------------------------------
# Action Buttons Bar
# ------------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([3, 2, 2, 2])

with col_btn1:
    translate_clicked = st.button("🚀 Translate Text", type="primary", use_container_width=True)

with col_btn2:
    if st.button("📋 Copy Translation", use_container_width=True):
        if result_obj and result_obj.success and result_obj.translated_text:
            st.code(result_obj.translated_text, language="")
            st.toast("✅ Translation copied above for easy selection!", icon="📋")
        else:
            st.toast("⚠️ No translated text available to copy.", icon="⚠️")

with col_btn3:
    if st.button("🗑 Clear All", use_container_width=True):
        st.session_state.source_text_val = ""
        st.session_state.translated_result = None
        st.rerun()

with col_btn4:
    if st.button("💡 Load Sample", use_container_width=True):
        st.session_state.source_text_val = (
            "Artificial Intelligence is advancing rapidly, empowering global communication "
            "across cultural and linguistic boundaries."
        )
        st.rerun()

# ------------------------------------------------------------------------------
# Translation Execution Logic
# ------------------------------------------------------------------------------
if translate_clicked:
    if not input_text or not input_text.strip():
        st.warning("⚠️ Please enter text to translate.")
    else:
        with st.spinner("Translating text across neural language models..."):
            res = service.translate(
                text=input_text,
                source=st.session_state.source_lang_code,
                target=st.session_state.target_lang_code
            )
            st.session_state.translated_result = res
            st.rerun()

# ------------------------------------------------------------------------------
# Translation History Section
# ------------------------------------------------------------------------------
st.markdown("---")
with st.expander(f"📜 Translation History ({len(service.history)} records)", expanded=False):
    if not service.history:
        st.caption("No translations recorded yet during this session.")
    else:
        col_hist_action1, col_hist_action2 = st.columns([2, 8])
        with col_hist_action1:
            if st.button("🧹 Clear History", key="btn_clear_history"):
                service.clear_history()
                st.rerun()

        history_data = [
            {
                "Time": item.timestamp,
                "Provider": item.provider,
                "Pair": f"{item.source_language.upper()} ➔ {item.target_language.upper()}",
                "Original Text": item.original_text,
                "Translated Text": item.translated_text,
                "Latency (ms)": item.response_time_ms,
            }
            for item in service.history
        ]

        df_history = pd.DataFrame(history_data)
        st.dataframe(df_history, use_container_width=True, hide_index=True)

        # Download Buttons
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            csv_data = df_history.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download History as CSV",
                data=csv_data,
                file_name="translation_history.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_dl2:
            json_data = json.dumps(history_data, indent=2, ensure_ascii=False).encode("utf-8")
            st.download_button(
                label="📥 Download History as JSON",
                data=json_data,
                file_name="translation_history.json",
                mime="application/json",
                use_container_width=True
            )

# ------------------------------------------------------------------------------
# Supported Language Matrix & Verification Info
# ------------------------------------------------------------------------------
with st.expander("ℹ️ Active Provider & Language Matrix Verification", expanded=False):
    st.markdown(
        f"""
        **Active Provider:** `{service.provider_name.title()}`  
        **Endpoint:** `{service.libre_client.base_url if is_libre else service.mymemory_client.base_url}`  
        **Total Verified Supported Languages:** `{len(available_languages)}`
        """
    )
    
    # Display language tags in multi-column layout
    cols_matrix = st.columns(4)
    for i, lang in enumerate(available_languages):
        col_idx = i % 4
        cols_matrix[col_idx].write(f"• **{lang.name}** (`{lang.code}`)")

# ------------------------------------------------------------------------------
# Footer
# ------------------------------------------------------------------------------
st.markdown(
    """
    <div class="footer-container">
        <b>CodeAlpha Artificial Intelligence Internship</b> • Project 3: Language Translation Tool<br>
        Developed with Python, Streamlit, Requests, and LibreTranslate API Architecture.
    </div>
    """,
    unsafe_allow_html=True,
)
