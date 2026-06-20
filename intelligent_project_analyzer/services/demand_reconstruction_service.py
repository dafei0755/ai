"""Compatibility import path for demand reconstruction service.

The canonical implementation lives in
``intelligent_project_analyzer.modules.demand_reconstruction.service``.
"""

from intelligent_project_analyzer.modules.demand_reconstruction.service import (
    DemandReconstructionService,
)
from intelligent_project_analyzer.modules.demand_reconstruction.contracts import (
    DemandReconstructionUnavailable,
)

__all__ = [
    "DemandReconstructionService",
    "DemandReconstructionUnavailable",
]
