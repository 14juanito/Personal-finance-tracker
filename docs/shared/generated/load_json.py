def load_json(path: Path | str, recover: bool = True) -> AppState:
    path = Path(path)
    state = AppState()
    if not path.exists():
        state.warnings.append(f"No data file at '{path}' — starting with empty data.")
        return state

    # Concept: exception handling — recover from a corrupted JSON file
    try:
        # Concept: file handling — `with` closes the file even if json.load fails
        with path.open("r", encoding=ENCODING) as handle:
            payload = json.load(handle)
        _check_structure(payload)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        if not recover:
            raise StorageError(f"Corrupted JSON file '{path}': {exc}") from exc
        backup = _backup_corrupted(path)
        state.warnings.append(
            f"'{path.name}' was corrupted ({exc}); a backup was saved as '{backup.name}'."
        )
    except OSError as exc:
        raise StorageError(f"Could not read '{path}': {exc.strerror or exc}") from exc
    else:
        # `else` runs only when the file was read and parsed without error.
        _fill_state(state, payload)
    return state
