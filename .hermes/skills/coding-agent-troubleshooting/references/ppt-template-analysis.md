# PPT模板拆解分析指南

## 会话：2026-09-11 模板采集任务

### 关键发现

1. **Terminal工具Windows兼容性问题**
   - MSYS bash路径转换与Windows原生路径冲突
   - 优先使用 `execute_code` 而非 `terminal`

2. **F:\ppt模板目录结构**
   - 总计2446个PPT模板
   - 分25个类别（国赛、工作汇报、毕业答辩等）

3. **python-pptx解析示例**
```python
from pptx import Presentation
prs = Presentation(filepath)
# 提取颜色
for shape in slide.shapes:
    if hasattr(shape, 'fill') and shape.fill.type == 1:
        color = shape.fill.fore_color.rgb
# 提取字体
for shape in slide.shapes:
    if hasattr(shape, 'text_frame'):
        for p in shape.text_frame.paragraphs:
            for run in p.runs:
                font = run.font.name
```

4. **分析结果**
   - 分析模板：120个（25类×5样本）
   - 提取配色：30种
   - 提取字体：30种

5. **输出文件**
   - docs/template_analysis.json (648KB)
   - docs/template_library_report.md (3.5KB)
   - docs/template_library.sql (7KB)
