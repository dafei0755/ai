"""生成预填充 Release Signoff 文本。

用途：
1) 自动读取 VERSION 与当天日期。
2) 生成可直接粘贴到 GitHub Issue 的 signoff 模板。
3) 降低手工填写版本号导致的漂移风险。
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    today = dt.datetime.now().strftime("%Y-%m-%d")
    title = f"[Release Signoff] v{version} {today}"

    output = f"""{title}

发布版本: v{version}
发布窗口（北京时间）: {today} 22:00-23:00

CI 证据链接:
- CI:
- Automated Tests:
- Security:

回滚方案:
- 目标Tag: v{version}
- 回滚命令(安全分支): python scripts/rollback_to_tag.py v{version}
- 触发阈值:
- 责任人:

P0 门禁确认:
- [ ] CI/测试门禁全部通过
- [ ] 安全基线无新增未审批风险
- [ ] 回滚方案已演练或验证
- [ ] PRE_RELEASE_CHECKLIST 已逐项完成

角色签字:
- [ ] 技术负责人签字
- [ ] 运维负责人签字
- [ ] 发布经理签字
"""

    out_dir = root / "docs" / "releases" / "signoff"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"release_signoff_v{version}_{today}.md"
    out_file.write_text(output, encoding="utf-8")

    print(f"✅ 已生成签字单草稿: {out_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
