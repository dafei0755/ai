"""Build and route v3.3 missing_slots.

The service keeps slot filling and slot routing separate from the context packet
builder so the policy can be tested directly.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional


class MissingSlotService:
    """Create missing slots from required slots and apply v3.3 routing policy."""

    physical_slot_names = {
        "existing_mep_capacity",
        "fire_boundary_conditions",
        "back_of_house_equipment_scope",
        "structural_modification_boundary",
    }
    business_slot_names = {
        "takeaway_ratio",
        "estimated_peak_orders_per_hour",
        "store_model",
        "seat_ratio",
        "public_private_access_control",
        "traffic_node_conversion",
        "payback_model_inputs",
    }
    subjective_slot_names = {
        "style_preference",
        "tone_preference",
        "brand_memory_keywords",
        "social_intensity",
    }

    def build(
        self,
        required_slots: Iterable[str],
        user_input: str,
        extra_slots: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        filled_slots: List[Dict[str, Any]] = []
        missing_slots: List[Dict[str, Any]] = []

        for raw_slot in required_slots:
            slot_key = str(raw_slot)
            filled = self._filled_slot(slot_key, user_input)
            if filled:
                filled_slots.append(filled)
                continue
            missing_slots.append(self.slot_from_required_slot(slot_key))

        if extra_slots:
            missing_slots.extend(extra_slots)

        routed_slots = self.apply_policy(missing_slots)
        return {
            "schema_version": "missing_slots.v1",
            "filled_slots": filled_slots,
            "missing_slots": routed_slots,
            "policy": self._policy_summary(routed_slots),
        }

    def apply_policy(self, slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        active_priority = self._active_priority(slots)
        routed: List[Dict[str, Any]] = []
        for slot in slots:
            next_slot = dict(slot)
            is_active = not active_priority or next_slot.get("priority") == active_priority
            next_slot["active_for_current_round"] = is_active
            next_slot["deferred_by"] = "" if is_active else self._deferred_by(active_priority)
            routed.append(next_slot)
        return sorted(routed, key=self._slot_sort_key)

    def slot_from_required_slot(self, slot: str) -> Dict[str, Any]:
        slot_type, severity, action, priority = self._slot_policy(slot)
        return {
            "name": self.canonical_slot_name(slot),
            "type": slot_type,
            "severity": severity,
            "action": action,
            "priority": priority,
            "affected_lens": [],
            "unlock_condition": f"known({slot})",
            "user_visible_note": self.slot_note(slot),
        }

    def _filled_slot(self, slot: str, user_input: str) -> Optional[Dict[str, Any]]:
        text = user_input or ""
        canonical_name = self.canonical_slot_name(slot)

        patterns = {
            "existing_mep_capacity": [
                r"机电.*(已确认|已明确|明确|没问题|满足)",
                r"给排水.*(已确认|已明确|明确|没问题|满足)",
                r"电力.*(已确认|已明确|明确|没问题|满足)",
            ],
            "fire_boundary_conditions": [
                r"消防.*(已确认|已明确|明确|没问题|满足)",
                r"疏散.*(已确认|已明确|明确|没问题|满足)",
            ],
            "back_of_house_equipment_scope": [
                r"后场设备.*(已确认|已明确|明确|没问题|满足)",
                r"设备.*(已确认|已明确|明确|清单|没问题|满足)",
            ],
            "takeaway_ratio": [
                r"外带为主",
                r"外卖为主",
                r"自提为主",
                r"堂食为主",
                r"外带|外卖|自提",
            ],
            "store_model": [
                r"商场",
                r"购物中心",
                r"街边",
                r"社区",
                r"园区",
                r"写字楼",
                r"店型.*(已确认|已明确|明确)",
                r"门店模型.*(已确认|已明确|明确)",
            ],
            "seat_ratio": [
                r"堂食",
                r"座位",
                r"无座",
                r"少量座",
                r"座位比例.*(已确认|已明确|明确)",
            ],
            "estimated_peak_orders_per_hour": [
                r"高峰订单.*(已确认|已明确|明确)",
                r"峰值订单.*(已确认|已明确|明确)",
                r"订单量.*(已确认|已明确|明确)",
                r"\d+\s*(单|杯).*(高峰|峰值|每小时|小时)",
            ],
            "style_preference": [
                r"极简",
                r"禅意",
                r"新中式",
                r"克制",
                r"高级",
                r"打卡",
            ],
            "tone_preference": [
                r"纯粹",
                r"松弛",
                r"温暖",
                r"冷静",
                r"新旧对撞",
            ],
        }
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns.get(slot, [])):
            return {
                "name": canonical_name,
                "raw_slot": slot,
                "status": "filled_from_user_input",
                "source": "user_input",
                "confidence": "explicit_or_strong_hint",
            }
        return None

    def _slot_policy(self, slot: str) -> tuple[str, str, str, str]:
        if slot in self.physical_slot_names:
            return ("physical_constraint", "high", "certainty_ceiling", "P1")
        if slot in self.subjective_slot_names:
            return ("subjective_preference", "medium", "option_menu", "P3")
        return ("business_fact", "high" if slot in self.business_slot_names else "medium", "branch_answer_plus_followup", "P2")

    @staticmethod
    def canonical_slot_name(slot: str) -> str:
        aliases = {
            "existing_mep_capacity": "water_drainage_point",
            "takeaway_ratio": "delivery_ratio",
            "estimated_peak_orders_per_hour": "peak_order_volume",
        }
        return aliases.get(slot, slot)

    @staticmethod
    def slot_note(slot: str) -> str:
        if slot == "traffic_node_conversion":
            return "需要确认地铁连接口的客流截取、排队外溢和取餐边界，否则门头、导视和队列策略只能先按条件级判断。"
        if slot == "payback_model_inputs":
            return "需要确认租金、客单价、日单量、设备投入和装修上限，否则半年回本只能作为目标压力，不能形成可核算方案。"
        notes = {
            "existing_mep_capacity": "需要确认给排水、排烟、电力等机电条件，否则不能锚定平面和设备节拍。",
            "fire_boundary_conditions": "需要确认消防边界和疏散条件，否则正式方案只能给条件级判断。",
            "back_of_house_equipment_scope": "需要确认后场设备和制作范围，否则吧台、仓储和机电负荷只能条件级判断。",
            "takeaway_ratio": "需要确认外带、外卖和堂食比例，才能判断点单、制作、取餐是否会互相卡死。",
            "estimated_peak_orders_per_hour": "需要确认高峰订单量，才能判断队列和出杯效率是否成立。",
            "store_model": "需要确认门店模型和所处场景，才能判断入口、排队、外摆和商场界面关系。",
            "seat_ratio": "需要确认堂食与停留比例，才能判断座位、等候和取餐空间的权重。",
            "style_preference": "需要确认整体风格偏好，否则只能给几条候选路径而不能收敛到一个方向。",
            "tone_preference": "需要确认空间调性，否则材料、灯光和品牌语言会停留在宽泛建议。",
        }
        return notes.get(slot, f"需要补齐 {slot}，否则会影响后续判断的确定性。")

    @staticmethod
    def _active_priority(slots: List[Dict[str, Any]]) -> str:
        priorities = {slot.get("priority") for slot in slots}
        for priority in ("P1", "P2", "P3"):
            if priority in priorities:
                return priority
        return ""

    @staticmethod
    def _deferred_by(active_priority: str) -> str:
        if active_priority == "P1":
            return "P1_physical_constraint_gate"
        if active_priority == "P2":
            return "P2_business_fact_gate"
        return ""

    @staticmethod
    def _slot_sort_key(slot: Dict[str, Any]) -> tuple[int, int, str]:
        priority_rank = {"P1": 0, "P2": 1, "P3": 2}.get(str(slot.get("priority")), 9)
        active_rank = 0 if slot.get("active_for_current_round") else 1
        return (active_rank, priority_rank, str(slot.get("name") or ""))

    def _policy_summary(self, slots: List[Dict[str, Any]]) -> Dict[str, Any]:
        active_priority = self._active_priority(slots)
        return {
            "active_priority": active_priority,
            "active_slot_count": sum(1 for slot in slots if slot.get("active_for_current_round")),
            "deferred_slot_count": sum(1 for slot in slots if not slot.get("active_for_current_round")),
            "serial_priority_rule": "P1>P2>P3",
        }
