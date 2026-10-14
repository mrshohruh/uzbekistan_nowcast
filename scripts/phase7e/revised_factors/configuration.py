"""Exact-label exclusions, retaining the original data and factor assignments."""
from dataclasses import dataclass

from scripts.phase7e.grouping import anchors, core_columns

EXCLUSIONS = {
    'Industrial production — Industrial production (billion UZS) [M]':
        ('F1', 'Aggregate overlaps industrial components; deliberately excluded.'),
    'CPI — Cumulative index (index, %) [M]':
        ('F5', 'Headline overlaps retained CPI categories; deliberately excluded.'),
    'PPI — Composite index (index, %) [M]':
        ('F5', 'Composite overlaps retained PPI categories; deliberately excluded.'),
}


@dataclass(frozen=True)
class RevisedFactors:
    """Same factor numbers, fixed weighting formula, and estimation settings."""
    cache_token: str = 'PHASE7E_EXCLUDE_INDUSTRY_CPI_PPI_V1'

    def columns(self, monthly, grouping, block, core=False):
        original = core_columns(monthly)[block] if core else grouping.loc[
            grouping.economic_group.eq(block), 'original_label'].tolist()
        return [c for c in original if c not in EXCLUSIONS]

    def anchor(self, usable, block):
        if block != 'F5':
            return anchors(usable, block)
        # Both original F5 anchors were explicitly removed. M2 is already in
        # both specifications: this fixes sign only, adds no measurement.
        matches = [c for c in usable if c.startswith('M2 — Broad money')]
        if len(matches) != 1:
            raise ValueError('Retained M2 sign anchor not identifiable at origin')
        return matches[0]

    def inventory(self, inputs, original):
        if not set(EXCLUSIONS).issubset(inputs.monthly):
            raise ValueError('Exact excluded workbook labels missing')
        result = original.copy()
        for label, (block, _) in EXCLUSIONS.items():
            if result.set_index('original_label').at[label, 'economic_group'] != block:
                raise ValueError('Excluded indicator has an unexpected factor')
        core = {c for b in ['F1', 'F2', 'F3', 'F4', 'F5']
                for c in self.columns(inputs.monthly, original, b, True)}
        result['original_core_selected'] = result.economic_core_selected
        result['revised_core_selected'] = result.original_label.isin(core)
        result['revised_factor_included'] = result.frequency.eq('M') & ~result.original_label.isin(EXCLUSIONS)
        result['revised_decision'] = [EXCLUSIONS[c][1] if c in EXCLUSIONS else
            'UNCHANGED_QUARTERLY_E4_COVARIATE' if c in inputs.quarterly else
            'RETAINED_IN_ORIGINAL_FACTOR' for c in result.original_label]
        return result
