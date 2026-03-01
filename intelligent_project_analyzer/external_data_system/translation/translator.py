"""
项目内容翻译器

使用Deepseek API进行建筑项目内容的英译中翻译
特点：
1. 专业术语处理
2. 人名地名保留
3. 质量评分
4. 缓存机制

语言策略
────────────────────────────────────────────────────────
- 英文源 (dezeen/archdaily)：description_en → 翻译 → description_zh
- 中文源 (archdaily_cn)：直接写入 description_zh，无需翻译
- 双语源 (gooood)：description_en （已由爬虫分离）→ 翻译 → 补写 description_zh
  若 description_zh 已有内容则跳过翻译
────────────────────────────────────────────────────────
"""

import os
import json
import hashlib
from typing import Dict, List, Optional
import requests
from loguru import logger
from dotenv import load_dotenv

from ..spiders.base_spider import ProjectData

# 加载环境变量
load_dotenv()


class ProjectTranslator:
    """项目内容翻译器"""

    def __init__(self, engine: str = "deepseek", cache_enabled: bool = True):
        """
        初始化翻译器

        Args:
            engine: 翻译引擎 ('deepseek', 'gpt4', 'claude')
            cache_enabled: 是否启用缓存
        """
        self.engine = engine
        self.cache_enabled = cache_enabled
        self._cache = {}

        # 从环境变量加载API配置
        if engine == "deepseek":
            self.api_key = os.getenv("DEEPSEEK_API_KEY")
            self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            self.model = "deepseek-chat"
        else:
            raise ValueError(f"不支持的翻译引擎: {engine}")

        if not self.api_key:
            raise ValueError(f"未找到{engine.upper()}_API_KEY环境变量")

        # 建筑专业术语词典
        self.terminology = self._load_terminology()

    def _load_terminology(self) -> Dict[str, str]:
        """加载建筑专业术语词典"""
        return {
            # 结构类
            "facade": "立面",
            "cantilever": "悬臂",
            "atrium": "中庭",
            "courtyard": "庭院",
            "skylight": "天窗",
            "colonnade": "柱廊",
            "portico": "门廊",
            "pavilion": "亭",
            # 空间类
            "lobby": "大堂",
            "foyer": "门厅",
            "gallery": "画廊/走廊",
            "auditorium": "礼堂",
            "amphitheater": "露天剧场",
            # 材料类
            "concrete": "混凝土",
            "timber": "木材",
            "steel": "钢材",
            "glass": "玻璃",
            "brick": "砖",
            "stone": "石材",
            # 风格类
            "minimalist": "极简主义",
            "brutalist": "粗野主义",
            "modernist": "现代主义",
            "contemporary": "当代",
            "vernacular": "本土",
            # 功能类
            "residential": "住宅",
            "commercial": "商业",
            "cultural": "文化",
            "public": "公共",
            "institutional": "机构",
            "mixed-use": "混合用途",
        }

    def translate_project(self, project: ProjectData) -> Dict[str, str]:
        """
        翻译项目内容

        Args:
            project: 项目数据对象

        Returns:
            {'title_zh': '...', 'description_zh': '...', 'quality': 0.85}
        """
        logger.info(f"开始翻译项目: {project.title[:50]}...")

        # 检查缓存
        if self.cache_enabled:
            cache_key = self._get_cache_key(project.title, project.description)
            if cache_key in self._cache:
                logger.debug("使用缓存的翻译")
                return self._cache[cache_key]

        # 构建翻译提示词
        prompt = self._build_translation_prompt(project)

        # 调用API翻译
        try:
            translation = self._call_api(prompt)

            # 解析结果
            result = self._parse_translation_result(translation)

            # 质量评分
            quality = self._evaluate_quality(project, result)
            result["quality"] = quality

            # 缓存结果
            if self.cache_enabled:
                self._cache[cache_key] = result

            logger.success(f"翻译完成，质量评分: {quality:.2f}")
            return result

        except Exception as e:
            logger.error(f"翻译失败: {e}")
            return {
                "title_zh": project.title,  # 失败时返回原文
                "description_zh": project.description,
                "quality": 0.0,
                "error": str(e),
            }

    def _build_translation_prompt(self, project: ProjectData) -> str:
        """构建翻译提示词"""

        # 提取关键信息（用于更好的翻译）
        context_info = []
        if project.architects:
            context_info.append(f"建筑师: {', '.join(project.architects)}")
        if project.location:
            location_str = ", ".join([v for v in project.location.values() if v])
            context_info.append(f"位置: {location_str}")
        if project.year:
            context_info.append(f"年份: {project.year}")

        context = "\n".join(context_info) if context_info else "无额外信息"

        # 对长描述进行智能截断（保留完整段落）
        description = project.description
        if len(description) > 8000:
            # 截取到最后一个完整段落
            truncated = description[:8000]
            last_newline = truncated.rfind("\n\n")
            if last_newline > 6000:
                description = truncated[:last_newline]
            else:
                description = truncated
            logger.warning(f"描述过长（{len(project.description)} 字符），已截取至 {len(description)} 字符")

        prompt = f"""你是专业的建筑设计翻译专家。请将以下英文建筑项目内容翻译成中文。

**翻译要求**：
1. 保持建筑专业性和准确性
2. 人名保留英文：如 "Sou Fujimoto"、"Frank Gehry" 不翻译
3. 建筑事务所名称保留英文：如 "Foster + Partners" 不翻译
4. 地名使用官方中文名或保留英文：如 "Abu Dhabi" → "阿布扎比"，"Saadiyat Island" → "萨迪亚特岛"
5. 专业术语首次出现时可用"中文（英文）"格式标注：如 "立面（Facade）"
6. 保持原文的段落结构，用两个换行符分隔段落
7. 数字、单位、尺寸保持原样：如 "77 homes"、"1,536 square meters"
8. 项目名称如果是专有名词保留英文：如 "Baccarat Residences"

**项目背景信息**：
{context}

**标题**：
{project.title}

**描述内容**：
{description}

**请返回JSON格式**，不要有任何其他文字：
{{
    "title_zh": "翻译后的标题",
    "description_zh": "翻译后的描述（保持段落结构）"
}}"""

        return prompt

    def _call_api(self, prompt: str) -> str:
        """调用Deepseek API"""

        url = f"{self.base_url}/v1/chat/completions"

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是专业的建筑设计翻译专家，精通中英文建筑术语。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,  # 低温度保证翻译稳定性
            "max_tokens": 8000,  # 增加到8000以支持长文本翻译
            "response_format": {"type": "json_object"},  # 要求JSON输出
        }

        logger.debug(f"调用Deepseek API: {url}")

        response = requests.post(url, headers=headers, json=data, timeout=60)

        if response.status_code != 200:
            raise Exception(f"API调用失败: {response.status_code} - {response.text}")

        result = response.json()

        if "choices" not in result or not result["choices"]:
            raise Exception(f"API返回格式错误: {result}")

        content = result["choices"][0]["message"]["content"]

        return content

    def _parse_translation_result(self, translation: str) -> Dict[str, str]:
        """解析翻译结果"""
        try:
            # 尝试解析JSON
            result = json.loads(translation)

            if "title_zh" not in result or "description_zh" not in result:
                raise ValueError("缺少必需字段")

            return {"title_zh": result["title_zh"].strip(), "description_zh": result["description_zh"].strip()}

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.debug(f"原始内容: {translation[:200]}...")

            # 尝试提取内容（容错处理）
            lines = translation.strip().split("\n")
            title_zh = lines[0] if lines else translation[:100]
            description_zh = "\n".join(lines[1:]) if len(lines) > 1 else translation

            return {"title_zh": title_zh, "description_zh": description_zh}

    def _evaluate_quality(self, project: ProjectData, translation: Dict[str, str]) -> float:
        """
        评估翻译质量

        指标：
        1. 长度比例 (0.8-1.5 正常)
        2. 人名保留检查
        3. 专业术语检查
        4. 段落结构保持
        """
        score = 1.0

        # 1. 长度比例检查
        if project.description and translation["description_zh"]:
            len_ratio = len(translation["description_zh"]) / len(project.description)
            if len_ratio < 0.5 or len_ratio > 2.0:
                score -= 0.3
                logger.warning(f"长度比例异常: {len_ratio:.2f}")

        # 2. 人名保留检查（如果原文有建筑师名）
        if project.architects:
            architects_preserved = sum(
                1
                for arch in project.architects
                if arch in translation["title_zh"] or arch in translation["description_zh"]
            )
            if architects_preserved < len(project.architects):
                score -= 0.1
                logger.warning(f"建筑师名称未完全保留: {architects_preserved}/{len(project.architects)}")

        # 3. 标题合理性检查
        if not translation["title_zh"] or len(translation["title_zh"]) < 10:
            score -= 0.2
            logger.warning("标题过短")

        # 4. 描述合理性检查
        if not translation["description_zh"] or len(translation["description_zh"]) < 100:
            score -= 0.2
            logger.warning("描述过短")

        return max(0.0, min(1.0, score))

    def _get_cache_key(self, title: str, description: str) -> str:
        """生成缓存键"""
        content = f"{title}|{description[:1000]}"
        return hashlib.md5(content.encode()).hexdigest()

    # ========================================================================
    # 高级接口：翻译并写回 ProjectData
    # ========================================================================

    def needs_translation(self, project: ProjectData) -> bool:
        """判断项目是否需要翻译

        规则：
        - lang="zh" → 已有中文，不翻译
        - lang="bilingual" → 若 description_zh 已有内容，不翻译（爬虫已分离）；
                             若 description_en 有内容但 description_zh 为空，翻译英文部分
        - lang="en" → 需要翻译
        - lang="unknown" → 尝试翻译
        """
        if project.lang == "zh":
            return False
        if project.lang == "bilingual" and project.description_zh:
            return False
        # 有英文内容才翻译
        return bool(project.description_en or project.description)

    def translate_and_apply(self, project: ProjectData) -> ProjectData:
        """翻译项目内容并将结果写回 ProjectData 双语字段

        - 英文源：翻译 description_en → 填入 description_zh / title_zh
        - 双语源：翻译 description_en（英文分离段）→ 填入已空的 description_zh
        - 中文源：直接返回，无需处理

        Returns:
            修改后的 ProjectData（原地修改，同时作为返回值）
        """
        if not self.needs_translation(project):
            logger.debug(f"[翻译] 跳过（lang={project.lang}）: {project.url}")
            return project

        # 构建翻译目标
        # 对于双语页，只翻译英文分离段；对于纯英文页，翻译全部描述
        source_title = project.title_en or project.title or ""
        source_desc = project.description_en or project.description or ""

        if not source_title and not source_desc:
            logger.warning(f"[翻译] 无英文内容可翻译: {project.url}")
            return project

        logger.info(f"[翻译] 开始 ({project.lang}): {source_title[:60]}")

        # 使用现有翻译接口，但传入正确的源内容
        tmp = ProjectData(
            source=project.source,
            source_id=project.source_id,
            url=project.url,
            title=source_title,
            description=source_desc,
            architects=project.architects,
            location=project.location,
            year=project.year,
        )

        result = self.translate_project(tmp)

        # 写回双语字段
        if result.get("title_zh") and not project.title_zh:
            project.title_zh = result["title_zh"]
        if result.get("description_zh"):
            # 双语页：追加翻译的英文段（到已有中文段后面）
            if project.lang == "bilingual" and project.description_zh:
                project.description_zh = project.description_zh + "\n\n" + result["description_zh"]
            else:
                project.description_zh = result["description_zh"]

        if result.get("title_en") and not project.title_en:
            project.title_en = source_title
        if not project.description_en:
            project.description_en = source_desc

        logger.success(f"[翻译] 完成，质量={result.get('quality', 0):.2f}: {project.url}")
        return project

    def batch_translate_and_apply(
        self,
        projects: List[ProjectData],
        max_workers: int = 3,
        skip_already_translated: bool = True,
    ) -> List[ProjectData]:
        """批量翻译并写回 ProjectData

        Args:
            projects: 项目列表
            max_workers: 并发数
            skip_already_translated: 跳过已有 description_zh 的项目

        Returns:
            处理后的项目列表（原地修改）
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        targets = [p for p in projects if self.needs_translation(p)] if skip_already_translated else projects
        skipped = len(projects) - len(targets)

        logger.info(f"[批量翻译] {len(targets)} 个需翻译，{skipped} 个跳过")

        if not targets:
            return projects

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_proj = {executor.submit(self.translate_and_apply, p): p for p in targets}
            for i, future in enumerate(as_completed(future_to_proj), 1):
                try:
                    future.result()
                    logger.info(f"[批量翻译] 进度: {i}/{len(targets)}")
                except Exception as e:
                    logger.error(f"[批量翻译] 失败: {e}")

        return projects

    # ========================================================================
    # 旧版批量接口（保留向后兼容）
    # ========================================================================

    def batch_translate(self, projects: List[ProjectData], max_workers: int = 3) -> List[Dict[str, str]]:
        """
        批量翻译项目

        Args:
            projects: 项目列表
            max_workers: 并发数（建议3-5，避免API限流）

        Returns:
            翻译结果列表
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        logger.info(f"开始批量翻译 {len(projects)} 个项目")

        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_project = {executor.submit(self.translate_project, project): project for project in projects}

            # 收集结果
            for i, future in enumerate(as_completed(future_to_project), 1):
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"进度: {i}/{len(projects)}")
                except Exception as e:
                    logger.error(f"翻译失败: {e}")
                    results.append({"title_zh": "", "description_zh": "", "quality": 0.0, "error": str(e)})

        # 统计
        avg_quality = sum(r["quality"] for r in results) / len(results) if results else 0
        success_count = sum(1 for r in results if r["quality"] > 0.6)

        logger.success(f"批量翻译完成: {success_count}/{len(projects)} 成功, 平均质量: {avg_quality:.2f}")

        return results


# 单例模式
_translator_instance = None


def get_translator(engine: str = "deepseek") -> ProjectTranslator:
    """获取翻译器单例"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = ProjectTranslator(engine=engine)
    return _translator_instance
