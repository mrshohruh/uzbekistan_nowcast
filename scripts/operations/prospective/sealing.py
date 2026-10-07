"""Current production seal; historical inventories are evidence only."""
from scripts.operations.state import model_lock
from scripts.operations.prospective.common import ROOT
def initialize(out=None):
    return model_lock(ROOT)[1]
