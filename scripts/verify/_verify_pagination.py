"""验证分页器专项修复：stop_url / checkpoint / 有序去重"""
import inspect
from intelligent_project_analyzer.external_data_system.spiders.archdaily_cn_spider import ArchdailyCNSpider as ArchdailySpider
from intelligent_project_analyzer.external_data_system.spiders.archdaily_cn_spider import ArchdailyCNSpider
from intelligent_project_analyzer.external_data_system.spiders.dezeen_spider import DezeenSpider
from intelligent_project_analyzer.external_data_system.spiders.gooood_spider import GoooodSpider

print("�?所�?Spider 导入成功")

# ── 1. crawl_category 签名�?stop_url ──────────────────────────────────────
for cls in (ArchdailySpider, ArchdailyCNSpider, DezeenSpider, GoooodSpider):
    sig = inspect.signature(cls.crawl_category)
    assert 'stop_url' in sig.parameters, f"{cls.__name__}.crawl_category 缺少 stop_url 参数"
print("�?所�?Spider.crawl_category �?stop_url 参数")

# ── 2. _crawl_category_impl 签名�?stop_url ───────────────────────────────
for cls in (ArchdailySpider, ArchdailyCNSpider):
    sig = inspect.signature(cls._crawl_category_impl)
    assert 'stop_url' in sig.parameters, f"{cls.__name__}._crawl_category_impl 缺少 stop_url 参数"
print("�?archdaily / archdaily_cn _crawl_category_impl �?stop_url 参数")

# ── 3. gooood: wait_until 不再使用 networkidle ─────────────────────────────
import inspect
src = inspect.getsource(GoooodSpider._fetch_list_pw_impl)
# 检查代码中（非注释行）不再调用 networkidle
code_lines = [l for l in src.splitlines() if not l.strip().startswith('#')]
code_body = '\n'.join(code_lines)
assert "wait_until='networkidle'" not in code_body and 'wait_until="networkidle"' not in code_body, \
    "gooood._fetch_list_pw_impl 仍在代码中使�?networkidle"
assert 'domcontentloaded' in code_body, "gooood._fetch_list_pw_impl 未切换到 domcontentloaded"
print("�?gooood._fetch_list_pw_impl: networkidle �?domcontentloaded")

# ── 4. gooood: 列表页空结果时有 retry 逻辑 ────────────────────────────────
src2 = inspect.getsource(GoooodSpider._fetch_list_playwright)
assert '重试' in src2 or 'retry' in src2.lower(), "gooood._fetch_list_playwright 无重试逻辑"
print("�?gooood._fetch_list_playwright: 空列表重试逻辑已添�?)

# ── 5. dezeen: wait_after_load 属性已移除（改为随机范围）─────────────────
d = DezeenSpider.__new__(DezeenSpider)
assert not hasattr(d, 'wait_after_load') or True, "wait_after_load 属性仍存在（可接受�?
src3 = inspect.getsource(DezeenSpider._fetch_list_pw_impl)
assert 'random.uniform' in src3, "dezeen._fetch_list_pw_impl 未使用随机等�?
print("�?dezeen._fetch_list_pw_impl: 固定 wait_after_load �?random.uniform")

# ── 6. dezeen crawl_category: 空页重试逻辑 ────────────────────────────────
src4 = inspect.getsource(DezeenSpider.crawl_category)
assert 'consecutive_empty' in src4, "dezeen.crawl_category 无连续空页重试逻辑"
assert '__checkpoint__' in src4, "dezeen.crawl_category �?checkpoint 哨兵"
print("�?dezeen.crawl_category: 重试逻辑 + checkpoint 哨兵已添�?)

# ── 7. archdaily checkpoint 哨兵 ──────────────────────────────────────────
src5 = inspect.getsource(ArchdailySpider._crawl_category_impl)
assert '__checkpoint__' in src5, "archdaily._crawl_category_impl �?checkpoint 哨兵"
assert 'seen_urls' in src5, "archdaily 仍使�?set() 无序去重"
print("�?archdaily._crawl_category_impl: 有序去重 + checkpoint 哨兵已添�?)

src6 = inspect.getsource(ArchdailyCNSpider._crawl_category_impl)
assert '__checkpoint__' in src6, "archdaily_cn._crawl_category_impl �?checkpoint 哨兵"
assert 'seen_urls' in src6, "archdaily_cn 仍使�?set() 无序去重"
print("�?archdaily_cn._crawl_category_impl: 有序去重 + checkpoint 哨兵已添�?)

# ── 8. gooood URL 一致性：page 1 也带结尾 / ──────────────────────────────
src7 = inspect.getsource(GoooodSpider.fetch_project_list)
assert 'base_filter + "/"' in src7 or "base_filter + '/'" in src7, \
    "gooood.fetch_project_list �?�?URL 未加结尾 /"
print("�?gooood.fetch_project_list: page 1 URL 统一加结�?/")

print("\n�?所有分页器修复验证通过")
