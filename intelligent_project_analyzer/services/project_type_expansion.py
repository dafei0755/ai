"""
项目类型自动扩展服务 (v1.0)

功能：
1. 监听用户输入，识别未被现有类型覆盖的场景 → 产生候选类型
2. 扫描爬虫知识库（sf_knowledge），发现高频新类型模式
3. 将候选写入 project_type_candidates 表，等待管理员审核
4. 审核通过后写入 data/project_type_extensions.json，热重载生效

触发点：
  - requirements_analyst._infer_project_type() 返回 None 时
  - 爬虫采集到大量某类词汇时，由外部调度器调用 scan_crawler_data()
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

# ── 路径常量 ─────────────────────────────────────────────────────────────────
_BASE_DIR = Path(__file__).parent.parent.parent
EXTENSIONS_FILE = _BASE_DIR / "data" / "project_type_extensions.json"
EXTENSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 扩展类型持久化
# ============================================================================


def load_extensions() -> Dict[str, Dict[str, Any]]:
    """从 JSON 文件加载已审批的扩展类型（可热重载）"""
    if not EXTENSIONS_FILE.exists():
        return {}
    try:
        with open(EXTENSIONS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("types", {})
    except Exception as e:
        logger.error(f"[TypeExpansion] 加载扩展文件失败: {e}")
        return {}


def save_extension(type_id: str, type_config: Dict[str, Any]) -> bool:
    """
    将已审批的类型写入扩展文件。
    调用后需触发 ProjectTypeDetector 重新初始化（或等待下次请求时自动加载）。
    """
    try:
        existing = {}
        if EXTENSIONS_FILE.exists():
            with open(EXTENSIONS_FILE, encoding="utf-8") as f:
                existing = json.load(f)

        if "types" not in existing:
            existing["types"] = {}
        if "meta" not in existing:
            existing["meta"] = {}

        existing["types"][type_id] = type_config
        existing["meta"]["last_updated"] = datetime.utcnow().isoformat()
        existing["meta"]["total"] = len(existing["types"])

        with open(EXTENSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        logger.info(f"[TypeExpansion] 已写入扩展类型: {type_id}")
        return True
    except Exception as e:
        logger.error(f"[TypeExpansion] 写入扩展文件失败: {e}")
        return False


def remove_extension(type_id: str) -> bool:
    """从扩展文件中删除某个类型（拒绝后清理）"""
    try:
        if not EXTENSIONS_FILE.exists():
            return False
        with open(EXTENSIONS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if type_id in data.get("types", {}):
            del data["types"][type_id]
            data["meta"]["last_updated"] = datetime.utcnow().isoformat()
            data["meta"]["total"] = len(data["types"])
            with open(EXTENSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[TypeExpansion] 已移除扩展类型: {type_id}")
        return True
    except Exception as e:
        logger.error(f"[TypeExpansion] 移除扩展类型失败: {e}")
        return False


# ============================================================================
# 候选类型收集器
# ============================================================================


class ProjectTypeCandidateCollector:
    """
    项目类型候选收集器

    职责：
    - 从用户会话文本提取「可能是新类型」的信号词
    - 对爬虫数据做频率分析，发现高频未覆盖模式
    - 生成候选条目并写入数据库（待管理员审核）
    """

    # 触发「未识别类型」记录的最低词频阈值
    MIN_KEYWORD_FREQ = 3

    def __init__(self):
        from .project_type_detector import ProjectTypeDetector

        self.detector = ProjectTypeDetector()
        logger.info("[TypeExpansion] 候选收集器已初始化")

    # ── 从用户会话收集 ─────────────────────────────────────────────────────────

    def collect_from_session(
        self,
        session_id: str,
        user_text: str,
        structured_data: Dict[str, Any] | None = None,
    ) -> int | None:
        """
        用户输入触发收集：当检测器无法匹配已有类型时，尝试归纳新类型。

        Args:
            session_id: 会话ID（用于溯源）
            user_text: 用户原始输入
            structured_data: 已解析结构化数据（可选）

        Returns:
            创建的候选ID，若无需创建返回 None
        """
        project_type, confidence, reason = self.detector.detect(user_text)

        # 只在「无匹配」或「低置信度」时收集候选
        if project_type is not None and confidence >= 0.6:
            return None

        # 尝试提取关键词
        keywords = self._extract_keywords(user_text)
        if len(keywords) < 2:
            return None  # 信息不足，不值得记录

        # 生成候选条目
        candidate = {
            "type_id_suggestion": self._suggest_type_id(keywords),
            "name_zh": self._suggest_name_zh(user_text, keywords),
            "name_en": "",
            "description": f"来自会话 {session_id} 的自动发现",
            "source": "user_input",
            "source_session_id": session_id,
            "sample_inputs": [user_text[:200]],
            "suggested_keywords": keywords[:10],
            "suggested_secondary_keywords": [],
            "confidence_score": 0.3 if project_type is None else confidence,
        }

        candidate_id = self._save_candidate(candidate)
        if candidate_id:
            logger.info(
                f"[TypeExpansion] 记录未识别类型候选 (session={session_id}, " f"suggestion={candidate['type_id_suggestion']})"
            )
        return candidate_id

    # ── 从爬虫知识库收集 ──────────────────────────────────────────────────────

    def scan_crawler_data(self, limit: int = 200) -> List[Dict[str, Any]]:
        """
        扫描爬虫采集的项目数据，统计未覆盖类型模式。

        Returns:
            候选类型列表（不直接保存，由调用方决定是否入库）
        """
        try:
            from .sf_knowledge_loader import SFKnowledgeLoader

            loader = SFKnowledgeLoader()
            projects = loader.load_projects(limit=limit)
        except Exception as e:
            logger.warning(f"[TypeExpansion] 无法加载爬虫数据: {e}")
            return []

        # 统计每个项目的未识别情况
        unmatched: Dict[str, List[str]] = {}
        for proj in projects:
            text = " ".join(
                [
                    proj.get("title", ""),
                    proj.get("description", ""),
                    proj.get("category", ""),
                ]
            )
            project_type, confidence, _ = self.detector.detect(text)
            if project_type is None or confidence < 0.5:
                kws = self._extract_keywords(text)
                cluster = kws[0] if kws else "unknown"
                unmatched.setdefault(cluster, []).append(text[:100])

        # 筛选高频未覆盖模式
        candidates = []
        for cluster, samples in unmatched.items():
            if len(samples) >= self.MIN_KEYWORD_FREQ:
                candidates.append(
                    {
                        "type_id_suggestion": f"crawler_{cluster}",
                        "name_zh": cluster,
                        "name_en": "",
                        "description": f"爬虫数据中高频出现（{len(samples)}次）",
                        "source": "crawler",
                        "source_session_id": None,
                        "sample_inputs": samples[:5],
                        "suggested_keywords": [cluster],
                        "suggested_secondary_keywords": [],
                        "confidence_score": min(0.9, 0.3 + len(samples) * 0.05),
                        "occurrence_count": len(samples),
                    }
                )

        logger.info(f"[TypeExpansion] 爬虫扫描完成: {len(candidates)} 个候选模式")
        return candidates

    # ── 合并候选（去重 + 频次累加）─────────────────────────────────────────────

    def merge_or_save_candidate(self, candidate: Dict[str, Any]) -> int | None:
        """
        若数据库中已有相似候选（相同 type_id_suggestion），则累加次数；否则新建。
        """
        try:
            from ..learning.database_manager import get_db_manager

            db = get_db_manager()
            existing = db.get_type_candidate_by_suggestion(candidate["type_id_suggestion"])
            if existing:
                db.increment_type_candidate_count(existing["id"])
                return existing["id"]
            return self._save_candidate(candidate)
        except Exception as e:
            logger.error(f"[TypeExpansion] 合并候选失败: {e}")
            return None

    async def async_infer_type_with_llm(
        self,
        user_text: str,
        session_id: str = "",
    ) -> Dict[str, Any]:
        """
        Step 8: LLM 异步回退推理。

        当规则检测器置信度低（< 0.6）且无法确定项目类型时，调用 LLM 对用户原始
        文本进行项目类型分类，并将结果作为候选入库以供管理员参考。

        调用方式（fire-and-forget）：
            asyncio.create_task(collector.async_infer_type_with_llm(text, session_id))

        Args:
            user_text:  原始用户输入
            session_id: 会话 ID（用于日志追踪）

        Returns:
            {
                "status": "success" | "skipped" | "error",
                "inferred_type_id": str | None,
                "inferred_name_zh": str | None,
                "candidate_id": int | None,
            }
        """
        if not user_text or len(user_text.strip()) < 5:
            return {"status": "skipped", "reason": "input_too_short"}

        try:
            # 惰性导入，避免循环依赖
            from ..agents.llm_factory import get_default_llm  # type: ignore[import]

            llm = get_default_llm()

            prompt = (
                "你是一名专业室内设计分类助手。请根据以下客户描述，判断其项目类型。\n"
                '只需返回 JSON，格式：{"type_id": "<英文下划线ID>", '
                '"name_zh": "<中文名称>", "confidence": <0-1浮点>}\n\n'
                f"客户描述：{user_text.strip()}"
            )

            raw = await llm.ainvoke(prompt)
            # 兼容字符串或 BaseMessage 返回值
            raw_text: str = raw if isinstance(raw, str) else getattr(raw, "content", str(raw))

            import json
            import re

            json_match = re.search(r"\{[^{}]+\}", raw_text, re.DOTALL)
            if not json_match:
                logger.warning(f"[TypeExpansion] LLM 返回无法解析: {raw_text[:120]}")
                return {"status": "error", "reason": "no_json_in_response"}

            parsed = json.loads(json_match.group())
            type_id_sug: str = parsed.get("type_id", "llm_unknown")
            name_zh_sug: str = parsed.get("name_zh", "LLM推断类型")
            llm_confidence: float = float(parsed.get("confidence", 0.5))

            candidate: Dict[str, Any] = {
                "type_id_suggestion": f"llm_{type_id_sug}",
                "name_zh_suggestion": name_zh_sug,
                "source_text": user_text[:300],
                "session_id": session_id,
                "llm_confidence": llm_confidence,
                "discovery_method": "llm_fallback",
                "occurrence_count": 1,
            }

            cid = self.merge_or_save_candidate(candidate)
            logger.info(
                f"[TypeExpansion] LLM 推断完成: '{name_zh_sug}' "
                f"({type_id_sug}, conf={llm_confidence:.2f}) → candidate_id={cid}"
            )
            return {
                "status": "success",
                "inferred_type_id": type_id_sug,
                "inferred_name_zh": name_zh_sug,
                "candidate_id": cid,
            }

        except ImportError:
            logger.debug("[TypeExpansion] LLM 工厂未配置，跳过 LLM 回退")
            return {"status": "skipped", "reason": "llm_not_configured"}
        except Exception as e:
            logger.error(f"[TypeExpansion] LLM 推断失败 (session={session_id}): {e}")
            return {"status": "error", "error": str(e)}

    # ── 私有帮助方法 ──────────────────────────────────────────────────────────

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本提取名词性关键词（简单规则，不依赖 NLP）"""
        # 常用空间/场所词
        space_words = [
            "展厅",
            "展馆",
            "展览馆",
            "旗舰店",
            "体验店",
            "概念店",
            "实验室",
            "工坊",
            "工作室",
            "车间",
            "厂房",
            "仓库",
            "粮仓",
            "炮台",
            "教堂",
            "礼堂",
            "剧场",
            "影院",
            "浴池",
            "泳池",
            "澡堂",
            "集装箱",
            "货柜",
            "移动",
            "临时",
            "帐篷",
            "穹顶",
            "农场",
            "牧场",
            "渔村",
            "渔港",
            "茶园",
            "茶室",
            "会所",
            "私人",
            "宴会",
            "婚宴",
            "婚礼",
            "幼儿园",
            "托育",
            "早教",
            "培训班",
            "宠物",
            "宠物店",
            "宠物医院",
            "汽车",
            "4S店",
            "新能源",
            "充电站",
            "数字",
            "元宇宙",
            "沉浸式",
            "虚拟",
        ]
        found = [w for w in space_words if w in text]
        return found

    def _suggest_type_id(self, keywords: List[str]) -> str:
        """根据关键词生成英文ID建议（供管理员参考，非最终值）"""
        mapping = {
            "展厅": "showroom",
            "展馆": "exhibition_hall",
            "旗舰店": "flagship_store",
            "体验店": "experience_store",
            "工坊": "workshop",
            "厂房": "factory",
            "临时": "temporary",
            "移动": "mobile",
            "农场": "farm",
            "幼儿园": "childcare",
            "宠物": "pet_facility",
            "汽车": "auto_showroom",
            "数字": "digital_space",
            "沉浸式": "immersive_space",
        }
        for kw in keywords:
            if kw in mapping:
                return f"auto_{mapping[kw]}"
        return f"auto_{'_'.join(keywords[:2])}" if keywords else "auto_unknown"

    def _suggest_name_zh(self, text: str, keywords: List[str]) -> str:
        """生成中文名建议"""
        if keywords:
            return keywords[0] + "空间"
        return "待命名空间类型"

    def _save_candidate(self, candidate: Dict[str, Any]) -> int | None:
        """写入数据库"""
        try:
            from ..learning.database_manager import get_db_manager

            db = get_db_manager()
            return db.add_type_candidate(candidate)
        except Exception as e:
            logger.error(f"[TypeExpansion] 保存候选失败: {e}")
            return None


# ============================================================================
# 注册表写入器（管理员审批后调用）
# ============================================================================


class ProjectTypeRegistryWriter:
    """
    将管理员审批通过的候选类型写入扩展 JSON，触发注册表热重载。
    不修改 Python 源码，安全可回滚。
    """

    @staticmethod
    def write_approved_type(candidate_data: Dict[str, Any]) -> bool:
        """
        构建符合 PROJECT_TYPE_REGISTRY 格式的条目并写入扩展文件。

        Args:
            candidate_data: 候选记录（含管理员填写的 type_id, name_zh 等）
        """
        type_id = candidate_data.get("type_id") or candidate_data.get("type_id_suggestion", "")
        if not type_id:
            logger.error("[TypeExpansion] 缺少 type_id，无法写入")
            return False

        # 构建注册表条目
        type_config = {
            "name": candidate_data.get("name_zh", type_id),
            "name_en": candidate_data.get("name_en", ""),
            "keywords": candidate_data.get("approved_keywords") or candidate_data.get("suggested_keywords", []),
            "secondary_keywords": candidate_data.get("approved_secondary_keywords")
            or candidate_data.get("suggested_secondary_keywords", []),
            "priority": int(candidate_data.get("priority", 6)),
            "min_secondary_hits": int(candidate_data.get("min_secondary_hits", 0)),
            "include_in_prompt": bool(candidate_data.get("include_in_prompt", True)),
            "_source": "admin_approved",
            "_created_at": datetime.utcnow().isoformat(),
        }

        success = save_extension(type_id, type_config)

        if success:
            # 1. 通知检测器热重载
            try:
                from .project_type_detector import ProjectTypeDetector

                ProjectTypeDetector.reload_extensions()
            except Exception as e:
                logger.warning(f"[TypeExpansion] 热重载失败（下次请求时自动加载）: {e}")

            # 2. 触发三层覆盖度审计：提醒本体论 / Few-shot 是否需要跟进
            try:
                report = KnowledgeCoverageAuditor.run_full_audit()
                if type_id in report.get("ontology_missing", []):
                    logger.warning(
                        f"[CoverageAlert] ⚠️  新类型 '{type_id}' 在 ontology.yaml 中没有框架！"
                        f" 建议运行: KnowledgeCoverageAuditor.generate_ontology_draft('{type_id}')"
                    )
                if type_id in report.get("few_shot_low_coverage", []):
                    logger.warning(
                        f"[CoverageAlert] 📋  新类型 '{type_id}' 的 few-shot 覆盖薄弱！"
                        f" 建议运行: KnowledgeCoverageAuditor.generate_few_shot_draft('{type_id}')"
                    )
            except Exception as e:
                logger.warning(f"[TypeExpansion] 覆盖度审计执行失败: {e}")

        return success

    @staticmethod
    def revoke_type(type_id: str) -> bool:
        """撤销已批准的扩展类型"""
        success = remove_extension(type_id)
        if success:
            try:
                from .project_type_detector import ProjectTypeDetector

                ProjectTypeDetector.reload_extensions()
            except Exception:
                pass
        return success


# ============================================================================
# 三层知识体系覆盖度审计器
# ============================================================================


class KnowledgeCoverageAuditor:
    """
    检查 project_type_detector（SSOT）与 ontology.yaml / few-shot registry
    之间的覆盖度缺口，并生成缺失提醒。

    调用时机：
    - write_approved_type() 写入新类型后自动触发
    - 管理员后台可手动调用 run_full_audit()
    - 定时任务每日执行一次（可选）
    """

    _BASE = Path(__file__).parent.parent.parent
    _ONTOLOGY_PATH = _BASE / "intelligent_project_analyzer" / "knowledge_base" / "ontology.yaml"
    _REGISTRY_PATH = (
        _BASE / "intelligent_project_analyzer" / "config" / "prompts" / "few_shot_examples" / "examples_registry.yaml"
    )

    @classmethod
    def run_full_audit(cls) -> Dict[str, Any]:
        """
        对比三层体系，返回缺口报告。

        Returns:
            {
              "ontology_missing": [type_ids],   # 有类型但无本体论框架
              "ontology_orphans": [type_ids],   # 有框架但类型已不存在
              "few_shot_low_coverage": [type_ids],  # few-shot 覆盖薄弱的类型
              "summary": str,
            }
        """
        from .project_type_detector import PROJECT_TYPE_REGISTRY, _load_extension_registry

        # 当前全部类型（含热重载扩展）
        all_types = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
        detector_ids = set(all_types.keys())

        # 本体论框架 keys
        ont_ids = cls._get_ontology_ids()

        # Few-shot 覆盖的 space_type 标签
        few_shot_space_tags = cls._get_few_shot_space_tags()

        # 计算缺口
        ontology_missing = sorted(detector_ids - ont_ids)
        ontology_orphans = sorted(ont_ids - detector_ids)

        # few-shot "薄弱"判断：某类型 ID 或其 name 未出现在任何示例的 space_type 中
        few_shot_low = []
        for tid in sorted(detector_ids):
            type_name = all_types[tid].get("name", "")
            # 简单启发：类型 ID 的主词 / name 中有没有对应 space_type tag
            id_words = set(tid.split("_"))
            name_words = set(type_name.replace("/", " ").replace("、", " ").split())
            overlap = id_words & few_shot_space_tags | name_words & few_shot_space_tags
            if not overlap:
                few_shot_low.append(tid)

        summary_lines = [
            f"[覆盖度审计] 检测器类型: {len(detector_ids)}",
            f"  本体论框架: {len(ont_ids)} (缺 {len(ontology_missing)}, 孤儿 {len(ontology_orphans)})",
            f"  Few-shot 薄弱覆盖: {len(few_shot_low)} 个类型",
        ]
        if ontology_missing:
            summary_lines.append("  ⚠️  本体论缺失: " + ", ".join(ontology_missing))
        if ontology_orphans:
            summary_lines.append("  🗑️  本体论孤儿: " + ", ".join(ontology_orphans))
        if few_shot_low:
            summary_lines.append("  📋  Few-shot 弱覆盖: " + ", ".join(few_shot_low))

        report = {
            "ontology_missing": ontology_missing,
            "ontology_orphans": ontology_orphans,
            "few_shot_low_coverage": few_shot_low,
            "detector_count": len(detector_ids),
            "ontology_count": len(ont_ids),
            "summary": "\n".join(summary_lines),
        }

        # 总是打印到日志，方便运维感知
        for line in summary_lines:
            logger.info(line)

        # 将报告写入 data/coverage_audit.json（方便前端展示）
        try:
            audit_file = cls._BASE / "data" / "coverage_audit.json"
            audit_file.parent.mkdir(parents=True, exist_ok=True)
            import json as _json

            with open(audit_file, "w", encoding="utf-8") as f:
                _json.dump(
                    {**report, "audited_at": datetime.utcnow().isoformat()},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            logger.warning(f"[CoverageAudit] 写入审计报告失败: {e}")

        return report

    @classmethod
    def _get_ontology_ids(cls) -> set:
        """从 ontology.yaml 提取 ontology_frameworks 的 key 集合（排除 meta）"""
        try:
            import yaml as _yaml

            with open(cls._ONTOLOGY_PATH, encoding="utf-8") as f:
                data = _yaml.safe_load(f) or {}
            keys = set(data.get("ontology_frameworks", {}).keys())
            keys.discard("meta_framework")
            return keys
        except Exception as e:
            logger.warning(f"[CoverageAudit] 读取 ontology.yaml 失败: {e}")
            return set()

    @classmethod
    def _get_few_shot_space_tags(cls) -> set:
        """从 examples_registry.yaml 收集所有 tags_matrix.space_type 标签"""
        try:
            import yaml as _yaml

            with open(cls._REGISTRY_PATH, encoding="utf-8") as f:
                data = _yaml.safe_load(f) or {}
            tags: set = set()
            for ex in data.get("examples", []):
                st = ex.get("tags_matrix", {}).get("space_type", [])
                if isinstance(st, list):
                    tags.update(st)
                elif isinstance(st, str):
                    tags.add(st)
            return tags
        except Exception as e:
            logger.warning(f"[CoverageAudit] 读取 few-shot registry 失败: {e}")
            return set()

    @classmethod
    def generate_ontology_draft(cls, type_id: str, llm_model=None) -> str | None:
        """
        用 LLM 为缺失的 project_type 生成 ontology.yaml 草稿（YAML 片段）。

        设计原则：
        - 生成的是"待人工审核的草稿"，不自动写入 ontology.yaml
        - 参考现有框架结构作为格式指导
        - 写入 data/ontology_drafts/<type_id>.yaml，供管理员复制审核

        Returns:
            生成的 YAML 字符串，或 None（LLM 不可用时）
        """
        from .project_type_detector import PROJECT_TYPE_REGISTRY, _load_extension_registry

        all_types = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
        type_info = all_types.get(type_id)
        if not type_info:
            logger.warning(f"[OntologyDraft] 类型 {type_id} 不在注册表中")
            return None

        # 读取一个现有框架作为结构示例
        try:
            import yaml as _yaml

            with open(cls._ONTOLOGY_PATH, encoding="utf-8") as f:
                ont_data = _yaml.safe_load(f) or {}
            example_framework = ont_data.get("ontology_frameworks", {}).get("healthcare_wellness", {})  # 结构相对完整的一个
            example_yaml = _yaml.dump(
                {"healthcare_wellness": example_framework}, allow_unicode=True, default_flow_style=False
            )[
                :1500
            ]  # 截断，只用来示意结构
        except Exception:
            example_yaml = ""

        prompt = f"""你是资深室内/建筑设计顾问，正在构建一套设计分析本体论框架。

## 任务
为项目类型 `{type_id}` 生成 ontology.yaml 框架草稿，格式与下面的参考框架完全一致。

## 项目类型信息
- ID: {type_id}
- 中文名: {type_info.get('name', '')}
- 主要关键词: {', '.join(type_info.get('keywords', [])[:8])}
- 说明: 这是一个设计项目分析系统，需要为该类型定义3-5个分析维度，每个维度含2-3个分析参数。

## 参考框架结构（healthcare_wellness 节选）
```yaml
{example_yaml}
```

## 要求
1. 生成3-5个该类型最重要的分析维度（category key）
2. 每个维度包含2-3个参数，参数包含：name（中英文）、description、ask_yourself（3个追问）、examples（4个案例）
3. 严格使用与参考框架相同的 YAML 结构
4. 只输出 YAML 片段，从 `  {type_id}:` 开始，不要有 ```yaml 代码块标记
5. 语言：中文描述 + 括号内英文
"""

        try:
            if llm_model is None:
                from .llm_factory import LLMFactory

                llm_model = LLMFactory.create_llm(temperature=0.4)

            from langchain_core.messages import HumanMessage

            response = llm_model.invoke([HumanMessage(content=prompt)])
            draft_yaml = response.content if hasattr(response, "content") else str(response)

            # 保存草稿
            draft_dir = cls._BASE / "data" / "ontology_drafts"
            draft_dir.mkdir(parents=True, exist_ok=True)
            draft_file = draft_dir / f"{type_id}.yaml"
            with open(draft_file, "w", encoding="utf-8") as f:
                f.write("# 自动生成草稿 - 请人工审核后复制到 ontology.yaml\n")
                f.write(f"# 生成时间: {datetime.utcnow().isoformat()}\n\n")
                f.write(draft_yaml)

            logger.info(f"[OntologyDraft] 草稿已写入: {draft_file}")
            return draft_yaml

        except Exception as e:
            logger.error(f"[OntologyDraft] LLM 生成失败: {e}")
            return None

    @classmethod
    def generate_few_shot_draft(cls, type_id: str, llm_model=None) -> str | None:
        """
        用 LLM 为缺失的 project_type 生成 few-shot registry 条目草稿。

        不生成完整的 YAML example 文件（那需要真实项目案例），
        只生成 examples_registry.yaml 的 entry（包含 tags_matrix）。

        写入 data/few_shot_drafts/<type_id>_registry_entry.yaml
        """
        from .project_type_detector import PROJECT_TYPE_REGISTRY, _load_extension_registry

        all_types = {**PROJECT_TYPE_REGISTRY, **_load_extension_registry()}
        type_info = all_types.get(type_id)
        if not type_info:
            return None

        # 读取一个现有 registry 条目作为格式参考
        try:
            import yaml as _yaml

            with open(cls._REGISTRY_PATH, encoding="utf-8") as f:
                reg_data = _yaml.safe_load(f) or {}
            examples = reg_data.get("examples", [])
            # 取第一个作为格式示例
            ref_example = _yaml.dump(examples[0], allow_unicode=True, default_flow_style=False) if examples else ""
        except Exception:
            ref_example = ""

        prompt = f"""你是室内/建筑设计领域专家，正在维护一套 few-shot 示例注册表。

## 任务
为项目类型 `{type_id}` 生成 examples_registry.yaml 的条目草稿。

## 项目类型信息
- ID: {type_id}
- 中文名: {type_info.get('name', '')}
- 主要关键词: {', '.join(type_info.get('keywords', [])[:8])}

## 参考格式（一个现有 registry 条目）
```yaml
{ref_example[:1200]}
```

## 要求
1. 生成1个典型案例的 registry 条目（id, name, file, tags_matrix, feature_vector）
2. tags_matrix 必须包含7个维度：space_type, scale, design_direction, user_profile, challenge_type, methodology, phase
3. file 字段填写建议的文件名（如 `{type_id}_01.yaml`），实际文件需要人工创建
4. 在条目顶部用注释说明"这是草稿，file 对应的 YAML 需要人工补充真实案例"
5. 只输出 YAML，不要使用代码块标记
"""

        try:
            if llm_model is None:
                from .llm_factory import LLMFactory

                llm_model = LLMFactory.create_llm(temperature=0.4)

            from langchain_core.messages import HumanMessage

            response = llm_model.invoke([HumanMessage(content=prompt)])
            draft_yaml = response.content if hasattr(response, "content") else str(response)

            draft_dir = cls._BASE / "data" / "few_shot_drafts"
            draft_dir.mkdir(parents=True, exist_ok=True)
            draft_file = draft_dir / f"{type_id}_registry_entry.yaml"
            with open(draft_file, "w", encoding="utf-8") as f:
                f.write("# 自动生成草稿 - 请人工审核后复制到 examples_registry.yaml\n")
                f.write("# 注意: file 字段对应的 YAML 文件需要人工补充真实案例\n")
                f.write(f"# 生成时间: {datetime.utcnow().isoformat()}\n\n")
                f.write(draft_yaml)

            logger.info(f"[FewShotDraft] 草稿已写入: {draft_file}")
            return draft_yaml

        except Exception as e:
            logger.error(f"[FewShotDraft] LLM 生成失败: {e}")
            return None
