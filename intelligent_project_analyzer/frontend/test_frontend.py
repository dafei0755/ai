"""
前端功能测试脚本

测试前端组件和功能是否正常工作
"""

import sys
import io
from pathlib import Path

# 设置输出编码为 UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """测试导入"""
    print("=" * 60)
    print("测试 1: 导入模块")
    print("=" * 60)
    
    try:
        import streamlit as st
        print(" Streamlit 导入成功")
    except ImportError as e:
        print(f" Streamlit 导入失败: {e}")
        return False
    
    try:
        from intelligent_project_analyzer.frontend import app
        print(" 前端应用模块导入成功")
    except ImportError as e:
        print(f" 前端应用模块导入失败: {e}")
        return False
    
    try:
        from intelligent_project_analyzer.frontend import frontend_components
        print(" 前端组件模块导入成功")
    except ImportError as e:
        print(f" 前端组件模块导入失败: {e}")
        return False
    
    try:
        from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow
        print(" 工作流模块导入成功")
    except ImportError as e:
        print(f" 工作流模块导入失败: {e}")
        return False
    
    print()
    return True


def test_env_config():
    """测试环境配置"""
    print("=" * 60)
    print("测试 2: 环境配置")
    print("=" * 60)
    
    import os
    from dotenv import load_dotenv
    
    # 加载环境变量
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f" .env 文件存在: {env_file}")
    else:
        print(f"️  .env 文件不存在: {env_file}")
    
    # 检查 API 密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print(f" OPENAI_API_KEY 已配置 (长度: {len(api_key)})")
    else:
        print(" OPENAI_API_KEY 未配置")
    
    # 检查 API Base
    api_base = os.getenv("OPENAI_API_BASE")
    if api_base:
        print(f" OPENAI_API_BASE 已配置: {api_base}")
    else:
        print("ℹ️  OPENAI_API_BASE 未配置 (将使用默认值)")
    
    print()
    return True


def test_workflow_creation():
    """测试工作流创建"""
    print("=" * 60)
    print("测试 3: 工作流创建")
    print("=" * 60)
    
    import os
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI
    from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow
    
    # 加载环境变量
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(" 无法测试工作流创建: 缺少 API 密钥")
        return False
    
    try:
        # 创建 LLM
        llm_config = {
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "api_key": api_key
        }
        
        api_base = os.getenv("OPENAI_API_BASE")
        if api_base:
            llm_config["base_url"] = api_base
        
        llm = ChatOpenAI(**llm_config)
        print(" LLM 创建成功")
        
        # 创建工作流 (Fixed 模式)
        config_fixed = {
            "mode": "fixed",
            "enable_role_config": False
        }
        workflow_fixed = MainWorkflow(llm, config_fixed)
        print(" Fixed 模式工作流创建成功")
        
        # 创建工作流 (Dynamic 模式)
        config_dynamic = {
            "mode": "dynamic",
            "enable_role_config": True
        }
        workflow_dynamic = MainWorkflow(llm, config_dynamic)
        print(" Dynamic 模式工作流创建成功")
        
    except Exception as e:
        print(f" 工作流创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    return True


def test_frontend_components():
    """测试前端组件"""
    print("=" * 60)
    print("测试 4: 前端组件")
    print("=" * 60)
    
    try:
        from intelligent_project_analyzer.frontend.frontend_components import (
            apply_custom_css,
            render_header,
            render_sidebar,
            render_progress_tracker,
            render_analysis_results,
            render_agent_card
        )
        
        print(" apply_custom_css 函数导入成功")
        print(" render_header 函数导入成功")
        print(" render_sidebar 函数导入成功")
        print(" render_progress_tracker 函数导入成功")
        print(" render_analysis_results 函数导入成功")
        print(" render_agent_card 函数导入成功")
        
    except ImportError as e:
        print(f" 前端组件导入失败: {e}")
        return False
    
    print()
    return True


def test_file_structure():
    """测试文件结构"""
    print("=" * 60)
    print("测试 5: 文件结构")
    print("=" * 60)
    
    frontend_dir = project_root / "intelligent_project_analyzer" / "frontend"
    
    required_files = [
        "app.py",
        "frontend_components.py",
        "run_frontend.py",
        "README.md",
        "requirements.txt",
        "__init__.py"
    ]
    
    all_exist = True
    for filename in required_files:
        filepath = frontend_dir / filename
        if filepath.exists():
            print(f" {filename} 存在")
        else:
            print(f" {filename} 不存在")
            all_exist = False
    
    print()
    return all_exist


def main():
    """主函数"""
    print("\n")
    print(" 智能项目分析系统 - 前端功能测试")
    print("=" * 60)
    print()
    
    results = []
    
    # 运行测试
    results.append(("导入模块", test_imports()))
    results.append(("环境配置", test_env_config()))
    results.append(("工作流创建", test_workflow_creation()))
    results.append(("前端组件", test_frontend_components()))
    results.append(("文件结构", test_file_structure()))
    
    # 汇总结果
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = " 通过" if result else " 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print()
    print(f"总计: {passed} 通过, {failed} 失败")
    print()
    
    if failed == 0:
        print(" 所有测试通过！前端已准备就绪。")
        print()
        print("启动前端:")
        print("  streamlit run intelligent_project_analyzer/frontend/app.py")
        print()
    else:
        print("️  部分测试失败，请检查配置。")
        print()
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

