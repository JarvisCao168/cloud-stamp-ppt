"""
数据库初始化
使用 aiosqlite 异步 SQLite，提供 schema 创建和 seed 数据导入
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite

from app.core.config import settings

# 完整的 schema 定义（含 is_system 字段 + 多对多关联表）
SCHEMA_SQL = """
-- 序号样式表（含 is_system 字段，区分系统内置 vs 用户上传）
CREATE TABLE IF NOT EXISTS numbering_styles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('numeric', 'chinese', 'level', 'graphic', 'icon', 'english', 'special')),
    symbols TEXT NOT NULL,  -- JSON array
    description TEXT,
    tags TEXT NOT NULL,     -- JSON array
    max_depth INTEGER DEFAULT 1,
    preview_html TEXT,
    is_system BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 模板表（含 default_numbering_id 外键）
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT DEFAULT 'theme',
    preview TEXT,
    description TEXT,
    default_numbering_id TEXT,
    is_system BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (default_numbering_id) REFERENCES numbering_styles(id)
);

-- 模板-序号样式多对多关联表
CREATE TABLE IF NOT EXISTS template_numbering (
    template_id TEXT NOT NULL,
    numbering_id TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    PRIMARY KEY (template_id, numbering_id),
    FOREIGN KEY (template_id) REFERENCES templates(id),
    FOREIGN KEY (numbering_id) REFERENCES numbering_styles(id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_numbering_styles_type ON numbering_styles(type);
CREATE INDEX IF NOT EXISTS idx_numbering_styles_tags ON numbering_styles(tags);
CREATE INDEX IF NOT EXISTS idx_templates_default_numbering ON templates(default_numbering_id);
"""

# 初始序号样式种子数据（30条，与 assets.py NUMBERING_STYLES 一致）
NUMBERING_SEED_SQL = """
INSERT OR IGNORE INTO numbering_styles (id, name, type, symbols, description, tags, max_depth, preview_html, is_system)
VALUES
('numeric-dot', '数字序号·', 'numeric', '["1.","2.","3.","4.","5."]', '标准数字加点号，适用于商务报告', '["商务","正式"]', 3, '<ol><li>第一项</li><li>第二项</li></ol>', true),
('numeric-paren', '数字序号()', 'numeric', '["(1)","(2)","(3)","(4)","(5)"]', '数字加括号，学术文档常用', '["学术","正式"]', 3, '<p>(1) 第一项 (2) 第二项</p>', true),
('numeric-bracket', '数字方括号', 'numeric', '["[1]","[2]","[3]","[4]","[5]"]', '方括号编号，参考文献风格', '["学术","引用"]', 3, '<p>[1] 第一项 [2] 第二项</p>', true),
('numeric-bracket-n', '编号方括号', 'numeric', '["1)","2)","3)","4)","5)"]', '数字后加右括号，简洁格式', '["简洁","通用"]', 3, '<p>1) 第一项 2) 第二项</p>', true),
('numeric-period-n', '圆圈数字', 'numeric', '["①","②","③","④","⑤"]', '圆圈数字，列表编号友好', '["列表","友好"]', 1, '<p>① 第一项 ② 第二项</p>', true),
('chinese-clause', '中文顿号', 'chinese', '["一、","二、","三、","四、","五、"]', '中文数字加顿号，正式公文首选', '["正式","公文","政府"]', 2, '<p>一、第一项  二、第二项</p>', true),
('chinese-paren', '中文括号', 'chinese', '["（一）","（二）","（三）","（四）","（五）"]', '中文数字加括号，二级标题常用', '["正式","公文"]', 2, '<p>（一）第一项  （二）第二项</p>', true),
('chinese-bracket', '中文括号()', 'chinese', '["(1)","(2)","(3)","(4)","(5)"]', '中文语境下的括号数字，简明报告', '["简洁","报告"]', 2, '<p>(1) 第一项 (2) 第二项</p>', true),
('chinese-ten', '中文天干', 'chinese', '["甲","乙","丙","丁","戊"]', '天干排序，传统文档适用', '["传统","文化"]', 1, '<p>甲 第一项  乙 第二项</p>', true),
('level-nested', '层级序号', 'level', '["1.1","1.1.1","1.1.1.1"]', '多级嵌套编号，技术文档/手册适用', '["技术","文档","手册"]', 4, '<p>1. 一级  1.1 二级  1.1.1 三级</p>', true),
('level-decimal', '小数层级', 'level', '["0.1","0.1.1","0.1.1.1"]', '从零开始的小数层级，规范文档风格', '["规范","文档"]', 4, '<p>0.1 一级  0.1.1 二级  0.1.1.1 三级</p>', true),
('level-bracket', '括号层级', 'level', '["(1.1)","(1.1.1)","(1.1.1.1)"]', '带括号的层级编号，学术论文常用', '["学术","论文"]', 4, '<p>(1.1) 二级  (1.1.1) 三级</p>', true),
('graphic-circle', '圆形图形', 'graphic', '["●","○","■","□","★","☆"]', '图形符号作序号，视觉化列表', '["创意","视觉"]', 1, '<p>● 第一项  ○ 第二项  ■ 第三项</p>', true),
('graphic-diamond', '菱形图形', 'graphic', '["◆","◇","▸","◂","▹","◃"]', '菱形箭头系列，方向感列表', '["创意","方向"]', 1, '<p>◆ 第一项  ◇ 第二项  ▸ 第三项</p>', true),
('graphic-square', '方块图形', 'graphic', '["▣","▤","▥","▦","▧","▨"]', '填充方块变体，现代设计感', '["现代","设计"]', 1, '<p>▣ 第一项  ▤ 第二项  ▥ 第三项</p>', true),
('graphic-triangle', '三角形图形', 'graphic', '["▲","△","▼","▽","⬆","⬇"]', '三角方向符号，流程指引列表', '["流程","指引"]', 1, '<p>▲ 第一项  △ 第二项  ▼ 第三项</p>', true),
('graphic-check', '勾选图形', 'graphic', '["✓","✗","☆","★","●","○"]', '勾选状态符号，待办事项列表', '["待办","清单"]', 1, '<p>✓ 已完成  ✗ 未完成  ☆ 待确认</p>', true),
('graphic-bullet', '项目符号', 'graphic', '["•","‣","⁃","·","▪","▫"]', '经典项目符号，通用列表格式', '["通用","列表"]', 1, '<p>• 第一项  ‣ 第二项  ⁃ 第三项</p>', true),
('icon-check', '箭头图标', 'icon', '["→","✓","✗","⚠","★"]', '箭头/对钩序列，流程图/步骤展示', '["流程","步骤","验证"]', 1, '<p>→ 第一步  → 第二步  ✓ 完成</p>', true),
('icon-arrow', '步骤箭头链', 'icon', '["▶","▶","▶","▶","▶"]', '箭头串联步骤，流程图/时间线', '["流程","时间线","步骤"]', 1, '<p>▶ 开始 ▶ 进行中 ▶ 完成</p>', true),
('icon-star', '星级图标', 'icon', '["⭐","☆","★★","★★★","★★★★"]', '星级评分符号，评价类列表', '["评分","评价"]', 1, '<p>⭐ 优秀  ☆ 待改进  ★★ 良好</p>', true),
('icon-badge', '徽章图标', 'icon', '["🏆","🥈","🥉","🎖","🏅"]', '奖牌徽章序列，排名类展示', '["排名","荣誉"]', 1, '<p>🏆 冠军  🥈 亚军  🥉 季军</p>', true),
('icon-alert', '警告图标', 'icon', '["⚠","❗","❓","ℹ","✅"]', '提示图标序列，注意事项列表', '["提示","注意","安全"]', 1, '<p>⚠ 注意  ❗ 重要  ℹ 说明</p>', true),
('english-alpha', '英文字母', 'english', '["A.","B.","C.","D.","E."]', '英文字母序号，英文PPT/学术演示', '["英文","学术"]', 3, '<p>A. First  B. Second  C. Third</p>', true),
('english-roman', '罗马数字', 'english', '["I.","II.","III.","IV.","V."]', '罗马数字序号，正式演讲/典礼', '["正式","典礼","学术"]', 3, '<p>I. Prima  II. Secunda  III. Tertia</p>', true),
('english-alpha-lower', '小写英文字母', 'english', '["a.","b.","c.","d.","e."]', '小写字母序号，温和风格列表', '["英文","温和"]', 3, '<p>a. first  b. second  c. third</p>', true),
('english-roman-lower', '小写罗马数字', 'english', '["i.","ii.","iii.","iv.","v."]', '小写罗马数字，精致正式风格', '["正式","精致"]', 3, '<p>i. prima  ii. secunda  iii. tertia</p>', true),
('special-enclosed', '圈码数字', 'special', '["①","②","③","④","⑤"]', '圆形圈码，创意PPT/儿童教育', '["创意","教育","儿童"]', 1, '<p>① 第一项  ② 第二项  ③ 第三项</p>', true),
('special-enclosed-caps', '大写圈码', 'special', '["Ⓐ","Ⓑ","Ⓒ","Ⓓ","Ⓔ"]', '大写字母圈码，特殊标记列表', '["特殊","标记"]', 1, '<p>Ⓐ 第一项  Ⓑ 第二项  Ⓒ 第三项</p>', true),
('special-enclosed-small', '小写圈码', 'special', '["ⓐ","ⓑ","ⓒ","ⓓ","ⓔ"]', '小写字母圈码，可爱风格列表', '["可爱","轻松"]', 1, '<p>ⓐ 第一项  ⓑ 第二项  ⓒ 第三项</p>', true);
"""

# 模板种子数据（含 default_numbering_id）
TEMPLATES_SEED_SQL = """
INSERT OR IGNORE INTO templates (id, name, category, preview, description, default_numbering_id, is_system)
VALUES
('modern-dark', '现代暗色', 'theme', '/assets/previews/modern-dark.png', '暗色主题，适合科技/互联网演示', 'numeric-dot', true),
('corporate-clean', '商务简洁', 'theme', '/assets/previews/corporate-clean.png', '简洁商务风，适合企业报告', 'numeric-dot', true),
('futuristic-neon', '未来霓虹', 'theme', '/assets/previews/futuristic-neon.png', '霓虹灯风格，适合创新路演', 'icon-arrow', true),
('minimal-light', '极简浅色系', 'theme', '/assets/previews/minimal-light.png', '白色极简，适合设计/艺术展示', 'chinese-clause', true),
('nature-organic', '自然有机', 'theme', '/assets/previews/nature-organic.png', '绿色自然风，适合环保/健康主题', 'graphic-bullet', true),
('academic', '学术严谨', 'theme', '/assets/previews/academic.png', '学术风格，适合论文答辩/研究报告', 'chinese-paren', true);
"""


async def init_db() -> None:
    """初始化数据库：创建表结构和种子数据"""
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA_SQL)
        await db.executescript(NUMBERING_SEED_SQL)
        await db.executescript(TEMPLATES_SEED_SQL)
        await db.commit()
        print(f"[DB] 初始化完成: {db_path}")


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """获取数据库连接（用于依赖注入）"""
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        yield db


def get_db_sync():
    """同步数据库连接（用于测试脚本）"""
    import sqlite3
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    # Windows path handling for sqlite3
    if db_path.startswith("/"):
        db_path = db_path.lstrip("/")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
