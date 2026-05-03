from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway

# 合法迁移表：{current_state: [allowed_target_states]}
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "draft":                ["pending_confirmation"],
    "pending_confirmation": ["frozen", "draft"],
    "frozen":               ["stale"],
    "stale":                ["pending_confirmation"],
}


class InvalidStateTransitionError(Exception):
    def __init__(self, current: str, target: str):
        self.status_code = 409
        super().__init__(
            f"Invalid state transition: {current} → {target}. "
            f"Allowed from {current}: {ALLOWED_TRANSITIONS.get(current, [])}"
        )


class StateTransitionService:
    def __init__(self, gateway: ObjectGateway):
        self._gw = gateway

    def transition(self, project_id: str, target_state: str) -> None:
        project = self._gw.get_project(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")
        current = project.object_state
        allowed = ALLOWED_TRANSITIONS.get(current, [])
        if target_state not in allowed:
            raise InvalidStateTransitionError(current, target_state)
        self._gw.update_project_state(project_id, target_state)
