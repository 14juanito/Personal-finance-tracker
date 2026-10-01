def test_corrupted_json_is_backed_up(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    path.write_text('{"transactions": [ {"date": ', encoding="utf-8")

    state = storage.load_json(path)

    assert state.transactions == []
    assert "corrupted" in state.warnings[0]
    assert not path.exists()
    backups = list(tmp_path.glob("data.json.corrupted-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8").startswith('{"transactions"')
