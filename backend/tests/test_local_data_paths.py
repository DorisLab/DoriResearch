"""Filesystem identity checks, including Windows package path virtualization."""

from pathlib import Path

import pytest
from test_local_data import fixture, query

from dorislab_research.local_data import read_data


def test_same_directory_with_different_resolved_spelling_is_readable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog, obj = fixture(tmp_path)
    hop = tmp_path / "alias-hop"
    hop.mkdir()
    aliased = hop / ".." / obj.name
    assert aliased.parent != tmp_path.resolve()
    assert aliased.parent.samefile(tmp_path)
    resolve = Path.resolve
    monkeypatch.setattr(
        Path, "resolve", lambda self, *a, **kw: aliased if self == obj else resolve(self, *a, **kw)
    )
    rows, proof = read_data(catalog, query())
    assert rows == [{"date": "2025-01-02", "value": None}, {"date": "2025-01-03", "value": 12}]
    assert proof["row_count"] == 2


def test_resolved_parent_in_another_directory_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog, obj = fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    resolve = Path.resolve
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda self, *a, **kw: outside / obj.name if self == obj else resolve(self, *a, **kw),
    )
    with pytest.raises(ValueError, match="linked or escapes"):
        read_data(catalog, query())


@pytest.mark.parametrize("link_check", ["is_symlink", "is_junction"])
def test_linked_object_is_rejected_even_when_parent_identity_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link_check: str
) -> None:
    catalog, obj = fixture(tmp_path)
    original = getattr(Path, link_check)
    monkeypatch.setattr(Path, link_check, lambda self: self == obj or original(self))
    with pytest.raises(ValueError, match="linked or escapes"):
        read_data(catalog, query())
