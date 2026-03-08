"""
智能 Few-Shot 选择器 - Phase 1 Intelligence Evolution

基于 sentence-transformers + FAISS 实现语义相似度驱动的
Few-Shot 示例检索，替代旧版关键词匹配（FewShotExampleLoader）。

特性：
- 多语言语义嵌入（paraphrase-multilingual-MiniLM-L12-v2）
- FAISS 向量索引（IVFFlat / 小型数据集用 Flat）
- 多样性筛选（余弦相似度去重）
- 磁盘缓存（首次构建后持久化，重启秒加载）
- 优雅降级（依赖缺失时自动回退到关键词匹配）
- UsageTracker 注入（可选）

Author: AI Architecture Team
Version: v1.0.0
Date: 2026-03-04
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

# ── 依赖检测 ──────────────────────────────────────────────────────────────
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    _HAS_ST = True
except ImportError:
    _HAS_ST = False
    np = None  # type: ignore[assignment]

try:
    import faiss  # type: ignore[import]

    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False

DEPENDENCIES_AVAILABLE: bool = _HAS_ST and _HAS_FAISS


# ── 数据模型 ──────────────────────────────────────────────────────────────


@dataclass
class SelectorConfig:
    """选择器配置"""

    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    cache_dir: Optional[Path] = None
    diversity_threshold: float = 0.7
    use_faiss: bool = True
    index_store_dir: Optional[Path] = None


@dataclass
class FewShotExample:
    """示例数据对象（统一接口，与旧版 FewShotExampleLoader 兼容）"""

    example_id: str
    description: str
    category: str
    user_request: str
    correct_output: str
    context: Dict[str, Any] = field(default_factory=dict)


# ── 智能选择器 ────────────────────────────────────────────────────────────


class IntelligentFewShotSelector:
    """
    语义感知的 Few-Shot 示例选择器

    当 sentence-transformers + FAISS 均可用时使用智能语义检索；
    否则自动回退到基线关键词匹配（与旧版 FewShotExampleLoader 行为一致）。
    """

    def __init__(
        self,
        config: Optional[SelectorConfig] = None,
        examples_dir: Optional[Path] = None,
        usage_tracker: Any = None,  # UsageTracker（可选注入）
    ) -> None:
        self.config = config or SelectorConfig()
        self.usage_tracker = usage_tracker

        # 示例来源目录
        if examples_dir is None:
            examples_dir = (
                Path(__file__).parent.parent
                / "config"
                / "prompts"
                / "few_shot_examples"
            )
        self.examples_dir = Path(examples_dir)

        # 传统角色示例目录（用于回退）
        self._legacy_examples_dir = (
            Path(__file__).parent.parent / "config" / "roles" / "examples"
        )

        # 索引缓存目录
        if self.config.index_store_dir is None:
            self.config.index_store_dir = (
                Path(__file__).parent.parent.parent
                / "data"
                / "intelligence"
                / "indexes"
            )
        self.config.index_store_dir.mkdir(parents=True, exist_ok=True)

        # 模型 & 索引
        self.model: Any = None
        self.indices: Dict[str, Any] = {}         # role_id -> FAISS index
        self.examples_cache: Dict[str, List[FewShotExample]] = {}  # role_id -> examples

        # 全量示例库（直接从 few_shot_examples/ 加载，不依赖角色）
        self._all_examples: List[FewShotExample] = []
        self._all_examples_loaded = False

        if DEPENDENCIES_AVAILABLE:
            self._load_model()
        else:
            logger.warning(
                "[IntelligentFewShotSelector] 依赖缺失, 已设为降级模式. "
                "安装方法: pip install sentence-transformers==2.3.1 faiss-cpu==1.7.4"
            )

    # ── 模型加载 ────────────────────────────────────────────────────────

    def _load_model(self) -> None:
        """加载 sentence-transformer 模型"""
        try:
            cache_dir = self.config.cache_dir
            kwargs: Dict[str, Any] = {}
            if cache_dir:
                Path(cache_dir).mkdir(parents=True, exist_ok=True)
                kwargs["cache_folder"] = str(cache_dir)

            logger.info(
                f"[IntelligentFewShotSelector] 加载嵌入模型: {self.config.model_name}"
            )
            self.model = SentenceTransformer(self.config.model_name, **kwargs)
            logger.info("[IntelligentFewShotSelector] 模型加载完成")
        except Exception as e:
            logger.error(f"[IntelligentFewShotSelector] 模型加载失败: {e}")
            self.model = None

    # ── 示例加载 ────────────────────────────────────────────────────────

    def _load_all_examples(self) -> List[FewShotExample]:
        """从 few_shot_examples/ 目录加载所有 YAML 示例"""
        if self._all_examples_loaded:
            return self._all_examples

        examples: List[FewShotExample] = []
        if not self.examples_dir.exists():
            logger.warning(f"[IntelligentFewShotSelector] 示例目录不存在: {self.examples_dir}")
            self._all_examples_loaded = True
            return examples

        for yaml_file in sorted(self.examples_dir.glob("*.yaml")):
            if yaml_file.name == "examples_registry.yaml":
                continue
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                example_block = data.get("example", data)
                project_info = example_block.get("project_info", {})
                ideal_tasks = example_block.get("ideal_tasks", [])

                description = project_info.get("description", "")
                if isinstance(description, str):
                    description = description.strip()

                # 把任务标题和描述拼接成 user_request
                task_texts = []
                for task in (ideal_tasks or []):
                    title = task.get("title", "")
                    desc = task.get("description", "")
                    if title:
                        task_texts.append(title)
                    if desc and isinstance(desc, str):
                        task_texts.append(desc.strip()[:200])

                user_request = project_info.get("name", yaml_file.stem)
                if project_info.get("name"):
                    user_request = project_info["name"]

                correct_output = json.dumps(
                    {"tasks": [t.get("title", "") for t in (ideal_tasks or [])]},
                    ensure_ascii=False,
                )

                example = FewShotExample(
                    example_id=yaml_file.stem,
                    description=description[:200] if description else yaml_file.stem,
                    category=yaml_file.stem.rsplit("_", 1)[0] if "_" in yaml_file.stem else yaml_file.stem,
                    user_request=user_request,
                    correct_output=correct_output,
                    context={
                        "source_file": yaml_file.name,
                        "task_count": len(ideal_tasks or []),
                        "feature_vector": project_info.get("feature_vector", {}),
                    },
                )
                examples.append(example)

            except Exception as e:
                logger.warning(f"[IntelligentFewShotSelector] 跳过 {yaml_file.name}: {e}")

        self._all_examples = examples
        self._all_examples_loaded = True
        logger.info(f"[IntelligentFewShotSelector] 加载示例 {len(examples)} 条")
        return examples

    def _load_examples_for_role(self, role_id: str) -> List[FewShotExample]:
        """加载指定角色的示例（兼容旧版角色示例目录）"""
        if role_id in self.examples_cache:
            return self.examples_cache[role_id]

        # 1. 尝试角色专属目录（传统路径）
        legacy_file = self._legacy_examples_dir / f"{role_id.lower()}_examples.yaml"
        if legacy_file.exists():
            return self._parse_legacy_examples(legacy_file, role_id)

        # 2. 回退到全量示例库
        all_examples = self._load_all_examples()
        self.examples_cache[role_id] = all_examples
        return all_examples

    def _parse_legacy_examples(
        self, yaml_file: Path, role_id: str
    ) -> List[FewShotExample]:
        """解析旧版角色格式示例文件"""
        examples: List[FewShotExample] = []
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            for item in data.get("examples", []):
                examples.append(
                    FewShotExample(
                        example_id=item.get("id", str(len(examples))),
                        description=item.get("description", ""),
                        category=item.get("category", ""),
                        user_request=item.get("user_request", ""),
                        correct_output=item.get("correct_output", ""),
                        context=item.get("context", {}),
                    )
                )
        except Exception as e:
            logger.warning(f"[IntelligentFewShotSelector] 解析旧版示例失败 {yaml_file}: {e}")

        self.examples_cache[role_id] = examples
        return examples

    # ── 索引构建 ────────────────────────────────────────────────────────

    def build_index_for_role(self, role_id: str) -> None:
        """
        为指定角色构建（或从缓存加载）FAISS 索引

        Args:
            role_id: 如 "V2_0"
        """
        # 尝试从磁盘缓存加载
        cache_index = self.config.index_store_dir / f"{role_id}.faiss"
        cache_meta = self.config.index_store_dir / f"{role_id}.pkl"

        if cache_index.exists() and cache_meta.exists():
            try:
                if DEPENDENCIES_AVAILABLE and self.config.use_faiss:
                    self.indices[role_id] = faiss.read_index(str(cache_index))
                with open(cache_meta, "rb") as f:
                    raw = pickle.load(f)

                # 兼容外部脚本（build_all_indexes.py）保存的 dict 列表
                examples_loaded: List[FewShotExample] = []
                for item in raw:
                    if isinstance(item, FewShotExample):
                        examples_loaded.append(item)
                    elif isinstance(item, dict):
                        examples_loaded.append(
                            FewShotExample(
                                example_id=item.get("id", item.get("example_id", "")),
                                description=item.get("description", ""),
                                category=item.get("category", ""),
                                user_request=item.get("user_request", item.get("id", "")),
                                correct_output=item.get("correct_output", ""),
                                context={
                                    k: v
                                    for k, v in item.items()
                                    if k not in ("id", "example_id", "description", "category",
                                                 "user_request", "correct_output", "embedding_text")
                                },
                            )
                        )

                self.examples_cache[role_id] = examples_loaded
                logger.info(
                    f"[IntelligentFewShotSelector] 从缓存加载索引: {role_id} "
                    f"({len(examples_loaded)} 个示例)"
                )
                return
            except Exception as e:
                logger.warning(f"[IntelligentFewShotSelector] 缓存加载失败，重新构建: {e}")

        # 加载示例
        examples = self._load_examples_for_role(role_id)
        if not examples:
            logger.warning(f"[IntelligentFewShotSelector] 角色 {role_id} 无示例，跳过索引构建")
            return

        self.examples_cache[role_id] = examples

        if not DEPENDENCIES_AVAILABLE or self.model is None:
            logger.info(f"[IntelligentFewShotSelector] 降级模式，跳过 FAISS 索引: {role_id}")
            return

        # 构建嵌入
        texts = [
            f"{ex.user_request} {ex.description}"
            for ex in examples
        ]
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        embeddings = embeddings.astype("float32")

        # 构建 FAISS 索引
        if self.config.use_faiss and _HAS_FAISS:
            dim = embeddings.shape[1]
            if len(examples) >= 40:
                nlist = min(len(examples) // 4, 100)
                quantizer = faiss.IndexFlatL2(dim)
                index = faiss.IndexIVFFlat(quantizer, dim, nlist)
                index.train(embeddings)
            else:
                index = faiss.IndexFlatL2(dim)
            index.add(embeddings)
            self.indices[role_id] = index

            # 持久化
            faiss.write_index(index, str(cache_index))

        # 持久化示例元数据
        with open(cache_meta, "wb") as f:
            pickle.dump(examples, f)

        logger.info(
            f"[IntelligentFewShotSelector] 索引构建完成: {role_id} "
            f"({len(examples)} 条, dim={embeddings.shape[1]})"
        )

    # ── 检索 ────────────────────────────────────────────────────────────

    def select_relevant_examples(
        self,
        role_id: str,
        user_query: str,
        top_k: int = 3,
        category: Optional[str] = None,
        diversity_threshold: Optional[float] = None,
    ) -> List[FewShotExample]:
        """
        智能选择与查询最相关的 Few-Shot 示例

        Args:
            role_id: 角色 ID
            user_query: 用户查询文本
            top_k: 返回示例上限
            category: 按分类过滤（None = 不过滤）
            diversity_threshold: 多样性阈值（覆盖配置默认值）

        Returns:
            相关示例列表
        """
        # 确保索引已构建
        if role_id not in self.examples_cache:
            self.build_index_for_role(role_id)

        examples = self.examples_cache.get(role_id, [])
        if not examples:
            return []

        # 分类过滤
        if category:
            examples = [e for e in examples if category.lower() in e.category.lower()]

        if not examples:
            return []

        # 智能检索（依赖可用时）
        if DEPENDENCIES_AVAILABLE and self.model is not None and role_id in self.indices:
            selected = self._semantic_search(
                role_id=role_id,
                user_query=user_query,
                examples=examples,
                top_k=top_k,
                diversity_threshold=diversity_threshold or self.config.diversity_threshold,
            )
        else:
            # 降级：关键词匹配
            selected = self._keyword_match(user_query, examples, top_k)

        # 记录使用
        if self.usage_tracker and selected:
            try:
                self.usage_tracker.log_expert_usage(
                    role_id=role_id,
                    user_request=user_query,
                    selected_examples=[e.example_id for e in selected],
                )
            except Exception:
                pass

        return selected

    def _semantic_search(
        self,
        role_id: str,
        user_query: str,
        examples: List[FewShotExample],
        top_k: int,
        diversity_threshold: float,
    ) -> List[FewShotExample]:
        """FAISS 语义检索 + 多样性筛选"""
        query_vec = self.model.encode([user_query], convert_to_numpy=True, show_progress_bar=False)
        query_vec = query_vec.astype("float32")

        index = self.indices[role_id]
        k = min(top_k * 4, len(examples))  # 多取候选后再做多样性筛选

        if hasattr(index, "nprobe"):
            index.nprobe = 4

        _, indices_arr = index.search(query_vec, k)
        candidates = [examples[i] for i in indices_arr[0] if i < len(examples)]

        # 多样性筛选
        selected: List[FewShotExample] = []
        selected_vecs: List[Any] = []

        for candidate in candidates:
            if len(selected) >= top_k:
                break
            if not selected:
                selected.append(candidate)
                vec = self.model.encode(
                    [f"{candidate.user_request} {candidate.description}"],
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                selected_vecs.append(vec[0])
                continue

            # 计算与已选示例的最大余弦相似度
            candidate_vec = self.model.encode(
                [f"{candidate.user_request} {candidate.description}"],
                convert_to_numpy=True,
                show_progress_bar=False,
            )[0]

            max_sim = max(
                float(np.dot(candidate_vec, sv) / (
                    np.linalg.norm(candidate_vec) * np.linalg.norm(sv) + 1e-8
                ))
                for sv in selected_vecs
            )
            if max_sim < diversity_threshold:
                selected.append(candidate)
                selected_vecs.append(candidate_vec)

        return selected

    def _keyword_match(
        self,
        user_query: str,
        examples: List[FewShotExample],
        top_k: int,
    ) -> List[FewShotExample]:
        """降级：基于关键词重叠度匹配"""
        query_tokens = set(user_query.lower().split())

        scored: List[tuple[int, FewShotExample]] = []
        for ex in examples:
            text = f"{ex.user_request} {ex.description}".lower()
            text_tokens = set(text.split())
            score = len(query_tokens & text_tokens)
            scored.append((score, ex))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:top_k]]

    # ── 基线对比 ────────────────────────────────────────────────────────

    def compare_with_baseline(
        self,
        role_id: str,
        test_queries: List[str],
        top_k: int = 2,
    ) -> Dict[str, Any]:
        """
        对比智能检索与关键词匹配的结果

        Returns:
            {"intelligent": [[ids...], ...], "baseline": [[ids...], ...], "agreement_rate": float}
        """
        if role_id not in self.examples_cache:
            self.build_index_for_role(role_id)

        examples = self.examples_cache.get(role_id, [])

        intelligent_results: List[List[str]] = []
        baseline_results: List[List[str]] = []

        for query in test_queries:
            # 智能
            smart = self.select_relevant_examples(role_id=role_id, user_query=query, top_k=top_k)
            intelligent_results.append([e.example_id for e in smart])

            # 基线
            baseline = self._keyword_match(query, examples, top_k)
            baseline_results.append([e.example_id for e in baseline])

        # 一致率
        agree = 0
        total = len(test_queries)
        for smart_ids, base_ids in zip(intelligent_results, baseline_results):
            if set(smart_ids) == set(base_ids):
                agree += 1

        return {
            "intelligent": intelligent_results,
            "baseline": baseline_results,
            "agreement_rate": agree / total if total else 0.0,
        }
