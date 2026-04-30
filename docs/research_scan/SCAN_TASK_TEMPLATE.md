# ScanTask 输入模板

```yaml
topic: "<主题>"
time_window: "近30天"
seed_sites:
  - "https://example.com"
languages:
  - "中文"
  - "英文"
max_depth_per_site: 2
exclusions:
  - "论坛"
  - "广告站"
  - "低可信聚合站"
```

## 字段说明
- `topic`: 研究主题，不能为空。
- `time_window`: 时间范围，建议使用绝对表达（如近7天/近30天/不限）。
- `seed_sites`: 指定优先深挖站点，可空列表。
- `languages`: 语言范围，至少一种。
- `max_depth_per_site`: 每个重点站点深挖层级，建议 `0-3`。
- `exclusions`: 过滤规则，降低噪声来源。
