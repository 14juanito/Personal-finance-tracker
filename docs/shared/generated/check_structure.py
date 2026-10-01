def _check_structure(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("top-level JSON value must be an object")
    for section in SECTIONS:
        if not isinstance(payload.get(section, []), list):
            raise ValueError(f"'{section}' must be a list")
