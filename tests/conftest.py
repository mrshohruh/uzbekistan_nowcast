from pathlib import Path
import json
import pytest
import requests
from uznowcast.registry import load_registry

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError('Network access forbidden in unit tests')
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)


@pytest.fixture
def registry():
    return load_registry(ROOT / 'registry/uzbekistan_nowcasting_v1.1_registry.xlsx')


@pytest.fixture
def contracts():
    return json.loads((ROOT / 'config/siat_contracts.json').read_text())


@pytest.fixture
def fixture_json():
    return lambda name: json.loads((ROOT / f'tests/fixtures/{name}.json').read_text(encoding='utf-8'))
