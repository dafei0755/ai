#!/usr/bin/env python
"""
build_all_indexes.py  —  Few-Shot Phase 1 生产部署工具

遍历 config/prompts/few_shot_examples/ 目录下所有 YAML 示例文件，
使用 sentence-transformers 构建语义嵌入，再用 FAISS 构建向量索引，
并将索引文件序列化到 data/intelligence/indexes/ 目录。

用法：
    python scripts/build_all_indexes.py [--dry-run] [--model MODEL_NAME]

选项：
    --dry-run       仅扫描并打印文件清单，不实际构建
    --model NAME    指定嵌入模型（默认: paraphrase-multilingual-MiniLM-L12-v2）
    --force         强制重新构建（忽略已有缓存）
    --examples-dir  指定示例目录（默认自动探测）

退出码：
    0  全部成功
    1  部分或全部失败
"""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# ── 项目路径设置 ─────────────────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# ── 尝试导入依赖 ─────────────────────────────────────────────────────────
_DEPS_OK = True
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"[ERROR] sentence-transformers 未安装: {e}")
    print("       请运行: pip install sentence-transformers==2.3.1")
    _DEPS_OK = False

try:
    import faiss  # type: ignore[import]
except ImportError as e:
    print(f"[ERROR] faiss-cpu 未安装: {e}")
    print("       请运行: pip install faiss-cpu==1.7.4")
    _DEPS_OK = False

# ── 常量 ─────────────────────────────────────────────────────────────────
DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_EXAMPLES_DIR = _PROJECT_ROOT / "intelligent_project_analyzer" / "config" / "prompts" / "few_shot_examples"
DEFAULT_INDEX_DIR = _PROJECT_ROOT / "data" / "intelligence" / "indexes"

REGISTRY_FILE = "examples_registry.yaml"

# ── 示例解析 ─────────────────────────────────────────────────────────────


def parse_yaml_example(yaml_file: Path) -> Optional[Dict[str, Any]]:
    """
    解析单个示例 YAML，返回结构化记录。

    Returns:
        {
            "id": str,
            "description": str,
            "user_request": str,
            "embedding_text": str,   # 用于嵌入的拼接文本
            "task_titles": [str],
            "source_file": str,
        }
        或 None（解析失败时）
    """
    try:
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return None

        example_block = data.get("example", data)
        project_info = example_block.get("project_info", {})
        ideal_tasks = example_block.get("ideal_tasks", []) or []

        name = project_info.get("name", yaml_file.stem)
        description = project_info.get("description", "")
        if isinstance(description, str):
            description = description.strip()

        task_titles = [
            t.get("title", "")
            for t in ideal_tasks
            if isinstance(t, dict) and t.get("title")
        ]

        # 嵌入文本：项目名 + 描述前 300 字 + 前 5 个任务标题
        embedding_parts = [name]
        if description:
            embedding_parts.append(description[:300])
        embedding_parts.extend(task_titles[:5])
        embedding_text = " ".join(p for p in embedding_parts if p).strip()

        return {
            "id": yaml_file.stem,
            "description": description[:200] if description else yaml_file.stem,
            "user_request": name,
            "embedding_text": embedding_text,
            "task_titles": task_titles,
            "source_file": yaml_file.name,
            "feature_vector": project_info.get("feature_vector", {}),
        }

    except Exception as e:
        print(f"  [WARN] 跳过 {yaml_file.name}: {e}")
        return None


# ── 加载注册表 ────────────────────────────────────────────────────────────


def load_registry(examples_dir: Path) -> Dict[str, Any]:
    """加载 examples_registry.yaml，返回示例条目字典 {id -> meta}"""
    registry_file = examples_dir / REGISTRY_FILE
    registry_map: Dict[str, Any] = {}

    if not registry_file.exists():
        print(f"  [WARN] 注册表不存在: {registry_file}")
        return registry_map

    try:
        with open(registry_file, encoding="utf-8") as f:
            registry = yaml.safe_load(f)
        for item in registry.get("examples", []):
            if isinstance(item, dict) and "id" in item:
                registry_map[item["id"]] = item
    except Exception as e:
        print(f"  [WARN] 注册表解析失败: {e}")

    return registry_map


# ── 索引构建 ──────────────────────────────────────────────────────────────


def build_index(
    examples: List[Dict[str, Any]],
    model: Any,
    index_name: str,
    output_dir: Path,
    force: bool = False,
) -> Tuple[bool, str]:
    """
    为一批示例构建 FAISS 索引并序列化保存。

    Returns:
        (success, message)
    """
    index_path = output_dir / f"{index_name}.faiss"
    meta_path = output_dir / f"{index_name}.pkl"
    manifest_path = output_dir / f"{index_name}.json"

    if not force and index_path.exists() and meta_path.exists():
        return True, f"已存在（跳过）: {index_path.name}"

    texts = [ex["embedding_text"] for ex in examples]
    if not texts:
        return False, "无有效示例文本"

    # 编码
    t0 = time.time()
    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=32,
    )
    embeddings = embeddings.astype("float32")
    encode_ms = (time.time() - t0) * 1000

    # 构建 FAISS 索引
    dim = embeddings.shape[1]
    n = len(examples)

    if n >= 40:
        nlist = min(n // 4, 64)
        quantizer = faiss.IndexFlatL2(dim)
        index = faiss.IndexIVFFlat(quantizer, dim, nlist)
        index.train(embeddings)
        index_type = f"IVFFlat(nlist={nlist})"
    else:
        index = faiss.IndexFlatL2(dim)
        index_type = "FlatL2"

    index.add(embeddings)

    # 序列化
    faiss.write_index(index, str(index_path))
    with open(meta_path, "wb") as f:
        pickle.dump(examples, f)

    # 写 manifest（可读摘要）
    manifest = {
        "index_name": index_name,
        "built_at": time.strftime("%Y-%m-%d %Human:%M:%S"),
        "example_count": n,
        "embedding_dim": dim,
        "index_type": index_type,
        "model": model.get_sentence_embedding_dimension
        if hasattr(model, "get_sentence_embedding_dimension")
        else str(type(model).__name__),
        "examples": [
            {"id": ex["id"], "source_file": ex["source_file"]}
            for ex in examples
        ],
    }
    manifest["built_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if callable(manifest["model"]):
        manifest["model"] = dim
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return True, (
        f"✅ {index_name}: {n} 条示例, dim={dim}, "
        f"index={index_type}, encode={encode_ms:.0f}ms"
    )


# ── 主流程 ────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="构建 Few-Shot 示例 FAISS 索引"
    )
    parser.add_argument("--dry-run", action="store_true", help="仅扫描，不构建")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="嵌入模型名称")
    parser.add_argument("--force", action="store_true", help="强制重新构建")
    parser.add_argument("--examples-dir", type=Path, default=DEFAULT_EXAMPLES_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_INDEX_DIR)
    args = parser.parse_args()

    examples_dir: Path = args.examples_dir
    output_dir: Path = args.output_dir

    print("=" * 60)
    print("  Few-Shot Phase 1 — 索引构建工具")
    print("=" * 60)
    print(f"  示例目录: {examples_dir}")
    print(f"  输出目录: {output_dir}")
    print(f"  嵌入模型: {args.model}")
    print(f"  强制重建: {args.force}")
    print()

    # ── 检查目录 ──────────────────────────────────────────────────────
    if not examples_dir.exists():
        print(f"[ERROR] 示例目录不存在: {examples_dir}")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 扫描 YAML 文件 ────────────────────────────────────────────────
    yaml_files = sorted(
        f for f in examples_dir.glob("*.yaml") if f.name != REGISTRY_FILE
    )
    if not yaml_files:
        print("[ERROR] 未找到任何 YAML 示例文件")
        return 1

    print(f"  发现 {len(yaml_files)} 个示例文件:")
    for f in yaml_files:
        print(f"    • {f.name}")
    print()

    # ── 加载注册表 ────────────────────────────────────────────────────
    registry_map = load_registry(examples_dir)
    print(f"  注册表条目: {len(registry_map)} 个")

    if args.dry_run:
        print("\n[DRY-RUN] 未构建任何索引。")
        return 0

    # ── 依赖检查 ──────────────────────────────────────────────────────
    if not _DEPS_OK:
        print("\n[ERROR] 缺少必要依赖，中止构建。")
        return 1

    # ── 加载模型 ──────────────────────────────────────────────────────
    print(f"  加载嵌入模型: {args.model} ...")
    t_model = time.time()
    model = SentenceTransformer(args.model)
    print(f"  模型加载完成, 耗时 {time.time() - t_model:.1f}s\n")

    # ── 解析所有示例 ──────────────────────────────────────────────────
    all_examples: List[Dict[str, Any]] = []
    parse_errors = 0
    for yaml_file in yaml_files:
        parsed = parse_yaml_example(yaml_file)
        if parsed:
            # 附加注册表的 tags_matrix 信息
            if parsed["id"] in registry_map:
                parsed["tags_matrix"] = registry_map[parsed["id"]].get("tags_matrix", {})
            all_examples.append(parsed)
        else:
            parse_errors += 1

    print(f"  解析成功: {len(all_examples)} 条  失败: {parse_errors} 条\n")

    if not all_examples:
        print("[ERROR] 没有可用的示例")
        return 1

    # ── 构建全局索引（all_examples） ─────────────────────────────────
    results: List[Tuple[bool, str]] = []

    print("── 构建全局索引 (all_examples) ──")
    ok, msg = build_index(
        examples=all_examples,
        model=model,
        index_name="all_examples",
        output_dir=output_dir,
        force=args.force,
    )
    results.append((ok, msg))
    print(f"  {msg}")

    # ── 按 space_type 分类构建子索引 ─────────────────────────────────
    print("\n── 构建分类子索引 ──")
    category_map: Dict[str, List[Dict[str, Any]]] = {}
    for ex in all_examples:
        tags = ex.get("tags_matrix", {})
        space_types = tags.get("space_type", [])
        if not space_types:
            # 从文件名推断分类
            stem = ex["id"]
            category = stem.rsplit("_", 1)[0] if "_" in stem else stem
            space_types = [category]
        for st in space_types:
            category_map.setdefault(st, []).append(ex)

    for cat, cat_examples in sorted(category_map.items()):
        if len(cat_examples) < 2:
            continue  # 少于 2 条的分类跳过（不值得建索引）
        index_name = f"cat_{cat}"
        ok, msg = build_index(
            examples=cat_examples,
            model=model,
            index_name=index_name,
            output_dir=output_dir,
            force=args.force,
        )
        results.append((ok, msg))
        print(f"  {msg}")

    # ── 汇总 ─────────────────────────────────────────────────────────
    print()
    success_count = sum(1 for ok, _ in results if ok)
    fail_count = len(results) - success_count
    print(f"  总计: {len(results)} 个索引  成功: {success_count}  失败: {fail_count}")

    # ── 写全局 manifest ───────────────────────────────────────────────
    global_manifest = {
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": args.model,
        "total_examples": len(all_examples),
        "indexes": [
            {"name": name, "success": ok}
            for ok, name in ((r[0], r[1].split(":")[0].strip().lstrip("✅").strip()) for r in results)
        ],
    }
    manifest_path = output_dir / "_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(global_manifest, f, ensure_ascii=False, indent=2)
    print(f"  全局 manifest: {manifest_path}")
    print()

    if fail_count > 0:
        print(f"[WARNING] {fail_count} 个索引构建失败")
        return 1

    print("[SUCCESS] 所有索引构建完成！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
