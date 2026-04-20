# -- Chart Label Formatters --
# Pure formatting functions for consistent price, percentage, and name
# rendering across all analysis charts. Locale-aware for Turkish Lira.

def format_price(value: float) -> str:
    # Format a numeric value as a Turkish Lira price string with thousands separators
    return f"₺{value:,.0f}"

def format_pct(value: float, decimals: int = 1) -> str:
    # Format a numeric value as a signed percentage string (e.g. "+5.2%", "-3.1%")
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"

def shorten_name(name: str, max_len: int = 20) -> str:
    # Truncate long product names with an ellipsis for chart label readability
    if len(name) <= max_len:
        return name
    return name[: max_len - 1] + "…"
