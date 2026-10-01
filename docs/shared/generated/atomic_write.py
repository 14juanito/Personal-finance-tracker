def _atomic_write(path: Path, write_func: Any, newline: str | None = None) -> None:
    path = Path(path)
    tmp_name: str | None = None
    # Concept: exception handling — try/except/finally guarantees cleanup of the temp file
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding=ENCODING, newline=newline) as handle:
            write_func(handle)
        # replace() is atomic on the same filesystem: readers see the old or new file,
        # never a partial one.
        Path(tmp_name).replace(path)
        tmp_name = None
    except OSError as exc:
        raise StorageError(f"Could not write '{path}': {exc.strerror or exc}") from exc
    finally:
        if tmp_name is not None:
            Path(tmp_name).unlink(missing_ok=True)
