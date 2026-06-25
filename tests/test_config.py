"""Project root and settings defaults."""

from __future__ import annotations

import benson.config as cfg
from benson.config import Settings


def test_project_root_source_layout(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("SCHEMA_ROOT", raising=False)
    repo = tmp_path / "repo"
    (repo / "assets" / "schemas").mkdir(parents=True)
    cfg_file = repo / "src" / "benson" / "config.py"
    cfg_file.parent.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cfg, "__file__", str(cfg_file))

    assert cfg.project_root() == repo.resolve()
    settings = Settings.from_env()
    assert settings.schema_root == (repo / "assets" / "schemas").resolve()


def test_project_root_from_workdir(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("SCHEMA_ROOT", raising=False)
    monkeypatch.delenv("SEARCHABLES_CACHE_DIR", raising=False)
    (tmp_path / "assets" / "schemas").mkdir(parents=True)
    fake_file = tmp_path / "lib" / "python3.14" / "site-packages" / "benson" / "config.py"
    fake_file.parent.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cfg, "__file__", str(fake_file))

    assert cfg.project_root() == tmp_path.resolve()
    settings = Settings.from_env()
    assert settings.schema_root == (tmp_path / "assets" / "schemas").resolve()
    assert settings.searchables_cache_dir == (tmp_path / "data" / "searchables").resolve()
