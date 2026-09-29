"""Phase 4A benchmark GDP-nowcasting models.

Read-only against the V1.2 database. Every output is written under
``results/`` and ``docs/modeling/``. No script here modifies raw payloads,
processed parquets, the observations-long table, vintages, revisions,
release calendar, or the registry.
"""

MODEL_LAYER_VERSION = '4a.0'
"""Bump when a model implementation changes in a way that affects
reproducible predictions."""
