from dataclasses import dataclass, field
from intelligent_project_analyzer.advisor.models import AdvisorActionDraft
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway

# Phase A 允许的 actor（简化，Phase B+ 接入真实权限系统）
_ALLOWED_ACTORS = {"user-1", "user-demo", "advisor", "system"}


@dataclass
class GateCheckError:
    code: int
    message: str


# 别名，兼容导入
GateError = GateCheckError


@dataclass
class GateResult:
    passed: bool = False
    errors: list[GateCheckError] = field(default_factory=list)
    needs_confirmation: bool = False
    response_code: int = 200


class MVPGate:
    """写路径前的 4 项同步校验。失败不改变对象状态。"""

    def __init__(self, gateway: ObjectGateway):
        self._gw = gateway

    def run(self, draft: AdvisorActionDraft, actor: str) -> GateResult:
        errors: list[GateCheckError] = []

        # 1. schema_check
        if not draft.payload.get("name"):
            errors.append(GateCheckError(422, "payload.name 是必填字段"))

        # 2. permission_check
        if actor not in _ALLOWED_ACTORS:
            errors.append(GateCheckError(403, f"actor '{actor}' 无权限执行此操作"))

        # 3. object_state_check
        project = self._gw.get_project(draft.project_id)
        if project and project.object_state == "frozen":
            errors.append(GateCheckError(409, f"Project {draft.project_id} 已冻结，拒绝写入"))

        if errors:
            return GateResult(passed=False, errors=errors)

        # 4. confirmation_required_check — Phase A 所有写操作都需要确认
        return GateResult(
            passed=True,
            errors=[],
            needs_confirmation=True,
            response_code=202,
        )
