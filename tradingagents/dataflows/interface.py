"""Vendor abstraction layer for data sources.

Routes data requests to appropriate vendor implementations with fallback support.
"""

import os
from typing import Callable

# Vendor registry: {method_name: {vendor_name: implementation_func}}
_VENDOR_METHODS: dict[str, dict[str, Callable]] = {}

# Category -> vendor mapping (configurable)
_VENDOR_CONFIG: dict[str, str] = {
    "core_stock_apis": "yfinance",
    "technical_indicators": "yfinance",
    "fundamental_data": "yfinance",
    "news_data": "yfinance",
}

# Method -> category mapping
_METHOD_CATEGORIES: dict[str, str] = {}


def register_vendor(method: str, vendor: str, category: str):
    """Decorator to register a vendor implementation for a method."""

    def decorator(func: Callable) -> Callable:
        if method not in _VENDOR_METHODS:
            _VENDOR_METHODS[method] = {}
        _VENDOR_METHODS[method][vendor] = func
        _METHOD_CATEGORIES[method] = category
        return func

    return decorator


def get_vendor(category: str, method: str) -> str:
    """Get the configured vendor for a category or method."""
    # Method-level override takes precedence
    env_key = f"TRADINGAGENTS_VENDOR_{method.upper()}"
    if env_key in os.environ:
        return os.environ[env_key]
    return _VENDOR_CONFIG.get(category, "yfinance")


def route_to_vendor(method: str, *args, **kwargs):
    """Route a method call to the appropriate vendor implementation with fallback."""
    if method not in _VENDOR_METHODS:
        raise ValueError(f"Unknown method: {method}")

    category = _METHOD_CATEGORIES.get(method, "core_stock_apis")
    primary_vendor = get_vendor(category, method)

    # Build fallback chain: primary first, then remaining vendors
    available = list(_VENDOR_METHODS[method].keys())
    fallback_chain = [primary_vendor] + [v for v in available if v != primary_vendor]

    last_error = None
    for vendor in fallback_chain:
        impl = _VENDOR_METHODS[method].get(vendor)
        if impl is None:
            continue
        try:
            return impl(*args, **kwargs)
        except Exception as e:
            last_error = e
            if "429" in str(e) or "rate limit" in str(e).lower():
                continue  # Rate limit -> try next vendor
            raise  # Other errors -> propagate

    raise RuntimeError(f"All vendors failed for {method}. Last error: {last_error}")


def set_vendor_config(config: dict[str, str]):
    """Update vendor configuration."""
    _VENDOR_CONFIG.update(config)
