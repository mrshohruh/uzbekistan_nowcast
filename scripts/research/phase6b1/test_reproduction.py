import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from reproduce import demonstrate


def test_original_phase6b_leak_is_reproducible():
    result=demonstrate()
    assert result['status']=='LEAK_CONFIRMED'
    assert not result['prior_available_under_registry_rule']
    assert result['prediction_after']!=result['prediction_before']
