"""Auditable grouping and a concept-based, predeclared economic core."""
import pandas as pd
from scripts.phase7d.data import release_gate

BLOCKS = {
    'F1': 'Industrial activity', 'F2': 'Services activity',
    'F3': 'Domestic demand', 'F4': 'External conditions',
    'F5': 'Prices and monetary conditions',
}
RATIONALE = {
    'F1': 'Nominal production and supply co-movement; neither real output nor additive sector GDP shares.',
    'F2': 'Reported service-sector activity indices; actual history starts in 2024; no earlier observations exist.',
    'F3': 'Trade, construction and enterprise activity proxies for transactions/investment; not final expenditure.',
    'F4': 'Nominal USD trade, gold price and reserves describe external demand, input and valuation conditions.',
    'F5': 'Inflation, liquidity and financing conditions; a single common factor requires empirical scrutiny.',
    'Q_BRIDGE': 'Separate quarterly covariate; q-1 only, released or projected from released history.',
}
# Unique substrings match exact original workbook labels, never synthetic series.
CORE = {
    'F1': ['Industrial production — Manufacturing industry', 'Industrial production — Mining and quarrying',
           'Industrial production — Electricity, gas, steam and air conditioning'],
    'F2': ['Rendered market services — Transport activities', 'Rendered market services — Information and communication',
           'Rendered market services — Financial activities', 'Rendered market services — Accommodation and food'],
    'F3': ['Retail trade volume', 'Wholesale trade volume', 'Construction works'],
    'F4': ['Export volume', 'Import volume', 'Gold (USD/troy oz)'],
    'F5': ['CPI — Cumulative index', 'PPI — Composite index', 'M2 — Broad money',
           'Interest rates — Loans extended to legal entities'],
}


def group(label, frequency):
    if frequency == 'Q':
        return 'Q_BRIDGE'
    if label.startswith('Industrial production'): return 'F1'
    if label.startswith('Rendered market services'): return 'F2'
    if label.startswith(('Construction', 'Retail', 'Wholesale', 'Small business', 'Operating enterprises')): return 'F3'
    if label.startswith(('Export', 'Import', 'Gold (', 'International reserves')): return 'F4'
    if label.startswith(('CPI', 'PPI', 'M2', 'Interest rates')): return 'F5'
    raise ValueError('Unassigned indicator: ' + label)


def core_columns(monthly):
    selected = {}
    for block, concepts in CORE.items():
        selected[block] = []
        for concept in concepts:
            matches = [c for c in monthly if concept in c]
            if len(matches) != 1: raise ValueError(f'Core concept {concept}: {matches}')
            selected[block].append(matches[0])
    flat = [c for cs in selected.values() for c in cs]
    if len(flat) != len(set(flat)): raise ValueError('Duplicated core indicator')
    return selected


def inventory(inputs, cutoff):
    result = inputs.inventory.copy()
    if not result.original_label.is_unique: raise ValueError('Duplicate predictor inventory')
    if set(result.original_label) != set(inputs.monthly) | set(inputs.quarterly):
        raise ValueError('Inventory omitted or added indicators')
    result['economic_group'] = [group(r.original_label, r.frequency) for r in result.itertuples()]
    result['economic_justification'] = result.economic_group.map(RATIONALE)
    result['source_definition_uncertainty'] = result.raw_definition + ' Workbook source URL, retrieval and release vintage unverified.'
    result['possible_duplication_overlap'] = [overlap(r.original_label, r.economic_group) for r in result.itertuples()]
    selected = {c for cs in core_columns(inputs.monthly).values() for c in cs}
    result['economic_core_selected'] = result.original_label.isin(selected)
    result['core_decision'] = ['SELECTED_PREDECLARED_CONCEPT' if c in selected else
        'QUARTERLY_CANDIDATE_E4_NOT_MONTHLY_CORE' if c in inputs.quarterly else
        'EXCLUDED_CORE_BROAD_COVERAGE_RETAINED_IN_FULL_BLOCK' for c in result.original_label]
    result['coverage_share'] = result.usable_observations / result.frequency.map({'M': len(inputs.monthly), 'Q': len(inputs.quarterly)})
    latest = {}
    for frame in [inputs.monthly, inputs.quarterly]:
        gated = release_gate(frame, inputs.inventory, cutoff)
        for c in frame: latest[c] = str(gated[c].last_valid_index())
    result['latest_available_at_cutoff'] = result.original_label.map(latest)
    result['current_availability_cutoff'] = str(pd.Timestamp(cutoff).date())
    if (result.frequency.eq('M').sum(), result.frequency.eq('Q').sum()) != (91, 5):
        raise ValueError('Expected exactly 91 monthly and five quarterly predictors')
    return result


def overlap(label, block):
    if block == 'F1': return 'Aggregate, broad sectors and detailed manufacturing overlap; fixed family-balanced measurement weights; not additive GDP contributions.'
    if block == 'F2': return 'Transport and motor transport overlap; services Trade overlaps trade turnover in F3.'
    if block == 'F3': return 'Retail/wholesale overlap services Trade; enterprise definitions provisional; construction is investment proxy.'
    if block == 'F4': return 'Gold price and USD gold reserves share valuation effects; trade values are not volumes; no FX indicator in this workbook.'
    if block == 'F5': return 'Headline and detailed CPI/PPI categories overlap; monetary stocks and rates need not share inflation factor.'
    return 'Investment/FDI investment and wages/population income overlap; secondary income credits are not verified migrant remittances.'


def family(label, block):
    """Fixed label-based weights control category multiplicity, without exclusions."""
    if block == 'F1':
        if '— Industrial production (' in label: return 'aggregate'
        if any(t in label for t in ['— Mining and quarrying', '— Manufacturing industry', '— Electricity, gas', '— Water supply']): return 'broad_sectors'
        return 'manufacturing_details'
    if block == 'F5':
        return 'CPI' if label.startswith('CPI') else 'PPI' if label.startswith('PPI') else 'money' if label.startswith('M2') else 'rates'
    if block == 'F4': return 'trade' if label.startswith(('Export', 'Import')) else 'reserves' if label.startswith('International') else 'gold_price'
    if block == 'F3': return 'enterprises' if label.startswith(('Small business', 'Operating')) else 'activity'
    return 'transport' if any(s in label for s in ['Transport activities', 'motor transport']) else 'other_services'


def anchors(columns, block):
    concepts = {'F1': ['Industrial production — Manufacturing industry', 'Industrial production — Industrial production'],
                'F2': ['Rendered market services — Transport activities', 'Rendered market services — Information and communication'],
                'F3': ['Retail trade volume', 'Wholesale trade volume'],
                'F4': ['Export volume', 'Gold (USD/troy oz)'],
                'F5': ['CPI — Cumulative index', 'PPI — Composite index']}[block]
    for concept in concepts:
        match = [c for c in columns if concept in c]
        if match: return match[0]
    raise ValueError(f'No predeclared orientation anchor for {block}')
