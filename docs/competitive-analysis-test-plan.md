# Competitive Analysis Test Plan

> Version: v1.0  
> Created: 2026-09-10  
> Owner: Hermes (coordination) / Codex (execution)

---

## Test Strategy

### Testing Approach
- **Manual testing** with structured evaluation
- **Standardized input** across all competitors
- **Consistent evaluation criteria** for comparability
- **Screenshot documentation** for evidence

### Test Input Document
**Theme**: "2026年人工智能发展趋势与商业应用"
**Structure**: 8 slides
1. Title Slide - 标题页
2. Overview - AI发展趋势概述
3. Enterprise Application - 企业应用场景
4. Consumer Products - 消费级产品
5. Industry Impact - 行业影响分析
6. Challenges - 挑战与伦理问题
7. Future Outlook - 未来展望
8. Conclusion - 总结与建议

---

## Evaluation Dimensions

### Dimension 1: Content Quality (权重 25%)
| Criteria | Weight | Score (1-5) | Notes |
|----------|--------|-------------|-------|
| Relevance | 30% | | How well does content match the theme? |
| Accuracy | 30% | | Factual correctness of information |
| Depth | 20% | | Level of detail and analysis |
| Structure | 20% | | Logical flow and organization |

### Dimension 2: Visual Design (权重 25%)
| Criteria | Weight | Score (1-5) | Notes |
|----------|--------|-------------|-------|
| Layout | 30% | | Slide composition and balance |
| Color Scheme | 25% | | Color harmony and appropriateness |
| Typography | 25% | | Font selection and readability |
| Visual Elements | 20% | | Use of icons, images, charts |

### Dimension 3: AI Capability (权重 20%)
| Criteria | Weight | Score (1-5) | Notes |
|----------|--------|-------------|-------|
| Content Understanding | 30% | | How well does AI understand the prompt? |
| Generation Quality | 30% | | Quality of generated content |
| Customization | 20% | | Flexibility for user modifications |
| Learning/Adaptation | 20% | | Ability to improve based on feedback |

### Dimension 4: User Experience (权重 15%)
| Criteria | Weight | Score (1-5) | Notes |
|----------|--------|-------------|-------|
| Interface Intuitiveness | 30% | | Ease of navigation |
| Generation Speed | 25% | | Time to complete generation |
| Error Handling | 25% | | How well errors are handled |
| Export Options | 20% | | Variety of export formats |

### Dimension 5: Chinese Support (权重 15%)
| Criteria | Weight | Score (1-5) | Notes |
|----------|--------|-------------|-------|
| Language Support | 30% | | Chinese text rendering quality |
| Cultural Relevance | 30% | | Appropriateness for Chinese context |
| Template Design | 20% | | Quality of Chinese-themed templates |
| Input Methods | 20% | | Support for Chinese input methods |

---

## Test Cases

### TC-01: Basic Generation Test
**Input**: Simple theme "人工智能发展趋势"
**Expected**: Single-slide generation with basic content
**Evaluation**: 
- Generation time
- Content relevance
- Visual quality

### TC-02: Multi-Slide Generation
**Input**: Full 8-slide outline as specified above
**Expected**: Complete 8-slide presentation
**Evaluation**:
- All slides generated
- Content consistency across slides
- Visual coherence

### TC-03: Customization Test
**Input**: Generated content with specific modification requests
**Expected**: Able to modify content, layout, or style
**Evaluation**:
- Modification flexibility
- Quality after modification
- Error handling

### TC-04: Export Test
**Input**: Completed presentation
**Expected**: Export in multiple formats (PDF, PPTX, PNG, HTML)
**Evaluation**:
- Available formats
- Export quality
- File size

### TC-05: Template Selection
**Input**: Different style preferences (professional, creative, minimalist)
**Expected**: Appropriate template matching
**Evaluation**:
- Template variety
- Style matching accuracy
- Customization options

---

## Scoring Summary

### Weighted Score Calculation
```
Total Score = 
  Content Quality × 0.25 +
  Visual Design × 0.25 +
  AI Capability × 0.20 +
  User Experience × 0.15 +
  Chinese Support × 0.15
```

### Rating Scale
| Score | Rating | Description |
|-------|--------|-------------|
| 4.5-5.0 | Excellent | Outstanding performance |
| 3.5-4.4 | Good | Solid performance with minor issues |
| 2.5-3.4 | Average | Adequate but needs improvement |
| 1.5-2.4 | Below Average | Significant issues |
| 1.0-1.4 | Poor | Major problems |

---

## Competitors to Test

### Tier 1: International
1. **Gamma** (gamma.app)
   - Free tier available
   - Focus: AI-generated presentations
   - Best for: Modern, design-forward presentations

2. **Tome** (tome.app)
   - Free tier available
   - Focus: Storytelling presentations
   - Best for: Narrative-driven content

3. **Beautiful.ai** (beautiful.ai)
   - 14-day free trial
   - Focus: Intelligent templates
   - Best for: Business presentations

### Tier 2: Chinese
4. **讯飞智文** (zhiwen.xfyun.cn)
   - Free tier available
   - Focus: Chinese language support
   - Best for: Chinese content generation

5. **腾讯文档AI** (docs.qq.com)
   - Free tier available
   - Focus: Integration with Tencent ecosystem
   - Best for: Collaborative work

6. **百度文库AI** (wenku.baidu.com)
   - Free tier available
   - Focus: Chinese document generation
   - Best for: Academic/professional documents

### Tier 3: Others
7. **WPS AI** (wps.cn)
   - Freemium model
   - Focus: Office suite integration
   - Best for: Microsoft Office users

---

## Data Collection Template

### Per-Competitor Data
```json
{
  "competitor_name": "Gamma",
  "test_date": "2026-09-10",
  "url": "https://gamma.app",
  "pricing_tier": "freemium",
  "free_features": ["3 projects", "Basic templates"],
  "scores": {
    "content_quality": {
      "relevance": 4,
      "accuracy": 4,
      "depth": 3,
      "structure": 4,
      "weighted": 3.85
    },
    "visual_design": {
      "layout": 5,
      "color_scheme": 4,
      "typography": 4,
      "visual_elements": 4,
      "weighted": 4.3
    },
    "ai_capability": {
      "content_understanding": 4,
      "generation_quality": 4,
      "customization": 3,
      "learning_adaptation": 3,
      "weighted": 3.5
    },
    "user_experience": {
      "interface_intuitiveness": 4,
      "generation_speed": 5,
      "error_handling": 4,
      "export_options": 4,
      "weighted": 4.25
    },
    "chinese_support": {
      "language_support": 3,
      "cultural_relevance": 2,
      "template_design": 3,
      "input_methods": 3,
      "weighted": 2.75
    }
  },
  "weighted_score": 3.71,
  "notes": "Excellent design but limited Chinese support",
  "screenshots": [
    "gamma_slide_1.png",
    "gamma_slide_2.png"
  ],
  "recommendation": "Best for international audiences, not suitable for Chinese-only projects"
}
```

---

## Deliverables

1. **competitive-analysis.json** - Structured data for all competitors
2. **competitive-analysis-report.md** - Narrative analysis and recommendations
3. **screenshots/** - Visual evidence folder (organized by competitor)
4. **pain-points-frequency.csv** - Aggregated user pain points from feedback collection

---

## Timeline

| Phase | Activity | Deadline | Owner |
|-------|----------|----------|-------|
| 1 | International competitors testing | 2026-09-12 | Codex |
| 2 | Chinese competitors testing | 2026-09-14 | Codex |
| 3 | Data compilation | 2026-09-15 | Codex |
| 4 | Analysis and report writing | 2026-09-16 | Hermes |
| 5 | Review and finalization | 2026-09-18 | Team |

---

## Notes

- Test each competitor at least twice for consistency
- Document any bugs or issues encountered
- Take screenshots at key stages (input, generation, export)
- Compare results side-by-side when possible
- Consider regional accessibility issues (some tools may not work in China)
