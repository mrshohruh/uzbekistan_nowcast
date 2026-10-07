"""Resolve active settings from their existing authoritative frozen documents."""
from pathlib import Path
from scripts.operations.state import read


def configuration(root: Path) -> dict:
    index = read(root/'config/production.json')
    pointer = read(root/index['active_pointer'])
    policy = read(root/pointer['policy'])
    frozen = read(root/index['frozen_models'])
    current = read(root/pointer['nowcast'])
    dfm = frozen['challengers']['PHASE6C_DFM']
    if index['active_specification'] != 'M0' or policy['model'] != 'COMBO_50_50':
        raise ValueError('Production freeze requires the existing M0 / COMBO_50_50 policy')
    if policy['specification_hashes'] != frozen['specification_hashes']:
        raise ValueError('Active and frozen specifications disagree')
    weights = frozen['challengers'][policy['model']]['weights']
    if weights != {'dfm': policy['dfm_weight'], 'umidas': policy['umidas_weight']}:
        raise ValueError('Active and frozen combination weights disagree')
    return dict(index=index, pointer=pointer, policy=policy, dfm=dfm,
                umidas=frozen['challengers']['UMIDAS_USD'], weights=weights,
                target=current['target_convention'], release_rule=policy['current_release_rule'])
