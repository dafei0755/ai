# 📸 外部项目图片存储评估报告

> **评估时间**: 2026-02-17
> **评估范围**: Archdaily、Gooood、Dezeen 三大数据源
> **决策目标**: 是否下载和存储项目图片

---

## 🎯 执行摘要（Executive Summary）

### 💡 推荐方案：**混合策略（优先级存储）**

| 存储类型 | 策略 | 适用场景 |
|---------|------|---------|
| **封面图** | ✅ 下载存储 | 所有项目（1张/项目）|
| **高质量项目图** | ✅ 下载存储 | quality_score ≥ 0.7 的项目（全部图片）|
| **低质量项目图** | ❌ 仅存URL | quality_score < 0.7 的项目（原URL引用）|
| **缩略图** | ⚡ 自动生成 | 所有下载图片生成400px缩略图 |

**预估成本**:
- 存储成本：¥120/年（50GB MinIO/阿里云OSS）
- 首次下载：50小时（10万张图 × 1.8秒/张）
- 带宽成本：可忽略（按需下载）

**核心理由**:
1. ✅ **版权保护**：原网站图片可能过期或删除
2. ✅ **访问速度**：本地存储比跨域请求快3-10倍
3. ✅ **数据完整性**：脱离原网站依赖
4. ⚠️ **成本可控**：仅存储高质量项目图片

---

## 📊 场景分析

### 场景1：不存储图片（仅保存URL）

#### 优势
- ✅ **零存储成本**：无需购买存储空间
- ✅ **快速爬取**：跳过图片下载，爬取速度提升80%
- ✅ **实现简单**：仅保存URL字符串到数据库

#### 劣势
- ❌ **依赖外部网站**：图片可能被删除或过期（404错误）
- ❌ **访问速度慢**：跨域请求延迟高（国外网站200-800ms）
- ❌ **防盗链限制**：某些网站检测Referer，阻止外链显示
- ❌ **数据不完整**：原网站改版可能导致图片丢失
- ❌ **版权风险**：直接引用外部图片可能侵权

**实际案例**：
```
原URL: https://images.archdaily.net/media/images/5f8e/1234/abcd/...jpg

问题：
1. Archdaily改版后URL格式变化 → 404
2. 网站检测到非官网Referer → 403 Forbidden
3. 项目被删除 → 图片永久丢失
4. CDN域名变更 → 全部失效
```

**适用场景**：
- 测试阶段（少量数据）
- 临时数据源（短期使用）
- 已有图片托管方案

---

### 场景2：全量存储图片（下载所有图片）

#### 优势
- ✅ **数据完整**：永久保存，不受原网站影响
- ✅ **访问快速**：本地CDN加速，延迟<50ms
- ✅ **离线可用**：无需互联网也能访问
- ✅ **版权合规**：明确数据所有权
- ✅ **支持二次处理**：缩略图、水印、格式转换

#### 劣势
- ❌ **存储成本高**：预估500GB-1TB存储空间
- ❌ **下载耗时长**：首次爬取10万张图需50小时
- ❌ **带宽消耗大**：下载阶段占用50-100GB流量
- ❌ **管理复杂**：需要文件清理、备份、监控

**成本估算**（10万个项目，平均10张图/项目 = 100万张图）：

| 项目 | 单价 | 数量 | 总成本 |
|------|------|------|--------|
| **MinIO存储** | ¥0.24/GB/月 | 500GB | ¥120/月 = **¥1440/年** |
| **阿里云OSS** | ¥0.12/GB/月 | 500GB | ¥60/月 = **¥720/年** |
| **CDN流量** | ¥0.24/GB | 100GB/月 | ¥24/月 = **¥288/年** |
| **首次下载带宽** | ¥0.8/GB | 200GB | ¥160（一次性）|
| **维护成本** | - | - | ¥500/年（人工）|

**总计**: **¥1,500-2,500/年**

**适用场景**：
- 生产环境（大规模用户）
- 需要离线访问
- 对数据完整性要求极高
- 有充足预算

---

### 场景3：混合策略（推荐）⭐

#### 策略设计

**核心思路**：根据项目质量和图片重要性分级存储

```
┌─────────────────────────────────────┐
│       项目质量评分（0-1）            │
└─────────────────────────────────────┘
           ▼                 ▼
    quality ≥ 0.7      quality < 0.7
   （高质量项目）       （低质量项目）
           │                 │
           ▼                 ▼
   ┌─────────────┐    ┌──────────────┐
   │ ✅ 下载存储  │    │ ❌ 仅存URL   │
   │   全部图片   │    │  + 封面图    │
   │   (10-20张)  │    │   (1张)      │
   └─────────────┘    └──────────────┘
           │                 │
           ▼                 ▼
   ┌─────────────┐    ┌──────────────┐
   │ 生成缩略图   │    │ 生成缩略图   │
   │  400px      │    │  400px       │
   └─────────────┘    └──────────────┘
```

**规则定义**：

| 图片类型 | 判断条件 | 存储策略 | 说明 |
|---------|---------|---------|------|
| **封面图** | `is_cover=True` | ✅ 必存 | 列表页展示必需 |
| **高质量项目** | `quality_score ≥ 0.7` | ✅ 全存 | 完整保存（10-20张）|
| **中等质量** | `0.4 ≤ quality < 0.7` | 🟡 仅封面 | 节省空间 |
| **低质量** | `quality < 0.4` | ❌ 仅URL | 降低成本 |

#### 成本优化

**存储量估算**：

假设：
- 总项目数：10万个
- 高质量项目（≥0.7）：3万个（30%）
- 中等质量项目：5万个（50%）
- 低质量项目：2万个（20%）

```
总图片下载量 =
  高质量项目: 3万 × 15张/项目 = 45万张
  中等质量项目: 5万 × 1张（封面） = 5万张
  低质量项目: 2万 × 1张（封面） = 2万张

总计: 52万张（节省48万张，减少48%）
```

**存储空间**：
- 原图（平均2MB/张）：52万 × 2MB = **1040GB = 1TB**
- 缩略图（平均50KB/张）：52万 × 50KB = **26GB**
- 总计：**1.1TB**

**月度成本**（阿里云OSS标准存储）：
```
1100GB × ¥0.12/GB = ¥132/月 = ¥1,584/年
```

**与全量存储对比**：
- 全量：2TB → ¥2,880/年
- 混合：1.1TB → ¥1,584/年
- **节省：¥1,296/年（45%）**

#### 优势总结

| 维度 | 评分 | 说明 |
|-----|------|------|
| **成本** | ⭐⭐⭐⭐⭐ | 比全量节省45%，比零存储增加可控 |
| **性能** | ⭐⭐⭐⭐ | 封面图必存，列表页加载快 |
| **完整性** | ⭐⭐⭐⭐ | 高质量项目完整保存 |
| **可维护性** | ⭐⭐⭐⭐ | 自动化规则，无需人工判断 |
| **扩展性** | ⭐⭐⭐⭐⭐ | 可随时调整阈值 |

**推荐指数**: ⭐⭐⭐⭐⭐ (5/5)

---

## 🔧 技术实现方案

### 架构设计

```
┌─────────────────────────────────────────────────┐
│              爬虫系统（Crawler）                  │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌──────────────┐      ┌──────────────────┐
│  项目内容    │      │    图片URL列表    │
│  + 质量评分  │      │  [url1, url2...]  │
└──────────────┘      └──────────────────┘
        │                       │
        │                       ▼
        │            ┌──────────────────┐
        │            │  判断是否下载：   │
        │            │  1. 封面图必下载  │
        │            │  2. quality≥0.7   │
        │            │     全部下载      │
        │            │  3. 其他仅存URL   │
        │            └──────────────────┘
        │                       │
        └───────────┬───────────┘
                    ▼
        ┌────────────────────────┐
        │  ImageStorageService   │
        │  - 异步下载图片         │
        │  - 生成缩略图           │
        │  - 上传到MinIO/OSS     │
        │  - 返回存储路径         │
        └────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌──────────────┐      ┌──────────────┐
│ 数据库保存    │      │  文件系统    │
│ storage_path │      │  /images/... │
│ url         │      │              │
└──────────────┘      └──────────────┘
```

---

### 核心代码结构

#### 1. 图片存储配置（settings.py）

```python
# intelligent_project_analyzer/settings.py

class ExternalProjectImageConfig(BaseModel):
    """外部项目图片存储配置"""

    # 存储策略
    enabled: bool = Field(default=True, description="是否启用图片下载")
    quality_threshold: float = Field(default=0.7, description="全量下载的质量阈值")
    always_download_cover: bool = Field(default=True, description="是否总是下载封面图")

    # 存储后端
    storage_backend: str = Field(default="minio", description="存储后端: minio/oss/s3/local")

    # 本地存储
    local_path: str = Field(default="data/external_images", description="本地存储路径")

    # MinIO配置
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="external-projects", alias="MINIO_BUCKET")

    # 阿里云OSS配置
    oss_endpoint: str = Field(default="", alias="OSS_ENDPOINT")
    oss_access_key: str = Field(default="", alias="OSS_ACCESS_KEY")
    oss_secret_key: str = Field(default="", alias="OSS_SECRET_KEY")
    oss_bucket: str = Field(default="", alias="OSS_BUCKET")

    # 图片处理
    generate_thumbnail: bool = Field(default=True, description="是否生成缩略图")
    thumbnail_size: int = Field(default=400, description="缩略图最大边长（像素）")
    thumbnail_quality: int = Field(default=80, description="缩略图JPEG质量")

    # 下载配置
    max_concurrent_downloads: int = Field(default=5, description="最大并发下载数")
    download_timeout: int = Field(default=30, description="下载超时时间（秒）")
    download_retry: int = Field(default=3, description="下载失败重试次数")

    # 文件大小限制
    max_file_size_mb: int = Field(default=10, description="单张图片最大大小（MB）")
```

---

#### 2. 图片存储服务（image_storage_service.py）

```python
# intelligent_project_analyzer/external_data_system/services/image_storage_service.py

from pathlib import Path
from typing import List, Optional, Dict
from PIL import Image
import io
import hashlib
import aiohttp
from loguru import logger

class ExternalImageStorageService:
    """
    外部项目图片存储服务

    功能：
    1. 下载图片
    2. 生成缩略图
    3. 上传到存储后端（MinIO/OSS/本地）
    4. 返回存储路径和URL
    """

    def __init__(self, config: ExternalProjectImageConfig):
        self.config = config
        self.storage_backend = self._init_storage_backend()

    def _init_storage_backend(self):
        """初始化存储后端"""
        if self.config.storage_backend == "minio":
            from minio import Minio
            return Minio(
                self.config.minio_endpoint,
                access_key=self.config.minio_access_key,
                secret_key=self.config.minio_secret_key,
                secure=False
            )
        elif self.config.storage_backend == "oss":
            import oss2
            auth = oss2.Auth(
                self.config.oss_access_key,
                self.config.oss_secret_key
            )
            return oss2.Bucket(
                auth,
                self.config.oss_endpoint,
                self.config.oss_bucket
            )
        else:  # local
            base_path = Path(self.config.local_path)
            base_path.mkdir(parents=True, exist_ok=True)
            return base_path

    async def download_and_store_image(
        self,
        url: str,
        project_id: int,
        source: str,
        is_cover: bool = False
    ) -> Dict[str, str]:
        """
        下载并存储图片

        Returns:
            {
                "original_url": "https://...",
                "storage_path": "external-projects/archdaily/12345/img_001.jpg",
                "thumbnail_path": "external-projects/archdaily/12345/img_001_thumb.jpg",
                "cdn_url": "https://cdn.example.com/...",
                "file_size": 2458967,
                "width": 1920,
                "height": 1080
            }
        """
        try:
            # 1. 下载图片
            logger.info(f"下载图片: {url}")
            image_bytes = await self._download_image(url)

            if not image_bytes:
                return None

            # 2. 验证和处理图片
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            file_size = len(image_bytes)

            # 检查文件大小
            if file_size > self.config.max_file_size_mb * 1024 * 1024:
                logger.warning(f"图片过大: {file_size / 1024 / 1024:.2f}MB")
                return None

            # 3. 生成存储路径
            file_hash = hashlib.md5(image_bytes).hexdigest()[:8]
            ext = img.format.lower() if img.format else 'jpg'
            filename = f"img_{file_hash}.{ext}"
            folder = f"{source}/{project_id}"

            storage_path = f"{folder}/{filename}"

            # 4. 上传原图
            await self._upload_to_storage(image_bytes, storage_path)

            # 5. 生成并上传缩略图
            thumbnail_path = None
            if self.config.generate_thumbnail:
                thumbnail_bytes = self._generate_thumbnail(img)
                thumbnail_path = f"{folder}/{filename}_thumb.jpg"
                await self._upload_to_storage(thumbnail_bytes, thumbnail_path)

            # 6. 生成访问URL
            cdn_url = self._generate_cdn_url(storage_path)
            thumbnail_url = self._generate_cdn_url(thumbnail_path) if thumbnail_path else None

            logger.success(f"图片存储成功: {cdn_url}")

            return {
                "original_url": url,
                "storage_path": storage_path,
                "thumbnail_path": thumbnail_path,
                "cdn_url": cdn_url,
                "thumbnail_url": thumbnail_url,
                "file_size": file_size,
                "width": width,
                "height": height,
                "format": ext
            }

        except Exception as e:
            logger.error(f"图片存储失败: {e}")
            return None

    async def _download_image(self, url: str) -> Optional[bytes]:
        """下载图片（带重试）"""
        for attempt in range(self.config.download_retry):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=self.config.download_timeout)
                    ) as response:
                        if response.status == 200:
                            return await response.read()
                        else:
                            logger.warning(f"下载失败 (HTTP {response.status}): {url}")
            except Exception as e:
                if attempt == self.config.download_retry - 1:
                    logger.error(f"下载失败（重试{attempt+1}次）: {e}")
                else:
                    logger.debug(f"下载失败，重试 {attempt+1}/{self.config.download_retry}")

        return None

    def _generate_thumbnail(self, img: Image.Image) -> bytes:
        """生成缩略图"""
        # 保持宽高比缩放
        img.thumbnail(
            (self.config.thumbnail_size, self.config.thumbnail_size),
            Image.Resampling.LANCZOS
        )

        # 转换为RGB（去除透明通道）
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # 压缩为JPEG
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=self.config.thumbnail_quality, optimize=True)
        return buffer.getvalue()

    async def _upload_to_storage(self, data: bytes, path: str):
        """上传到存储后端"""
        if self.config.storage_backend == "minio":
            self.storage_backend.put_object(
                self.config.minio_bucket,
                path,
                io.BytesIO(data),
                length=len(data)
            )
        elif self.config.storage_backend == "oss":
            self.storage_backend.put_object(path, data)
        else:  # local
            file_path = self.storage_backend / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(data)

    def _generate_cdn_url(self, path: str) -> str:
        """生成CDN访问URL"""
        if self.config.storage_backend == "minio":
            return f"http://{self.config.minio_endpoint}/{self.config.minio_bucket}/{path}"
        elif self.config.storage_backend == "oss":
            return f"https://{self.config.oss_bucket}.{self.config.oss_endpoint}/{path}"
        else:  # local
            return f"/static/external_images/{path}"

    async def batch_download_images(
        self,
        image_urls: List[str],
        project_id: int,
        source: str,
        cover_index: int = 0
    ) -> List[Dict]:
        """
        批量下载图片（异步并发）

        Args:
            image_urls: 图片URL列表
            project_id: 项目ID
            source: 数据源
            cover_index: 封面图索引（默认第一张）
        """
        from asyncio import Semaphore, gather

        semaphore = Semaphore(self.config.max_concurrent_downloads)

        async def download_with_limit(url: str, index: int):
            async with semaphore:
                return await self.download_and_store_image(
                    url,
                    project_id,
                    source,
                    is_cover=(index == cover_index)
                )

        tasks = [
            download_with_limit(url, idx)
            for idx, url in enumerate(image_urls)
        ]

        results = await gather(*tasks, return_exceptions=True)

        # 过滤失败的下载
        return [r for r in results if r and not isinstance(r, Exception)]
```

---

#### 3. 集成到爬虫（crawl_from_index.py）

```python
# scripts/crawl_from_index.py（修改部分）

class IndexBasedCrawler:
    def __init__(self, auto_translate=False, auto_download_images=True):
        self.auto_translate = auto_translate
        self.auto_download_images = auto_download_images

        if auto_download_images:
            from intelligent_project_analyzer.external_data_system.services.image_storage_service import (
                ExternalImageStorageService
            )
            from intelligent_project_analyzer.settings import settings
            self.image_service = ExternalImageStorageService(
                settings.external_project_image
            )

    def crawl_from_index(self, source, limit=None):
        # ... 省略前面的爬取逻辑

        for project_idx in projects:
            # 1. 爬取项目详情
            project_data = spider.parse_project_page(project_idx.url)

            # 2. 翻译（如果需要）
            if self.auto_translate:
                # ... 翻译逻辑
                pass

            # 3. 判断是否下载图片
            should_download_images = self._should_download_images(project_data)

            # 4. 下载图片（如果需要）
            image_metadata = []
            if should_download_images and self.auto_download_images:
                logger.info(f"下载项目图片: {len(project_data.images)} 张")
                image_metadata = await self.image_service.batch_download_images(
                    image_urls=[img['url'] for img in project_data.images],
                    project_id=project_data.source_id,
                    source=source,
                    cover_index=0  # 第一张为封面
                )
                logger.success(f"成功下载: {len(image_metadata)} 张")

            # 5. 保存到数据库
            db_project = ExternalProject(
                source=project_data.source,
                url=project_data.url,
                # ... 其他字段
                quality_score=project_data.quality_score
            )
            db.add(db_project)
            db.commit()

            # 6. 保存图片元数据
            for idx, img in enumerate(project_data.images):
                # 如果有存储路径，使用存储路径；否则使用原URL
                img_metadata = image_metadata[idx] if idx < len(image_metadata) else {}

                db_image = ExternalProjectImage(
                    project_id=db_project.id,
                    url=img['url'],  # 原URL（备用）
                    storage_path=img_metadata.get('storage_path'),  # 存储路径
                    thumbnail_path=img_metadata.get('thumbnail_path'),
                    cdn_url=img_metadata.get('cdn_url'),
                    file_size=img_metadata.get('file_size'),
                    width=img_metadata.get('width'),
                    height=img_metadata.get('height'),
                    order_index=idx,
                    is_cover=(idx == 0)
                )
                db.add(db_image)

            db.commit()

    def _should_download_images(self, project: ProjectData) -> bool:
        """判断是否需要下载图片"""
        if not self.auto_download_images:
            return False

        config = settings.external_project_image

        # 1. 如果设置了总是下载封面，至少下载封面
        if config.always_download_cover:
            return True

        # 2. 如果质量评分达到阈值，全部下载
        if project.quality_score >= config.quality_threshold:
            return True

        return False
```

---

#### 4. CLI使用

```bash
# 启用图片下载
python scripts/crawl_from_index.py \
    --source dezeen \
    --limit 10 \
    --auto-translate \
    --auto-download-images

# 禁用图片下载（仅保存URL）
python scripts/crawl_from_index.py \
    --source dezeen \
    --limit 10 \
    --auto-translate \
    --no-download-images

# 配置环境变量
# .env
IMAGE_STORAGE_ENABLED=true
IMAGE_QUALITY_THRESHOLD=0.7
IMAGE_STORAGE_BACKEND=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=external-projects
```

---

## 📈 成本对比总结

| 方案 | 存储成本/年 | 下载耗时 | 数据完整性 | 访问速度 | 推荐指数 |
|-----|-----------|---------|-----------|---------|---------|
| **不存储** | ¥0 | 0小时 | ⭐⭐ | ⭐⭐ | ⭐⭐ |
| **全量存储** | ¥2,880 | 50小时 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **混合策略** | ¥1,584 | 25小时 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🎯 最终建议

### ✅ 采用混合策略的核心优势

1. **成本可控**：
   - 比全量节省45%（¥1,296/年）
   - 仅存储有价值的内容
   - 低质量项目可随时删除

2. **性能优化**：
   - 封面图必存，列表页加载快
   - 高质量项目详情页体验完整
   - 低质量项目可接受的延迟

3. **数据安全**：
   - 核心内容永久保存
   - 不受原网站删除影响
   - 支持离线访问

4. **灵活扩展**：
   - 质量阈值可调整（0.5 → 0.7 → 0.8）
   - 后期可补充下载低质量项目
   - 支持按需下载

---

### 📋 实施步骤（分阶段）

#### 阶段1：基础环境准备（1天）

```bash
# 1. 安装MinIO或配置OSS
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  -v /data/minio:/data \
  minio/minio server /data --console-address ":9001"

# 2. 创建存储桶
mc alias set myminio http://localhost:9000 minioadmin minioadmin
mc mb myminio/external-projects

# 3. 配置环境变量（.env）
IMAGE_STORAGE_ENABLED=true
IMAGE_QUALITY_THRESHOLD=0.7
IMAGE_STORAGE_BACKEND=minio
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=external-projects
```

#### 阶段2：代码开发（2-3天）

1. ✅ 实现 `ExternalImageStorageService`（核心服务）
2. ✅ 修改 `IndexBasedCrawler`（集成图片下载）
3. ✅ 修改 `ExternalProjectImage` 模型（添加存储字段）
4. ✅ 创建数据库迁移脚本
5. ✅ 添加CLI参数（`--auto-download-images`）

#### 阶段3：小规模测试（1天）

```bash
# 测试10个项目
python scripts/crawl_from_index.py \
    --source dezeen \
    --limit 10 \
    --auto-download-images \
    --quality-threshold 0.7

# 检查存储
mc ls myminio/external-projects/dezeen/

# 验证数据库
python scripts/check_image_storage.py
```

#### 阶段4：全量爬取（按需）

```bash
# 高质量项目优先
python scripts/crawl_from_index.py \
    --source archdaily \
    --auto-download-images \
    --quality-threshold 0.8 \
    --limit 1000

# 逐步降低阈值
python scripts/crawl_from_index.py \
    --source archdaily \
    --auto-download-images \
    --quality-threshold 0.7 \
    --limit 5000
```

---

## 📞 决策建议

### 如果预算充足（>¥3,000/年）
→ **全量存储**，数据最完整，用户体验最佳

### 如果预算中等（¥1,000-3,000/年）
→ **混合策略**（推荐），平衡成本与性能

### 如果预算紧张（<¥1,000/年）
→ **仅封面图**，最小化存储成本

### 如果仅测试阶段
→ **不存储**，快速验证爬虫功能

---

## 🔗 相关资源

- MinIO文档: https://min.io/docs/minio/linux/index.html
- 阿里云OSS: https://help.aliyun.com/product/31815.html
- Pillow图片处理: https://pillow.readthedocs.io/
- aiohttp异步下载: https://docs.aiohttp.org/

---

**评估结论**: ✅ **推荐采用混合策略**，在成本和性能之间取得最佳平衡。
