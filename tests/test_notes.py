import os
import pytest
from docs_search_mcp.notes import Notes, NotesError


@pytest.fixture
def notes(tmp_path):
    (tmp_path / "a.md").write_text("# Alpha\n\n## Cats\nCats purr and sleep a lot.\n\n## Dogs\nDogs bark loudly.\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_text("Fish swim. Cats chase fish.")
    (tmp_path / "ignore.py").write_text("cats = 1")
    return Notes(tmp_path)


def test_lists_only_allowed_files(notes):
    assert [n["path"] for n in notes.list_notes()] == ["a.md", "sub/b.txt"]


def test_search_ranks_relevant_section_first(notes):
    r = notes.search("dogs bark")
    assert r[0]["path"] == "a.md" and r[0]["heading"] == "Dogs"
    assert "bark" in r[0]["snippet"]


def test_search_no_match_and_empty_query(notes):
    assert notes.search("zebra") == []
    with pytest.raises(NotesError):
        notes.search("   ")


def test_limit_is_clamped(notes):
    assert len(notes.search("cats", limit=1)) == 1
    assert len(notes.search("cats", limit=-5)) == 1


def test_read_ok_and_truncation(notes):
    assert "Dogs bark" in notes.read("a.md")["content"]
    r = notes.read("a.md", max_chars=5)
    assert r["truncated"] and len(r["content"]) == 5


@pytest.mark.parametrize("bad", ["../etc/passwd", "/etc/passwd", "sub/../../x.md", "ignore.py", "missing.md", ""])
def test_read_rejects_bad_paths(notes, bad):
    with pytest.raises(NotesError):
        notes.read(bad)


def test_symlink_escape_blocked(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("top secret")
    root = tmp_path / "root"
    root.mkdir()
    try:
        os.symlink(outside / "secret.md", root / "link.md")
    except OSError:
        pytest.skip("symlinks unavailable")
    n = Notes(root)
    assert n.list_notes() == []          # symlinks are not indexed
    with pytest.raises(NotesError):
        n.read("link.md")                 # nor readable


def test_missing_root():
    with pytest.raises(NotesError):
        Notes("/definitely/not/here")
