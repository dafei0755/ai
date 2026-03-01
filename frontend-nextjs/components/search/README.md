# Search Components

## Step1DeepAnalysis

Displays Step 1 deep analysis output in user-friendly v2.0 format.

### Usage

```typescript
import Step1DeepAnalysis from '@/components/search/Step1DeepAnalysis';

<Step1DeepAnalysis
  content={step1Output}
  isLoading={false}
  error={undefined}
/>
```

### Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| content | string | Yes | Step 1 markdown output |
| isLoading | boolean | No | Show loading state |
| error | string | No | Error message to display |

### Format Support

- **v2.0 (current)**: 3-section format with visual markers
  - 【您将获得什么】
  - 【我们如何理解您的需求】
  - 【接下来的搜索计划】

- **v1.0 (legacy)**: Backward compatible
  - 【使命1：我的理解】
  - 【输出结果框架】
  - 【搜索方向提示】

### Visual Markers

- 📦 Deliverables package
- ✅ Checkmarks for features
- 📋 Content list
- 1️⃣ 2️⃣ 3️⃣ Numbered blocks
- 🎯 Target for understanding
- 🔍 Magnifying glass for search

### Styling

- Responsive design (mobile-first)
- Distinct section backgrounds
- Tailwind CSS classes
- Accessible ARIA labels

### Testing

Run tests:
```bash
npm test -- Step1DeepAnalysis.test.tsx
```

Coverage: 100% (9/9 tests passing)
