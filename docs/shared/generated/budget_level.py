def budget_level(ratio: float) -> str:
    # Concept: decision structure — thresholds are tested from most to least severe
    if ratio >= EXCEEDED_THRESHOLD:
        return LEVEL_EXCEEDED
    elif ratio >= WARNING_THRESHOLD:
        return LEVEL_WARNING
    else:
        return LEVEL_OK
