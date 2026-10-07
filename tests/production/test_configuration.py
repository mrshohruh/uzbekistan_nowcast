"""The production index resolves settings without redefining the frozen model."""
from pathlib import Path
from scripts.production.config import configuration
from scripts.production import models


def test_active_configuration_matches_the_actual_design():
    config=configuration(Path(__file__).resolve().parents[2])
    assert tuple(config['dfm']['factor_specification']['fields']) == tuple(models.FIELDS)
    assert config['dfm']['source_model'] == models.SPEC_NAME
    assert config['weights'] == {'dfm': 0.5, 'umidas': 0.5}
    assert config['policy']['model'] == 'COMBO_50_50'
    assert config['index']['active_specification'] == 'M0'
