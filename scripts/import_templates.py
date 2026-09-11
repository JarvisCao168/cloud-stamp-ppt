#!/usr/bin/env python
"""Template library import script"""
import sqlite3
import os

DB_PATH = "yunzhang.db"
SQL_PATH = "docs/template_library.sql"

# Read and execute the main SQL
conn = sqlite3.connect(DB_PATH)

# Drop tables that might have schema mismatches
for table in ['color_palettes', 'font_library', 'template_categories', 'templates', 'template_numbering', 'numbering_styles']:
    conn.execute(f"DROP TABLE IF EXISTS {table}")

conn.commit()
print("Dropped existing tables")

# Execute the template library SQL (creates tables + inserts data)
with open(SQL_PATH, 'r', encoding='utf-8') as f:
    sql = f.read()
conn.executescript(sql)
conn.commit()
print(f"Imported from {SQL_PATH}")

# Now add numbering styles (the SQL doesn't include them)
numbering_seed = '''
CREATE TABLE IF NOT EXISTS numbering_styles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('numeric', 'chinese', 'level', 'graphic', 'icon', 'english', 'special')),
    symbols TEXT NOT NULL,
    description TEXT,
    tags TEXT NOT NULL,
    max_depth INTEGER DEFAULT 1,
    preview_html TEXT,
    is_system BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS template_numbering (
    template_id TEXT NOT NULL,
    numbering_id TEXT NOT NULL,
    priority INTEGER DEFAULT 0,
    PRIMARY KEY (template_id, numbering_id),
    FOREIGN KEY (template_id) REFERENCES templates(id),
    FOREIGN KEY (numbering_id) REFERENCES numbering_styles(id)
);
'''
conn.executescript(numbering_seed)

# Insert numbering styles
numbering_data = [
    ('numeric-dot', '数字序号·', 'numeric', '["1.","2.","3.","4.","5."]'),
    ('numeric-paren', '数字序号()', 'numeric', '["(1)","(2)","(3)","(4)","(5)"]'),
    ('numeric-bracket', '数字方括号', 'numeric', '["[1]","[2]","[3]","[4]","[5]"]'),
    ('numeric-bracket-n', '编号方括号', 'numeric', '["1)","2)","3)","4)","5)"]'),
    ('numeric-period-n', '圆圈数字', 'numeric', '["①","②","③","④","⑤"]'),
    ('chinese-clause', '中文顿号', 'chinese', '["一、","二、","三、","四、","五、"]'),
    ('chinese-paren', '中文括号', 'chinese', '["（一）","（二）","（三）","（四）","（五）"]'),
    ('chinese-bracket', '中文括号()', 'chinese', '["(1)","(2)","(3)","(4)","(5)"]'),
    ('chinese-ten', '中文天干', 'chinese', '["甲","乙","丙","丁","戊"]'),
    ('level-nested', '层级序号', 'level', '["1.1","1.1.1","1.1.1.1"]'),
    ('level-decimal', '小数层级', 'level', '["0.1","0.1.1","0.1.1.1"]'),
    ('level-bracket', '括号层级', 'level', '["(1.1)","(1.1.1)","(1.1.1.1)"]'),
    ('graphic-circle', '圆形图形', 'graphic', '["●","○","■","□","★","☆"]'),
    ('graphic-diamond', '菱形图形', 'graphic', '["◆","◇","▸","◂","▹","◃"]'),
    ('graphic-square', '方块图形', 'graphic', '["▣","▤","▥","▦","▧","▨"]'),
    ('graphic-triangle', '三角形图形', 'graphic', '["▲","△","▼","▽","⬆","⬇"]'),
    ('graphic-check', '勾选图形', 'graphic', '["✓","✗","☆","★","●","○"]'),
    ('graphic-bullet', '项目符号', 'graphic', '["•","‣","⁃","·","▪","▫"]'),
    ('icon-check', '箭头图标', 'icon', '["→","✓","✗","⚠","★"]'),
    ('icon-arrow', '步骤箭头链', 'icon', '["▶","▶","▶","▶","▶"]'),
    ('icon-star', '星级图标', 'icon', '["⭐","☆","★★","★★★","★★★★"]'),
    ('icon-badge', '徽章图标', 'icon', '["🏆","🥈","🥉","🎖","🏅"]'),
    ('icon-alert', '警告图标', 'icon', '["⚠","❗","❓","ℹ","✅"]'),
    ('english-alpha', '英文字母', 'english', '["A.","B.","C.","D.","E."]'),
    ('english-roman', '罗马数字', 'english', '["I.","II.","III.","IV.","V."]'),
    ('english-alpha-lower', '小写英文字母', 'english', '["a.","b.","c.","d.","e."]'),
    ('english-roman-lower', '小写罗马数字', 'english', '["i.","ii.","iii.","iv.","v."]'),
    ('special-enclosed', '圈码数字', 'special', '["①","②","③","④","⑤"]'),
    ('special-enclosed-caps', '大写圈码', 'special', '["Ⓐ","Ⓑ","Ⓒ","Ⓓ","Ⓔ"]'),
    ('special-enclosed-small', '小写圈码', 'special', '["ⓐ","ⓑ","ⓒ","ⓓ","ⓔ"]'),
]

for row in numbering_data:
    conn.execute(
        "INSERT OR IGNORE INTO numbering_styles (id, name, type, symbols) VALUES (?, ?, ?, ?)",
        row
    )

conn.commit()
print(f"Inserted {len(numbering_data)} numbering styles")

# Verify counts
print("\n=== Database Status ===")
for table in ['color_palettes', 'font_library', 'template_categories', 'templates', 'numbering_styles']:
    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table}: {count} rows")

# Category distribution
print("\n=== Templates by Category ===")
cats = conn.execute("SELECT category, COUNT(*) FROM templates GROUP BY category ORDER BY COUNT(*) DESC").fetchall()
for cat, count in cats:
    print(f"  {cat}: {count}")

conn.close()
print("\nImport completed successfully!")
