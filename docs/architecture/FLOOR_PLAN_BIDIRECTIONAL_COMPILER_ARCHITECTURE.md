# Floor Plan Bidirectional Compiler Architecture

Version: v0.1  
Status: executable contract + Phase 0 layout engine  
Date: 2026-04-29

## Positioning

Plan Sandbox is not a CAD editor, a drawing recognizer, or a rendering tool. It is a spatial reasoning surface:

```text
floor-plan facts + project brief + platform knowledge
→ strategy-different layout variants
→ user choice / command iteration
→ version graph and decision traces
```

The product principle is:

```text
The user owns the question and the final decision.
The system owns options, consequences, comparison and traceability.
```

## Cross-Checked Architecture Decision

The main implementation decision is to separate fact and proposal objects.

`FloorPlanFacts` records what the system believes exists in the source plan: boundary, structural wall, column, core, shaft, stair, entry, windows and confidence. It can be compiled from DXF/PDF, created manually, or supplemented by LLM hints.

`LayoutIR` records what the system proposes: space blocks, circulation, open/closed boundaries, score, risks and explanation. It is never treated as source truth.

They share coordinates, visualization and gate logic, but not semantic authority.

This resolves the main conflict in the reference opinions:

```text
Do not create three unrelated systems for parsing/generation/editing.
Do not force parsed facts and generated proposals into one truth object either.
```

## Object Chain

```text
SpatialProgramGraph
  user goals, zones, flows, area targets, privacy and adjacency

FloorPlanFacts
  source plan facts, immutable elements, flexible elements, confidence and review flags

DesignConstraintGraph
  hard locks, adjacency, area, orientation, circulation, privacy, view and cost constraints

DesignIntent
  strategy identity for one variant; LLM should output this, not direct geometry

LayoutIR
  generated proposal blocks, circulation, open/closed boundaries, score and risks

LayoutVariant
  one named candidate version with intent + layout + comparison summary

LayoutVersionGraph
  user choice, rejected reasons, instruction operations and frozen version
```

The first executable version lives in:

```text
intelligent_project_analyzer/core/domain_objects.py
intelligent_project_analyzer/services/floor_plan_layout_engine.py
tests/services/test_floor_plan_layout_engine.py
```

## Engine Boundaries

### Geometry Compiler

Responsibility:

```text
CAD/PDF/manual input → FloorPlanFacts
```

It should prioritize “carrier readiness” over formal IR promotion:

```text
boundary
column/core/shaft/stair
entry
main window/view edge
immutable or likely immutable walls
scale status
confidence and review flags
```

LLM should not block this path. It may run as background semantic QA.

### Layout Variant Engine

Responsibility:

```text
SPG + FloorPlanFacts → 3-5 LayoutVariant objects
```

Phase 0 uses deterministic coarse space blocks. It has three built-in strategy presets:

```text
conservative_low_change
functional_efficiency
experience_value
```

The point is not geometric perfection. The point is to create strategy-different choices early enough for user judgment.

### Design Reasoning Engine

Responsibility:

```text
DesignIntent + LayoutIR + peer variants → explanation, diff, warning and next move
```

LLM belongs here. It should explain why each version exists, what it sacrifices, and how user commands change the project logic.

## User Command Iteration

Natural language should be parsed into operation primitives before touching geometry:

```text
lock_space
move_space
resize_space
swap_space
merge_spaces
split_space
add_buffer
reduce_corridor
increase_privacy
improve_view
shorten_path
separate_flow
open_boundary
close_boundary
merge_strategy
reduce_cost
```

Rule:

```text
User commands must always be understood and answered.
Hard constraints must not be faked.
```

If a command conflicts with immutable facts, the system should return:

```text
direct conflict explanation
closest feasible alternative
impact on score / risks
next question or user override point
```

## Response Timing

Two paths should coexist:

```text
Immediate path:
local lock, drag, resize, simple block update
target: 300ms-1s

Reasoning path:
multi-variant regeneration, merge A/B strengths, full explanation and score diff
target: 3-30s, async
```

This preserves user agency while still letting the high-advisor layer think.

## Version Graph

Versions are not a flat history list. They are a decision graph:

```text
baseline
├─ conservative_low_change
├─ functional_efficiency
│  └─ user: reduce corridor
└─ experience_value
   └─ user: keep public core, reduce cost
```

Each node should retain:

```text
strategy
source constraints
user instruction
operation primitives
score movement
risk movement
selected/rejected/frozen status
decision trace
```

This is the platform learning substrate.

## MVP Sequence

### Phase 0: Executable Contract

Done in this implementation:

```text
FloorPlanFacts
DesignConstraintGraph
DesignIntent
LayoutIR
LayoutVariant
LayoutVersionGraph
deterministic generate_layout_variants()
unit tests
```

### Phase 1: Connect Existing Plan Sandbox

Next steps:

```text
add an API endpoint for generate-variants
map current FloorPlanCompiler output to FloorPlanFacts
render LayoutIR spaces as selectable variant overlays
record selected/rejected/frozen version in local/session state
```

### Phase 2: Command Iteration

```text
natural language → LayoutOperation
impact scope calculation
local regenerate affected spaces
show diff and high-advisor explanation
```

### Phase 3: Platform Knowledge Injection

```text
project type methods
knowledge-base case hits
DSS preference weights
role-attributed DesignIntent generation
```

## Competitive Boundary

Kujiale/Coohom is stronger at drawing, modeling, material libraries and rendering.

qbiq is stronger at planning packages and fast test-fit delivery.

Finch is stronger at rule-based architectural generation and graph-rule feedback.

This system should compete on:

```text
Chinese design-advisor reasoning
strategy-different variants
user-command iteration
decision trace and platform learning
```

The north-star feature is not “more plans”. It is:

```text
more visible spatial judgment under user control
```
