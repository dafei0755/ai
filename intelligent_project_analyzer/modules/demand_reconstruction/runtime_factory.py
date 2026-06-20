"""Runtime dependency assembly for demand reconstruction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from intelligent_project_analyzer.modules.demand_reconstruction.alignment_gate import (
    DemandReconstructionAlignmentGate,
)
from intelligent_project_analyzer.modules.demand_reconstruction.blueprint_coordinator import (
    DemandReconstructionBlueprintCoordinator,
)
from intelligent_project_analyzer.modules.demand_reconstruction.conversation_handler import (
    DemandReconstructionConversationHandler,
)
from intelligent_project_analyzer.modules.demand_reconstruction.contracts import (
    DemandReconstructionUnavailable,
)
from intelligent_project_analyzer.modules.demand_reconstruction.entry_classifier import (
    DemandReconstructionEntryClassifier,
)
from intelligent_project_analyzer.modules.demand_reconstruction.governance import (
    DemandReconstructionGovernance,
)
from intelligent_project_analyzer.modules.demand_reconstruction.insight_quality_gate import (
    DemandReconstructionInsightQualityGate,
)
from intelligent_project_analyzer.modules.demand_reconstruction.pipeline import (
    DemandReconstructionPipeline,
)
from intelligent_project_analyzer.modules.demand_reconstruction.response_builder import (
    DemandReconstructionResponseBuilder,
)
from intelligent_project_analyzer.modules.demand_reconstruction.semantic_context_applier import (
    DemandReconstructionSemanticContextApplier,
)
from intelligent_project_analyzer.modules.demand_reconstruction.semantic_router import (
    DemandReconstructionSemanticRouter,
)
from intelligent_project_analyzer.modules.demand_reconstruction.semantic_targets import (
    LLM_SEMANTIC_TARGET_ALIASES,
)
from intelligent_project_analyzer.modules.demand_reconstruction.synthesis import (
    DemandReconstructionSynthesis,
)
from intelligent_project_analyzer.services.demand_reconstruction_context_adapter import (
    DemandReconstructionContextAdapter,
)
from intelligent_project_analyzer.services.demand_reconstruction_insight_protocol import (
    DemandReconstructionInsightProtocol,
)
from intelligent_project_analyzer.services.demand_reconstruction_insight_quality import (
    DemandReconstructionInsightQualityEvaluator,
)
from intelligent_project_analyzer.services.demand_reconstruction_output_planner import (
    DemandReconstructionOutputPlanner,
)
from intelligent_project_analyzer.services.latent_model_adapter import LatentModelAdapter


@dataclass(frozen=True)
class DemandReconstructionRuntime:
    """Instantiated collaborators required by the compatibility service."""

    governance: Any
    entry_classifier: Any
    context_adapter: Any
    insight_protocol: Any
    semantic_router: Any
    semantic_context_applier: Any
    output_planner: Any
    synthesis: Any
    blueprint_coordinator: Any
    response_builder: Any
    alignment_gate: Any
    latent_model_adapter: Any
    insight_quality_evaluator: Any
    insight_quality_gate: Any
    pipeline: Any
    conversation_handler: Any


class DemandReconstructionRuntimeFactory:
    """Assemble demand reconstruction runtime components in dependency order."""

    @staticmethod
    def build(
        *,
        llm: Any,
        require_llm: bool,
        governance_store: Any,
        card_type: str,
        result_builder: Callable[..., Dict[str, Any]],
        context_adapter: Any = None,
        insight_protocol: Any = None,
        output_planner: Any = None,
        latent_model_adapter: Any = None,
        insight_quality_evaluator: Any = None,
        semantic_router: Any = None,
        synthesis: Any = None,
        governance: Any = None,
        alignment_gate: Any = None,
        insight_quality_gate: Any = None,
        response_builder: Any = None,
        semantic_context_applier: Any = None,
        blueprint_coordinator: Any = None,
        conversation_handler: Any = None,
        entry_classifier: Any = None,
        pipeline: Any = None,
    ) -> DemandReconstructionRuntime:
        governance = governance or DemandReconstructionGovernance(
            governance_store=governance_store,
        )
        entry_classifier = entry_classifier or DemandReconstructionEntryClassifier()
        context_adapter = context_adapter or DemandReconstructionContextAdapter()
        insight_protocol = insight_protocol or DemandReconstructionInsightProtocol()
        semantic_router = semantic_router or DemandReconstructionSemanticRouter(
            llm=llm,
            parse_response_json=insight_protocol.parse_response_json,
            target_aliases=LLM_SEMANTIC_TARGET_ALIASES,
        )
        semantic_context_applier = (
            semantic_context_applier
            or DemandReconstructionSemanticContextApplier(
                target_aliases=LLM_SEMANTIC_TARGET_ALIASES,
            )
        )
        output_planner = output_planner or DemandReconstructionOutputPlanner()
        synthesis = synthesis or DemandReconstructionSynthesis(
            llm=llm,
            insight_protocol=insight_protocol,
            output_planner=output_planner,
        )
        blueprint_coordinator = (
            blueprint_coordinator
            or DemandReconstructionBlueprintCoordinator(
                llm=llm,
                output_planner=output_planner,
                synthesis=synthesis,
                require_llm=require_llm,
                unavailable_factory=DemandReconstructionUnavailable,
            )
        )
        response_builder = response_builder or DemandReconstructionResponseBuilder()
        alignment_gate = alignment_gate or DemandReconstructionAlignmentGate(
            output_planner=output_planner,
            render_reply=response_builder.render_reply,
            build_card=response_builder.build_card,
        )
        latent_model_adapter = latent_model_adapter or LatentModelAdapter()
        insight_quality_evaluator = (
            insight_quality_evaluator or DemandReconstructionInsightQualityEvaluator()
        )
        insight_quality_gate = insight_quality_gate or DemandReconstructionInsightQualityGate(
            evaluator=insight_quality_evaluator,
        )
        pipeline = pipeline or DemandReconstructionPipeline(
            llm=llm,
            require_llm=require_llm,
            unavailable_factory=DemandReconstructionUnavailable,
            context_adapter=context_adapter,
            semantic_router=semantic_router,
            semantic_context_applier=semantic_context_applier,
            governance=governance,
            latent_model_adapter=latent_model_adapter,
            blueprint_coordinator=blueprint_coordinator,
            response_builder=response_builder,
            alignment_gate=alignment_gate,
            insight_quality_gate=insight_quality_gate,
        )
        conversation_handler = (
            conversation_handler
            or DemandReconstructionConversationHandler(
                card_type=card_type,
                entry_classifier=entry_classifier,
                result_builder=result_builder,
            )
        )

        return DemandReconstructionRuntime(
            governance=governance,
            entry_classifier=entry_classifier,
            context_adapter=context_adapter,
            insight_protocol=insight_protocol,
            semantic_router=semantic_router,
            semantic_context_applier=semantic_context_applier,
            output_planner=output_planner,
            synthesis=synthesis,
            blueprint_coordinator=blueprint_coordinator,
            response_builder=response_builder,
            alignment_gate=alignment_gate,
            latent_model_adapter=latent_model_adapter,
            insight_quality_evaluator=insight_quality_evaluator,
            insight_quality_gate=insight_quality_gate,
            pipeline=pipeline,
            conversation_handler=conversation_handler,
        )
