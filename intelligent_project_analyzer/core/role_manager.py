"""
角色管理器 - Role Manager

负责加载、管理和查询角色配置。
Responsible for loading, managing, and querying role configurations.
"""

import yaml
from typing import Dict, List, Optional
from pathlib import Path


class RoleManager:
    """
    角色管理器 - 管理所有可用的专业角色配置
    
    功能:
    1. 从YAML文件加载角色配置
    2. 提供角色查询接口
    3. 支持动态添加角色
    4. 创建默认配置模板
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化角色管理器

        Args:
            config_path: 角色配置文件或目录路径,如果为None则使用默认路径
        """
        if config_path is None:
            # 使用默认配置路径 - 优先使用roles目录，如果不存在则使用roles.yaml文件
            current_dir = Path(__file__).parent.parent
            roles_dir = current_dir / "config" / "roles"
            roles_file = current_dir / "config" / "roles.yaml"

            # 优先使用目录
            if roles_dir.exists() and roles_dir.is_dir():
                config_path = roles_dir
            else:
                config_path = roles_file

        self.config_path = Path(config_path)
        self.roles: Dict = {}

        # 加载角色配置
        if self.config_path.exists():
            self._load_roles()
        else:
            # 如果配置文件不存在,创建默认模板
            self._create_default_template()
            self._load_roles()
    
    def _load_roles(self) -> None:
        """从YAML文件或目录加载角色配置 - 支持目录拆分"""
        try:
            # 方案1：如果config_path是目录，加载目录下所有yaml文件
            if self.config_path.is_dir():
                print(f"[INFO] Loading roles from directory: {self.config_path}")
                self.roles = {}
                yaml_files = list(self.config_path.glob("*.yaml")) + list(self.config_path.glob("*.yml"))

                for yaml_file in yaml_files:
                    print(f"[INFO] Loading {yaml_file.name}...")
                    with open(yaml_file, 'r', encoding='utf-8') as f:
                        file_roles = yaml.safe_load(f) or {}
                        self.roles.update(file_roles)

                print(f"[OK] Successfully loaded role configuration from {len(yaml_files)} files: {len(self.get_all_role_ids())} roles")

            # 方案2：如果是单个文件，按原方式加载
            elif self.config_path.is_file():
                print(f"[INFO] Loading roles from file: {self.config_path}")
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.roles = yaml.safe_load(f) or {}
                print(f"[OK] Successfully loaded role configuration: {len(self.get_all_role_ids())} roles")

            else:
                print(f"[WARNING] Config path does not exist: {self.config_path}")
                self.roles = {}

        except Exception as e:
            print(f"[ERROR] Failed to load role configuration: {e}")
            self.roles = {}
    
    def _create_default_template(self) -> None:
        """创建默认配置模板"""
        # 确保配置目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建默认模板
        default_template = {
            "V2_设计总监": {
                "description": "设计总监类角色",
                "roles": {
                    "2-1": {
                        "name": "示例角色",
                        "description": "这是一个示例角色",
                        "keywords": ["示例", "模板"],
                        "system_prompt": "请在这里编写详细的角色提示词"
                    }
                }
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_template, f, allow_unicode=True, default_flow_style=False)

        print(f"[OK] Created default configuration template: {self.config_path}")
    
    def get_role_config(self, base_type: str, role_id: str) -> Optional[Dict]:
        """
        获取指定角色的配置
        
        Args:
            base_type: 基础类型 (如 "V2_设计总监")
            role_id: 角色ID (如 "2-1")
        
        Returns:
            角色配置字典,如果不存在则返回None
        
        v8.1: 支持合成角色ID (如 "2-1+5-1")
        当检测到合成角色时，自动融合父角色配置
        """
        # v8.1: 检测合成角色ID
        clean_id = role_id.replace("SYNTHESIZED_", "")
        if "+" in clean_id:
            return self._get_synthesized_role_config(clean_id)

        if base_type not in self.roles:
            return None
        
        base_config = self.roles[base_type]
        if not isinstance(base_config, dict):
            return None
            
        roles = base_config.get("roles", {})
        return roles.get(role_id)

    def _get_synthesized_role_config(self, composite_id: str) -> Optional[Dict]:
        """
        v8.1: 为合成角色动态生成融合配置
        
        将多个父角色的配置智能融合为一个新的角色配置。
        合成策略：
        1. system_prompt: 以主导父角色为框架，融合其他父角色的核心专业领域
        2. keywords: 合并去重所有父角色关键词
        3. description: 综合描述
        
        Args:
            composite_id: 合成角色ID，如 "2-1+5-1"
        
        Returns:
            融合后的角色配置字典
        """
        parent_ids = composite_id.split("+")
        parent_configs = []
        
        # V层级映射
        v_layer_map = {
            "2": "V2_设计总监", "3": "V3_叙事与体验专家",
            "4": "V4_设计研究员", "5": "V5_场景与行业专家",
            "6": "V6_专业总工程师", "7": "V7_社会关系与心理洞察专家",
        }
        
        for pid in parent_ids:
            layer_num = pid.split("-")[0]
            base_type = v_layer_map.get(layer_num)
            if base_type and base_type in self.roles:
                roles = self.roles[base_type].get("roles", {})
                config = roles.get(pid)
                if config:
                    parent_configs.append({
                        "parent_id": pid,
                        "base_type": base_type,
                        "config": config
                    })
        
        if not parent_configs:
            print(f"[WARNING] 合成角色 {composite_id} 未找到任何父角色配置")
            return None
        
        # 主导父角色 = 第一个
        primary = parent_configs[0]
        primary_config = primary["config"]
        
        # 融合关键词（合并去重）
        all_keywords = []
        seen_keywords = set()
        for pc in parent_configs:
            for kw in pc["config"].get("keywords", []):
                if kw not in seen_keywords:
                    all_keywords.append(kw)
                    seen_keywords.add(kw)
        
        # 融合描述
        parent_descs = [f"{pc['parent_id']}({pc['config'].get('name', '')})" for pc in parent_configs]
        fused_description = f"合成角色[{'+'.join(parent_descs)}]: 融合{', '.join(pc['config'].get('name', '') for pc in parent_configs)}的跨界能力"
        
        # 融合system_prompt: 主导框架 + 其他角色的核心能力注入
        primary_prompt = primary_config.get("system_prompt", "")
        capability_injections = []
        for pc in parent_configs[1:]:
            pc_name = pc["config"].get("name", pc["parent_id"])
            pc_keywords = ", ".join(pc["config"].get("keywords", [])[:5])
            capability_injections.append(
                f"\n### 融合能力来源: {pc_name}\n"
                f"你同时具备来自{pc['base_type']}的专业能力，核心领域包括: {pc_keywords}。\n"
                f"你需要将这些能力与你的主导能力深度融合，而非简单叠加。"
            )
        
        fused_prompt = primary_prompt
        if capability_injections:
            fused_prompt += "\n\n---\n## 跨界融合能力（动态合成）\n" + "\n".join(capability_injections)
        
        return {
            "name": primary_config.get("name", "") + "(合成)",
            "description": fused_description,
            "keywords": all_keywords,
            "system_prompt": fused_prompt,
            "is_synthesized": True,
            "parent_roles": [pc["parent_id"] for pc in parent_configs],
            "parent_base_types": [pc["base_type"] for pc in parent_configs],
            "synthesis_metadata": {
                "primary_parent": primary["parent_id"],
                "fusion_layers": list(set(pc["base_type"][:2] for pc in parent_configs)),
                "keyword_count": len(all_keywords),
            }
        }
    
    def get_roles_by_category(self, category: str) -> Dict:
        """
        获取指定类别下的所有角色配置

        Args:
            category: 角色类别名称（如 "V2_设计总监"）

        Returns:
            该类别下的角色字典 {role_id: role_config}

        Raises:
            KeyError: 如果类别不存在
        """
        if category not in self.roles:
            raise KeyError(f"角色类别不存在: {category}")
        base_config = self.roles[category]
        if not isinstance(base_config, dict):
            return {}
        return base_config.get("roles", {})

    def get_available_roles(self, base_type: Optional[str] = None) -> List[Dict]:
        """
        获取可用角色列表
        
        Args:
            base_type: 如果指定,只返回该类型下的角色;否则返回所有角色
        
        Returns:
            角色列表,每个角色包含完整信息
        """
        available_roles = []
        
        if base_type:
            # 只返回指定类型的角色
            if base_type in self.roles:
                base_config = self.roles[base_type]
                if isinstance(base_config, dict):
                    roles = base_config.get("roles", {})
                    for role_id, role_config in roles.items():
                        available_roles.append({
                            "base_type": base_type,
                            "role_id": role_id,
                            "full_id": f"{base_type}_{role_id}",
                            **role_config
                        })
        else:
            # 返回所有角色
            for b_type, type_config in self.roles.items():
                if not isinstance(type_config, dict):
                    continue
                    
                roles = type_config.get("roles", {})
                for role_id, role_config in roles.items():
                    available_roles.append({
                        "base_type": b_type,
                        "role_id": role_id,
                        "full_id": f"{b_type}_{role_id}",
                        **role_config
                    })
        
        return available_roles
    
    def get_all_role_ids(self) -> List[str]:
        """
        获取所有角色的完整ID列表
        
        Returns:
            角色ID列表 (格式: "V2_设计总监_2-1")
        """
        role_ids = []
        for base_type, base_config in self.roles.items():
            if not isinstance(base_config, dict):
                continue
                
            roles = base_config.get("roles", {})
            for role_id in roles.keys():
                role_ids.append(f"{base_type}_{role_id}")
        return role_ids
    
    def search_roles_by_keywords(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        根据关键词搜索角色
        
        Args:
            query: 搜索查询
            top_k: 返回前k个最相关的角色
        
        Returns:
            匹配的角色列表
        """
        all_roles = self.get_available_roles()
        matched_roles = []
        
        query_lower = query.lower()
        
        for role in all_roles:
            # 计算匹配分数
            score = 0
            
            # 检查名称匹配
            if query_lower in role.get("name", "").lower():
                score += 10
            
            # 检查描述匹配
            if query_lower in role.get("description", "").lower():
                score += 5
            
            # 检查关键词匹配
            keywords = role.get("keywords", [])
            for keyword in keywords:
                if query_lower in keyword.lower():
                    score += 3
            
            if score > 0:
                matched_roles.append({
                    **role,
                    "match_score": score
                })
        
        # 按分数排序
        matched_roles.sort(key=lambda x: x["match_score"], reverse=True)
        
        return matched_roles[:top_k]
    
    def add_role(self, base_type: str, role_id: str, role_config: Dict) -> bool:
        """
        动态添加新角色
        
        Args:
            base_type: 基础类型
            role_id: 角色ID
            role_config: 角色配置
        
        Returns:
            是否添加成功
        """
        try:
            # 确保基础类型存在
            if base_type not in self.roles:
                self.roles[base_type] = {
                    "description": f"{base_type}类角色",
                    "roles": {}
                }
            
            # 添加角色
            self.roles[base_type]["roles"][role_id] = role_config
            
            # 保存到文件
            self._save_roles()
            
            print(f" 成功添加角色: {base_type}_{role_id}")
            return True
        
        except Exception as e:
            print(f" 添加角色失败: {e}")
            return False
    
    def _save_roles(self) -> None:
        """保存角色配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.roles, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            print(f" 保存角色配置失败: {e}")
    
    def get_role_summary(self) -> str:
        """
        获取所有角色的摘要信息
        
        Returns:
            格式化的角色摘要字符串
        """
        summary_lines = ["# 可用角色列表\n"]
        
        for base_type, base_config in self.roles.items():
            summary_lines.append(f"\n## {base_type}")
            summary_lines.append(f"描述: {base_config.get('description', 'N/A')}\n")
            
            roles = base_config.get("roles", {})
            for role_id, role_config in roles.items():
                summary_lines.append(f"  - **{role_id}**: {role_config.get('name', 'N/A')}")
                summary_lines.append(f"    描述: {role_config.get('description', 'N/A')}")
                keywords = role_config.get('keywords', [])
                if keywords:
                    summary_lines.append(f"    关键词: {', '.join(keywords)}")
                summary_lines.append("")
        
        return "\n".join(summary_lines)
    
    def parse_full_role_id(self, full_id: str) -> tuple:
        """
        解析完整角色ID
        
        Args:
            full_id: 完整角色ID (格式: "V2_设计总监_2-1")
        
        Returns:
            (base_type, role_id) 元组
        """
        parts = full_id.split("_")
        if len(parts) >= 3:
            # 处理类似 "V2_设计总监_2-1" 的格式
            role_id = parts[-1]
            base_type = "_".join(parts[:-1])
            return base_type, role_id
        else:
            raise ValueError(f"无效的角色ID格式: {full_id}")


# 使用示例
if __name__ == "__main__":
    # 创建角色管理器
    manager = RoleManager()
    
    # 获取所有角色
    print("\n所有角色:")
    print(manager.get_role_summary())
    
    # 搜索角色
    print("\n搜索'建筑'相关角色:")
    results = manager.search_roles_by_keywords("建筑")
    for role in results:
        print(f"  - {role['full_id']}: {role['name']} (匹配分数: {role['match_score']})")

