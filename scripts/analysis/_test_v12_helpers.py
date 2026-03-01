"""Quick smoke test for v12.0 helper functions."""
from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
    _extract_spatial_zones,
    _build_constraint_envelope,
)

# Test 1: _extract_spatial_zones
print("=" * 50)
print("Test 1: _extract_spatial_zones")
print("=" * 50)

zones = _extract_spatial_zones({}, "这是一个三层别墅，1楼有客厅和餐厅，2楼有主卧和书房，地下室作为车库")
for z in zones:
    print(f"  Zone: {z['id']} -> {z['label']} ({z['source']})")

assert len(zones) >= 5, f"Expected at least 5 zones, got {len(zones)}"
zone_ids = {z["id"] for z in zones}
assert "overall" in zone_ids
assert "1f" in zone_ids
assert "2f" in zone_ids
assert "basement" in zone_ids
print(f"  ✅ Passed ({len(zones)} zones)")

# Test 2: _build_constraint_envelope
print()
print("=" * 50)
print("Test 2: _build_constraint_envelope")
print("=" * 50)

constraints = {
    "overall": [
        {"level": "immutable", "description": "承重墙位置不可移动"},
        {"level": "baseline", "description": "层高2.8m"},
    ],
    "1f": [
        {"level": "opportunity", "description": "南向采光极佳，可引入自然光"},
        {"level": "immutable", "description": "入户门朝北"},
    ],
}
envelope = _build_constraint_envelope(constraints, zones, {"prefer": ["现代简约"], "avoid": ["欧式古典"]})
print(envelope)
assert "设计参照系" in envelope
assert "immutable" not in envelope.lower() or "L1 不可变" in envelope  # Check Chinese labels
assert "END" in envelope
print(f"  ✅ Passed (envelope length: {len(envelope)})")

# Test 3: Empty case
print()
print("=" * 50)
print("Test 3: Empty constraints")
print("=" * 50)
empty_envelope = _build_constraint_envelope({}, zones)
assert empty_envelope == "", f"Expected empty string, got: {empty_envelope}"
print("  ✅ Passed (empty correctly)")

# Test 4: No-image constraint pipeline returns None
print()
print("=" * 50)
print("Test 4: _run_constraint_pipeline with no images")
print("=" * 50)
import asyncio
from intelligent_project_analyzer.interaction.nodes.output_intent_detection import _run_constraint_pipeline

result = asyncio.run(_run_constraint_pipeline({"uploaded_visual_references": []}))
assert result is None, f"Expected None, got: {result}"
result2 = asyncio.run(_run_constraint_pipeline({}))
assert result2 is None
print("  ✅ Passed (returns None for empty)")

print()
print("🎉 All v12.0 helper tests passed!")
