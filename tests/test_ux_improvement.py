"""
快速测试脚本 - 验证结果呈现 UX 改进

测试点:
1. 后端路由调整: pdf_generator → END
2. 前端状态变量: showReportModal, finalReport, followupAvailable
3. 事件处理函数: handleDownloadReport, handleFollowupSubmit
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_backend_route():
    """测试后端路由逻辑"""
    print("=" * 60)
    print("测试 1: 后端路由调整")
    print("=" * 60)
    
    try:
        from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow
        from intelligent_project_analyzer.core.state import ProjectAnalysisState
        
        # 创建测试工作流
        workflow = MainWorkflow(config={
            "post_completion_followup_enabled": True
        })
        
        # 创建测试状态
        test_state = ProjectAnalysisState()
        
        # 调用路由函数
        result = workflow._route_after_pdf_generator(test_state)
        
        # 验证结果（LangGraph 的 END 常量实际值是 "__end__"）
        assert str(result) in ["END", "__end__"], f"❌ 路由应返回 END，实际返回: {result}"
        assert test_state.get("post_completion_followup_available") == True, "❌ 缺少 followup_available 标志"
        
        print("✅ 后端路由测试通过")
        print(f"   - 路由返回: {result}")
        print(f"   - followup_available: {test_state.get('post_completion_followup_available')}")
        return True
        
    except Exception as e:
        print(f"❌ 后端路由测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_frontend_code():
    """测试前端代码结构"""
    print("\n" + "=" * 60)
    print("测试 2: 前端代码结构")
    print("=" * 60)
    
    frontend_file = "frontend-nextjs/app/analysis/[sessionId]/page.tsx"
    
    if not os.path.exists(frontend_file):
        print(f"❌ 前端文件不存在: {frontend_file}")
        return False
    
    with open(frontend_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键代码
    checks = [
        ("showReportModal 状态变量", "const [showReportModal, setShowReportModal]"),
        ("finalReport 状态变量", "const [finalReport, setFinalReport]"),
        ("followupAvailable 状态变量", "const [followupAvailable, setFollowupAvailable]"),
        ("showFollowupDialog 状态变量", "const [showFollowupDialog, setShowFollowupDialog]"),
        ("handleDownloadReport 函数", "const handleDownloadReport = "),
        ("handleOpenFollowup 函数", "const handleOpenFollowup = "),
        ("handleFollowupSubmit 函数", "const handleFollowupSubmit = "),
        ("报告展示模态框 JSX", "{showReportModal && finalReport &&"),
        ("追问对话框 JSX", "{showFollowupDialog &&"),
        ("自动弹出报告逻辑", "setShowReportModal(true)")
    ]
    
    all_passed = True
    for check_name, check_string in checks:
        if check_string in content:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name} - 未找到")
            all_passed = False
    
    return all_passed


def test_documentation():
    """测试文档是否创建"""
    print("\n" + "=" * 60)
    print("测试 3: 文档完整性")
    print("=" * 60)
    
    doc_file = "docs/RESULT_PRESENTATION_REDESIGN.md"
    
    if not os.path.exists(doc_file):
        print(f"❌ 文档不存在: {doc_file}")
        return False
    
    with open(doc_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查关键章节
    sections = [
        "## 📋 问题分析",
        "## 🎯 理想用户体验",
        "## 🛠️ 技术实现",
        "### Phase 1: 后端调整",
        "### Phase 2: 前端实现",
        "## 🎨 视觉设计",
        "## 📊 预期效果",
        "## 🚀 实施计划"
    ]
    
    all_passed = True
    for section in sections:
        if section in content:
            print(f"✅ {section}")
        else:
            print(f"❌ {section} - 未找到")
            all_passed = False
    
    # 检查文档长度（应该是详细的设计文档）
    word_count = len(content)
    if word_count > 5000:
        print(f"✅ 文档长度: {word_count} 字符（详细）")
    else:
        print(f"⚠️  文档长度: {word_count} 字符（可能不够详细）")
    
    return all_passed


def test_readme_update():
    """测试 README 是否更新"""
    print("\n" + "=" * 60)
    print("测试 4: README 更新")
    print("=" * 60)
    
    readme_file = "README.md"
    
    with open(readme_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否包含 UX 改进说明
    checks = [
        ("结果呈现 UX 改进", "结果呈现 UX 改进"),
        ("自动弹出报告展示", "自动弹出报告展示模态框"),
        ("智能追问对话框", "智能追问对话框"),
        ("流程优化说明", "先呈现成果"),
        ("文档链接", "RESULT_PRESENTATION_REDESIGN.md")
    ]
    
    all_passed = True
    for check_name, check_string in checks:
        if check_string in content:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name} - 未找到")
            all_passed = False
    
    return all_passed


def main():
    """运行所有测试"""
    print("\n🚀 开始测试结果呈现 UX 改进...")
    print("=" * 60)
    
    results = {
        "后端路由": test_backend_route(),
        "前端代码": test_frontend_code(),
        "设计文档": test_documentation(),
        "README": test_readme_update()
    }
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print("\n" + "=" * 60)
    if passed == total:
        print(f"🎉 所有测试通过！({passed}/{total})")
        print("\n✅ 结果呈现 UX 改进已完成")
        print("\n📝 关键改动:")
        print("   1. 后端: pdf_generator → END (前端接管)")
        print("   2. 前端: 新增报告展示模态框 + 追问对话框")
        print("   3. 体验: 先呈现成果 → 再提供追问选项")
        print("\n📚 详细设计文档:")
        print("   docs/RESULT_PRESENTATION_REDESIGN.md")
        return 0
    else:
        print(f"⚠️  部分测试失败 ({passed}/{total})")
        print("\n请检查上述失败项并修复")
        return 1


if __name__ == "__main__":
    sys.exit(main())
