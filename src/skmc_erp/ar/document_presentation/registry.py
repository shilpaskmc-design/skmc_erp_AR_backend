SUPPORTED_BILLING_TEMPLATE_KEYS = frozenset(
    {
        "COMPACT_V1",
        "MODERN_V1",
        "STANDARD_V1",
    }
)


def is_supported_billing_template(template_key: str) -> bool:
    return template_key in SUPPORTED_BILLING_TEMPLATE_KEYS
