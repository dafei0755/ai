import json

data = json.load(open("data/website_structures.json", encoding="utf-8"))

print("=" * 80)
print("【完整索引目标统计】")
print("=" * 80)

gooood_cats = len(data["gooood"]["categories"])
archdaily_cats = len(data["archdaily"]["categories"])
dezeen_cats = len(data["dezeen"]["categories"])
total = gooood_cats + archdaily_cats + dezeen_cats

print(f"\n📊 Gooood:    {gooood_cats:3d} 个分类")
print(f"📊 Archdaily: {archdaily_cats:3d} 个分类")
print(f"📊 Dezeen:    {dezeen_cats:3d} 个分类")
print(f"\n{'='*80}")
print(f"✅ 总计:      {total:3d} 个分类")
print(f"{'='*80}")

print("\n【Gooood分类明细】")
for i, cat in enumerate(data["gooood"]["categories"][:5], 1):
    print(f"  {i}. {cat['name']}")
print(f"  ... (共{gooood_cats}个)")

print("\n【Archdaily分类明细】")
for i, cat in enumerate(data["archdaily"]["categories"][:5], 1):
    print(f"  {i}. {cat['name']}")
print(f"  ... (共{archdaily_cats}个)")

print("\n【Dezeen分类明细】")
for i, cat in enumerate(data["dezeen"]["categories"], 1):
    print(f"  {i}. {cat['name']}")

print("\n" + "=" * 80)
print("索引策略:")
print("=" * 80)
print(f"• Gooood ({gooood_cats}个): 包含专辑、类型、资讯等多维度分类")
print(f"• Archdaily ({archdaily_cats}个): 主题分类（访谈、城市指南、奖项等）")
print(f"• Dezeen ({dezeen_cats}个): 主分类（建筑、设计、室内、技术）")
print("\n预估索引量（按999页/分类）:")
print(f"  每分类约200-500个项目 × {total}分类 = 预估10,000-25,000个项目URL")
