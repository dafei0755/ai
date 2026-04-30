import pytest

from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow


class _FakeLLM:
    def invoke(self, *args, **kwargs):
        return None


def test_first_batch_builder_should_raise_instead_of_swallowing_exception():
    workflow = MainWorkflow(llm_model=_FakeLLM())

    # active_agents 传入不可迭代对象，触发异常分支
    with pytest.raises(RuntimeError, match="无法创建第一批并行任务"):
        workflow._continue_to_first_batch_agents({"active_agents": None})


def test_second_batch_builder_should_raise_instead_of_swallowing_exception():
    workflow = MainWorkflow(llm_model=_FakeLLM())

    # active_agents 传入不可迭代对象，触发异常分支
    with pytest.raises(RuntimeError, match="无法创建第二批并行任务"):
        workflow._continue_to_second_batch_agents({"active_agents": None})
