from scripts.audit_demand_reconstruction_insight_quality import parse_numbered_questions


def test_parse_numbered_questions_from_plain_text() -> None:
    questions = parse_numbered_questions("1. 第一题内容\n2. 第二题内容\n")

    assert questions == [(1, "第一题内容"), (2, "第二题内容")]
