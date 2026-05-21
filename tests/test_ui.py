"""Tests for Streamlit UI module."""

from __future__ import annotations

import warnings

import europulse.config as config


def test_app_imports_without_streamlit_runtime():
    original_db_path = getattr(config, "DB_PATH", None)
    try:
        config.DB_PATH = "/nonexistent/db.duckdb"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import importlib
            import europulse.ui.app as app_module

            importlib.reload(app_module)
            assert hasattr(app_module, "load_data")
    finally:
        if original_db_path is not None:
            config.DB_PATH = original_db_path
