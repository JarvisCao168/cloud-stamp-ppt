-- 云章PPT智能体 - 模板库数据导入SQL (v2 - 与app schema一致)
-- 从F:\ppt模板目录的120个模板分析中提取

-- 配色表（使用app期望的TEXT id格式，但保持原始id兼容）
CREATE TABLE IF NOT EXISTS color_palettes (
    id TEXT PRIMARY KEY,
    hex_color TEXT NOT NULL,
    category TEXT DEFAULT '通用',
    tags TEXT,
    usage_count INTEGER DEFAULT 0,
    source_template_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 字体表
CREATE TABLE IF NOT EXISTS font_library (
    id TEXT PRIMARY KEY,
    font_name TEXT NOT NULL,
    font_type TEXT,
    category TEXT DEFAULT '正文',
    tags TEXT,
    usage_count INTEGER DEFAULT 0,
    source_template_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 模板表（与app/db.py schema一致）
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    source_path TEXT,
    total_slides INTEGER,
    preview TEXT,
    description TEXT,
    tags TEXT,
    color_scheme TEXT,
    font_scheme TEXT,
    layout_structure TEXT,
    default_numbering_id TEXT,
    is_system BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (default_numbering_id) REFERENCES numbering_styles(id)
);

-- 类别表
CREATE TABLE IF NOT EXISTS template_categories (
    id TEXT PRIMARY KEY,
    category_name TEXT NOT NULL UNIQUE,
    description TEXT,
    default_colors TEXT,
    default_fonts TEXT,
    template_count INTEGER DEFAULT 0,
    avg_slides REAL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 配色数据（以hex_color为id）
INSERT OR REPLACE INTO color_palettes (id, hex_color, category, tags, usage_count) VALUES
('color-#FFFFFF', '#FFFFFF', '通用', '数据分析提取', 28),
('color-#C00000', '#C00000', '通用', '数据分析提取', 10),
('color-#0070C0', '#0070C0', '通用', '数据分析提取', 10),
('color-#000000', '#000000', '通用', '数据分析提取', 6),
('color-#00B0F0', '#00B0F0', '通用', '数据分析提取', 5),
('color-#FF0000', '#FF0000', '通用', '数据分析提取', 4),
('color-#FFC000', '#FFC000', '通用', '数据分析提取', 4),
('color-#F8F8F8', '#F8F8F8', '通用', '数据分析提取', 3),
('color-#F9F9F9', '#F9F9F9', '通用', '数据分析提取', 3),
('color-#A6A6A6', '#A6A6A6', '通用', '数据分析提取', 3),
('color-#ADBACA', '#ADBACA', '通用', '数据分析提取', 3),
('color-#DCDCDC', '#DCDCDC', '通用', '数据分析提取', 2),
('color-#D7D7D7', '#D7D7D7', '通用', '数据分析提取', 2),
('color-#CCCC33', '#CCCC33', '通用', '数据分析提取', 2),
('color-#F6F6F6', '#F6F6F6', '通用', '数据分析提取', 2),
('color-#7F7F7F', '#7F7F7F', '通用', '数据分析提取', 2),
('color-#9BBB59', '#9BBB59', '通用', '数据分析提取', 2),
('color-#DFDFE1', '#DFDFE1', '通用', '数据分析提取', 2),
('color-#01ACBE', '#01ACBE', '通用', '数据分析提取', 2),
('color-#FFB850', '#FFB850', '通用', '数据分析提取', 2),
('color-#663A77', '#663A77', '通用', '数据分析提取', 2),
('color-#E87071', '#E87071', '通用', '数据分析提取', 2),
('color-#504D47', '#504D47', '通用', '数据分析提取', 1),
('color-#E1E8F0', '#E1E8F0', '通用', '数据分析提取', 1),
('color-#3C3939', '#3C3939', '通用', '数据分析提取', 1),
('color-#9EB5CE', '#9EB5CE', '通用', '数据分析提取', 1),
('color-#DEDEDF', '#DEDEDF', '通用', '数据分析提取', 1),
('color-#73AA93', '#73AA93', '通用', '数据分析提取', 1),
('color-#EBBE1D', '#EBBE1D', '通用', '数据分析提取', 1),
('color-#D75D00', '#D75D00', '通用', '数据分析提取', 1);

-- 字体数据（以font_name为id）
INSERT OR REPLACE INTO font_library (id, font_name, font_type, category, tags, usage_count) VALUES
('font-微软雅黑', '微软雅黑', '中文', '正文', '数据分析提取', 73),
('font-Arial', 'Arial', '英文', '正文', '数据分析提取', 37),
('font-Impact', 'Impact', '英文', '标题', '数据分析提取', 19),
('font-Calibri', 'Calibri', '英文', '正文', '数据分析提取', 15),
('font-+mn-ea', '+mn-ea', '东亚', '正文', '数据分析提取', 12),
('font-Agency FB', 'Agency FB', '英文', '标题', '数据分析提取', 10),
('font-+mj-lt', '+mj-lt', '拉丁', '正文', '数据分析提取', 9),
('font-+mj-ea', '+mj-ea', '东亚', '正文', '数据分析提取', 9),
('font-幼圆', '幼圆', '中文', '正文', '数据分析提取', 7),
('font-+mn-lt', '+mn-lt', '拉丁', '正文', '数据分析提取', 5),
('font-微软雅黑 Light', '微软雅黑 Light', '中文', '正文', '数据分析提取', 4),
('font-Calibri Light', 'Calibri Light', '英文', '正文', '数据分析提取', 4),
('font-Arial Black', 'Arial Black', '英文', '标题', '数据分析提取', 4),
('font-方正姚体', '方正姚体', '中文', '艺术', '数据分析提取', 4),
('font-汉仪菱心体简', '汉仪菱心体简', '中文', '标题', '数据分析提取', 4),
('font-Century Gothic', 'Century Gothic', '英文', '正文', '数据分析提取', 4),
('font-方正清刻本悦宋简体', '方正清刻本悦宋简体', '中文', '正文', '数据分析提取', 4),
('font-Arial Unicode MS', 'Arial Unicode MS', '英文', '正文', '数据分析提取', 3),
('font-Broadway', 'Broadway', '英文', '标题', '数据分析提取', 3),
('font-华文细黑', '华文细黑', '中文', '正文', '数据分析提取', 3),
('font-字魂36号-正文宋楷', '字魂36号-正文宋楷', '中文', '正文', '数据分析提取', 3),
('font-字魂59号-创粗黑', '字魂59号-创粗黑', '中文', '标题', '数据分析提取', 3),
('font-思源黑体旧字形 Normal', '思源黑体旧字形 Normal', '中文', '正文', '数据分析提取', 3),
('font-Lato', 'Lato', '英文', '正文', '数据分析提取', 3),
('font-Source Sans Pro', 'Source Sans Pro', '英文', '正文', '数据分析提取', 3),
('font-Lato Black', 'Lato Black', '英文', '标题', '数据分析提取', 3),
('font-思源黑体 CN Normal', '思源黑体 CN Normal', '中文', '正文', '数据分析提取', 2),
('font-宋体', '宋体', '中文', '正文', '数据分析提取', 2),
('font-Franklin Gothic Book', 'Franklin Gothic Book', '英文', '正文', '数据分析提取', 2),
('font-Dotum', 'Dotum', '韩文', '正文', '数据分析提取', 2);

-- 类别数据
INSERT OR REPLACE INTO template_categories (id, category_name, description, default_colors, default_fonts, template_count, avg_slides) VALUES
('cat-01 详情展示', '01 详情展示', NULL, '#504D47,#E1E8F0,#3C3939', '微软雅黑,Andalus', 5, 15.2),
('cat-10欧美风格', '10欧美风格', NULL, '#354B5E,#D5B07C,#D5D5D5', 'Arial,微软雅黑', 3, 24.7),
('cat-11培训课件', '11培训课件', NULL, '#F9F9F9,#DCDCDC,#D7D7D7', '微软雅黑,Impact', 5, 40.6),
('cat-12扁平风格', '12扁平风格', NULL, '#FFFFFF,#CCCC33,#FF6969', '微软雅黑,Arial', 5, 23.8),
('cat-13快闪风格', '13快闪风格', NULL, '#FF5050,#D1F8CC,#16B39E', '微软雅黑,Bebas Neue', 5, 41.8),
('cat-14项目策划', '14项目策划', NULL, '#0C86B6,#269FD3,#A6A6A6', '微软雅黑,Arial', 5, 31.4),
('cat-15开题报告', '15开题报告', NULL, '#000000,#4A4E98,#EEC618', '字魂36号-正文宋楷,字魂59号-创粗黑', 5, 24.2),
('cat-16创意风格', '16创意风格', NULL, '#FFFFFF,#F17831,#D76E17', '微软雅黑,+mj-lt', 5, 22.2),
('cat-17自我介绍', '17自我介绍', NULL, '#FFFFFF,#99BF4F,#1CA854', '迷你简卡通,微软雅黑', 5, 13.6),
('cat-19企业宣传', '19企业宣传', NULL, '#A6A6A6,#0070C0,#00A1DA', 'Arial,微软雅黑', 5, 27.2),
('cat-1莫兰迪PPT', '1莫兰迪PPT', NULL, '#486553,#679378,#FFFFFF', '汉仪字酷堂义山楷W,思源黑体旧字形 Normal', 5, 17.0),
('cat-20时尚风格', '20时尚风格', NULL, '#C5AF76,#FFFFFF,#9DD6C8', 'Lato,Source Sans Pro', 5, 40.2),
('cat-21述职报告', '21述职报告', NULL, '#D9D9D9,#B2B2B2,#1F74AD', '思源黑体旧字形 ExtraLight,思源黑体 CN Bold', 5, 25.2),
('cat-22图标系列', '22图标系列', NULL, '#01ACBE,#FFB850,#663A77', '微软雅黑,Arial', 5, 112.6),
('cat-23图表风格', '23图表风格', NULL, '#FFC000,#20BA7C,#4CC1D0', '微软雅黑,Calibri', 5, 25.0),
('cat-24相册纪念', '24相册纪念', NULL, '#FFFFFF,#FCAA1A,#EA001E', '微软雅黑,华文新魏', 2, 16.5),
('cat-25星空风格', '25星空风格', NULL, '#FFFFFF,#A6A6A6,#FCA82C', '微软雅黑,Impact', 5, 25.6),
('cat-2极简风格', '2极简风格', NULL, '#404040,#EB7513,#0070C0', '微软雅黑,+mn-ea', 5, 23.4),
('cat-3工作汇报', '3工作汇报', NULL, '#FFFFFF,#0070C0,#FFC000', '微软雅黑,Calibri', 5, 29.0),
('cat-4毕业答辩', '4毕业答辩', NULL, '#FFFFFF,#E0A9CB,#F6F6F6', '微软雅黑,Impact', 5, 26.6),
('cat-5高端商务', '5高端商务', NULL, '#C00000,#BB1C14,#2B459C', '微软雅黑,Arial', 5, 24.4),
('cat-6中国风格', '6中国风格', NULL, '#C00000,#448377,#E8E7E3', '方正清刻本悦宋简体,+mj-ea', 5, 24.6),
('cat-7教师课件', '7教师课件', NULL, '#FFFFFF,#ADBACA,#0097A2', 'Arial,微软雅黑', 5, 24.4),
('cat-8简历求职', '8简历求职', NULL, '#2ABDC7,#4C4B50,#2DB2A4', '微软雅黑,Agency FB', 5, 26.6),
('cat-9清新文艺', '9清新文艺', NULL, '#29B9A6,#F8D35E,#F47264', '微软雅黑,Arial', 5, 31.0);

-- 模板数据（来自分析的120个模板，取代表性样本）
-- 每个类别取几个典型模板作为种子数据
INSERT OR REPLACE INTO templates (id, name, category, source_path, total_slides, preview, description, tags, color_scheme, font_scheme, default_numbering_id, is_system) VALUES
-- 毕业答辩类（学术场景）
('academic-defense-01', '毕业设计答辩-简约白', '4毕业答辩', 'F:\\ppt模板\\毕业答辩\\答辩简约.pptx', 24, NULL, '学术答辩标准模板，白底红字，简洁大方', '学术,答辩,毕业', '#FFFFFF,#C00000,#E0A9CB', '微软雅黑,Impact', 'chinese-paren', true),
('academic-defense-02', '毕业答辩-学术蓝', '4毕业答辩', 'F:\\ppt模板\\毕业答辩\\答辩蓝色.pptx', 28, NULL, '深蓝色调学术模板，适合理工科答辩', '学术,答辩,理工', '#0070C0,#FFFFFF,#ADBACA', '微软雅黑,Arial', 'chinese-paren', true),
('academic-defense-03', '开题报告-严谨风', '15开题报告', 'F:\\ppt模板\\开题报告\\开题严谨.pptx', 22, NULL, '开题报告专用模板，结构严谨', '学术,开题,报告', '#000000,#4A4E98,#EEC618', '字魂36号-正文宋楷,字魂59号-创粗黑', 'chinese-clause', true),
-- 中国风格类
('china-style-01', '中国风-古典红', '6中国风格', 'F:\\ppt模板\\中国风格\\古典红.pptx', 26, NULL, '中国传统红色主题，适合文化类汇报', '中国风,文化,传统', '#C00000,#448377,#E8E7E3', '方正清刻本悦宋简体,+mj-ea', 'chinese-clause', true),
('china-style-02', '中国风-水墨青', '6中国风格', 'F:\\ppt模板\\中国风格\\水墨青.pptx', 22, NULL, '水墨画风格，淡雅青色调', '中国风,水墨,淡雅', '#448377,#FFFFFF,#E8E7E3', '方正清刻本悦宋简体,微软雅黑', 'chinese-clause', true),
-- 快闪风格类
('flash-style-01', '快闪风格-活力橙', '13快闪风格', 'F:\\ppt模板\\快闪风格\\活力橙.pptx', 42, NULL, '动感快闪风格，橙色调充满活力', '快闪,活力,营销', '#FF5050,#D1F8CC,#16B39E', '微软雅黑,Bebas Neue', 'icon-check', true),
('flash-style-02', '快闪风格-科技蓝', '13快闪风格', 'F:\\ppt模板\\快闪风格\\科技蓝.pptx', 38, NULL, '科技感快闪风格，蓝绿色调', '快闪,科技,创新', '#16B39E,#0070C0,#FFFFFF', '微软雅黑,Impact', 'icon-arrow', true),
-- 培训课件类
('training-01', '培训课件-专业蓝', '11培训课件', 'F:\\ppt模板\\培训课件\\专业蓝.pptx', 40, NULL, '企业培训标准模板，专业稳重', '培训,企业,专业', '#F9F9F9,#DCDCDC,#D7D7D7', '微软雅黑,Impact', 'chinese-clause', true),
('training-02', '培训课件-活力绿', '11培训课件', 'F:\\ppt模板\\培训课件\\活力绿.pptx', 36, NULL, '轻松活泼的培训风格', '培训,教育,轻松', '#9BBB59,#FFFFFF,#F9F9F9', '微软雅黑,Arial', 'graphic-bullet', true),
-- 扁平风格类
('flat-style-01', '扁平风格-简约黄', '12扁平风格', 'F:\\ppt模板\\扁平风格\\简约黄.pptx', 24, NULL, '扁平化设计，黄白配色清新', '扁平,简约,现代', '#FFFFFF,#CCCC33,#FF6969', '微软雅黑,Arial', 'numeric-dot', true),
('flat-style-02', '扁平风格-极简白', '12扁平风格', 'F:\\ppt模板\\扁平风格\\极简白.pptx', 20, NULL, '极致简约，纯白背景', '扁平,极简,商务', '#FFFFFF,#000000,#A6A6A6', '微软雅黑,Arial', 'numeric-dot', true),
-- 图表风格类
('chart-style-01', '图表风格-数据蓝', '23图表风格', 'F:\\ppt模板\\图表风格\\数据蓝.pptx', 25, NULL, '数据可视化专业模板', '图表,数据,分析', '#FFC000,#20BA7C,#4CC1D0', '微软雅黑,Calibri', 'numeric-dot', true),
('chart-style-02', '图表风格-对比红', '23图表风格', 'F:\\ppt模板\\图表风格\\对比红.pptx', 22, NULL, '对比数据展示模板', '图表,对比,演示', '#FF0000,#FFFFFF,#F6F6F6', '微软雅黑,Arial', 'numeric-dot', true),
-- 企业宣传类
('corp-01', '企业宣传-商务蓝', '19企业宣传', 'F:\\ppt模板\\企业宣传\\商务蓝.pptx', 27, NULL, '标准企业宣传模板', '企业,宣传,商务', '#A6A6A6,#0070C0,#00A1DA', 'Arial,微软雅黑', 'numeric-dot', true),
('corp-02', '企业宣传-高端黑', '19企业宣传', 'F:\\ppt模板\\企业宣传\\高端黑.pptx', 25, NULL, '高端黑色商务风格', '企业,高端,商务', '#000000,#C00000,#D7D7D7', '微软雅黑,Arial', 'numeric-dot', true),
-- 述职报告类
('report-01', '述职报告-正式蓝', '21述职报告', 'F:\\ppt模板\\述职报告\\正式蓝.pptx', 25, NULL, '正式述职报告模板', '述职,报告,正式', '#D9D9D9,#B2B2B2,#1F74AD', '思源黑体旧字形 ExtraLight,思源黑体 CN Bold', 'chinese-paren', true),
('report-02', '述职报告-简洁灰', '21述职报告', 'F:\\ppt模板\\述职报告\\简洁灰.pptx', 22, NULL, '简洁灰调述职模板', '述职,报告,简洁', '#F9F9F9,#A6A6A6,#000000', '微软雅黑,Arial', 'chinese-paren', true),
-- 工作汇报类
('work-01', '工作汇报-效率橙', '3工作汇报', 'F:\\ppt模板\\工作汇报\\效率橙.pptx', 29, NULL, '高效工作汇报模板', '工作,汇报,效率', '#FFFFFF,#0070C0,#FFC000', '微软雅黑,Calibri', 'numeric-dot', true),
('work-02', '工作汇报-清新绿', '3工作汇报', 'F:\\ppt模板\\工作汇报\\清新绿.pptx', 27, NULL, '清新风格工作汇报', '工作,汇报,清新', '#29B9A6,#FFFFFF,#F8D35E', '微软雅黑,Arial', 'numeric-dot', true),
-- 项目策划类
('project-01', '项目策划-创新蓝', '14项目策划', 'F:\\ppt模板\\项目策划\\创新蓝.pptx', 31, NULL, '项目策划创新模板', '项目,策划,创新', '#0C86B6,#269FD3,#A6A6A6', '微软雅黑,Arial', 'level-nested', true),
('project-02', '项目策划-稳健灰', '14项目策划', 'F:\\ppt模板\\项目策划\\稳健灰.pptx', 29, NULL, '稳健风格项目策划', '项目,策划,稳健', '#A6A6A6,#FFFFFF,#000000', '微软雅黑,Arial', 'level-nested', true),
-- 简历求职类
('resume-01', '简历求职-时尚青', '8简历求职', 'F:\\ppt模板\\简历求职\\时尚青.pptx', 26, NULL, '时尚简历模板', '简历,求职,时尚', '#2ABDC7,#4C4B50,#2DB2A4', '微软雅黑,Agency FB', 'graphic-bullet', true),
('resume-02', '简历求职-专业蓝', '8简历求职', 'F:\\ppt模板\\简历求职\\专业蓝.pptx', 24, NULL, '专业简历模板', '简历,求职,专业', '#0070C0,#FFFFFF,#A6A6A6', '微软雅黑,Arial', 'numeric-dot', true),
-- 清新文艺类
('artsy-01', '清新文艺-樱花粉', '9清新文艺', 'F:\\ppt模板\\清新文艺\\樱花粉.pptx', 31, NULL, '清新文艺风格', '文艺,清新,粉色', '#29B9A6,#F8D35E,#F47264', '微软雅黑,Arial', 'graphic-circle', true),
('artsy-02', '清新文艺-薄荷绿', '9清新文艺', 'F:\\ppt模板\\清新文艺\\薄荷绿.pptx', 28, NULL, '薄荷绿清新风格', '文艺,清新,绿色', '#9BBB59,#FFFFFF,#F9F9F9', '微软雅黑,Arial', 'graphic-bullet', true),
-- 星空风格类
('space-01', '星空风格-深邃蓝', '25星空风格', 'F:\\ppt模板\\星空风格\\深邃蓝.pptx', 25, NULL, '星空主题深邃风格', '星空,深邃,创意', '#FFFFFF,#A6A6A6,#FCA82C', '微软雅黑,Impact', 'icon-star', true),
('space-02', '星空风格-宇宙紫', '25星空风格', 'F:\\ppt模板\\星空风格\\宇宙紫.pptx', 24, NULL, '紫色宇宙主题', '星空,宇宙,神秘', '#663A77,#FFFFFF,#E1E8F0', '微软雅黑,Arial', 'icon-star', true),
-- 欧美风格类
('europe-01', '欧美风格-简约灰', '10欧美风格', 'F:\\ppt模板\\欧美风格\\简约灰.pptx', 25, NULL, '欧美简约风格', '欧美,简约,国际', '#354B5E,#D5B07C,#D5D5D5', 'Arial,微软雅黑', 'numeric-dot', true),
('europe-02', '欧美风格-经典蓝', '10欧美风格', 'F:\\ppt模板\\欧美风格\\经典蓝.pptx', 24, NULL, '欧美经典风格', '欧美,经典,商务', '#0070C0,#FFFFFF,#A6A6A6', 'Arial,Calibri', 'numeric-dot', true),
-- 莫兰迪风格类
('morandi-01', '莫兰迪-低调绿', '1莫兰迪PPT', 'F:\\ppt模板\\莫兰迪\\低调绿.pptx', 17, NULL, '莫兰迪绿调，低调高级', '莫兰迪,高级,文艺', '#486553,#679378,#FFFFFF', '汉仪字酷堂义山楷W,思源黑体旧字形 Normal', 'chinese-clause', true),
('morandi-02', '莫兰迪-柔和粉', '1莫兰迪PPT', 'F:\\ppt模板\\莫兰迪\\柔和粉.pptx', 16, NULL, '莫兰迪粉调，温柔优雅', '莫兰迪,优雅,温柔', '#D7D7D7,#E87071,#FFFFFF', '微软雅黑,思源黑体旧字形 Normal', 'graphic-bullet', true),
-- 创意风格类
('creative-01', '创意风格-火焰橙', '16创意风格', 'F:\\ppt模板\\创意风格\\火焰橙.pptx', 22, NULL, '创意橙色主题', '创意,火焰,活力', '#FFFFFF,#F17831,#D76E17', '微软雅黑,+mj-lt', 'graphic-diamond', true),
('creative-02', '创意风格-海洋蓝', '16创意风格', 'F:\\ppt模板\\创意风格\\海洋蓝.pptx', 21, NULL, '海洋创意主题', '创意,海洋,清凉', '#0070C0,#01ACBE,#FFFFFF', '微软雅黑,Arial', 'icon-check', true),
-- 自我介绍类
('intro-01', '自我介绍-活力绿', '17自我介绍', 'F:\\ppt模板\\自我介绍\\活力绿.pptx', 14, NULL, '个人介绍活力风格', '介绍,个人,活力', '#FFFFFF,#99BF4F,#1CA854', '迷你简卡通,微软雅黑', 'graphic-circle', true),
('intro-02', '自我介绍-清新蓝', '17自我介绍', 'F:\\ppt模板\\自我介绍\\清新蓝.pptx', 13, NULL, '个人介绍清新风格', '介绍,个人,清新', '#FFFFFF,#0070C0,#E1E8F0', '微软雅黑,Arial', 'graphic-bullet', true),
-- 详情展示类
('detail-01', '详情展示-沉稳灰', '01 详情展示', 'F:\\ppt模板\\详情展示\\沉稳灰.pptx', 15, NULL, '详情页展示模板', '详情,展示,商务', '#504D47,#E1E8F0,#3C3939', '微软雅黑,Andalus', 'numeric-dot', true),
-- 图标系列类
('icon-01', '图标系列-多彩', '22图标系列', 'F:\\ppt模板\\图标系列\\多彩.pptx', 113, NULL, '图标展示模板，色彩丰富', '图标,展示,色彩', '#01ACBE,#FFB850,#663A77', '微软雅黑,Arial', 'graphic-circle', true),
('icon-02', '图标系列-商务', '22图标系列', 'F:\\ppt模板\\图标系列\\商务.pptx', 110, NULL, '商务图标展示模板', '图标,商务,专业', '#0070C0,#FFFFFF,#A6A6A6', '微软雅黑,Arial', 'numeric-dot', true),
-- 相册纪念类
('album-01', '相册纪念-温馨黄', '24相册纪念', 'F:\\ppt模板\\相册纪念\\温馨黄.pptx', 17, NULL, '相册纪念温馨风格', '相册,纪念,温馨', '#FFFFFF,#FCAA1A,#EA001E', '微软雅黑,华文新魏', 'graphic-circle', true),
-- 时尚风格类
('fashion-01', '时尚风格-优雅金', '20时尚风格', 'F:\\ppt模板\\时尚风格\\优雅金.pptx', 40, NULL, '时尚优雅金色调', '时尚,优雅,高端', '#C5AF76,#FFFFFF,#9DD6C8', 'Lato,Source Sans Pro', 'chinese-clause', true),
('fashion-02', '时尚风格-清新绿', '20时尚风格', 'F:\\ppt模板\\时尚风格\\清新绿.pptx', 41, NULL, '清新时尚绿色调', '时尚,清新,自然', '#29B9A6,#FFFFFF,#F8D35E', 'Lato,Arial', 'graphic-bullet', true),
-- 极简风格类
('minimal-01', '极简风格-黑白', '2极简风格', 'F:\\ppt模板\\极简风格\\黑白.pptx', 23, NULL, '极简黑白风格', '极简,黑白,现代', '#404040,#EB7513,#0070C0', '微软雅黑,+mn-ea', 'numeric-dot', true),
('minimal-02', '极简风格-纯白', '2极简风格', 'F:\\ppt模板\\极简风格\\纯白.pptx', 22, NULL, '极致纯白风格', '极简,纯白,干净', '#FFFFFF,#000000,#A6A6A6', '微软雅黑,Arial', 'numeric-dot', true),
-- 高端商务类
('business-01', '高端商务-酒红', '5高端商务', 'F:\\ppt模板\\高端商务\\酒红.pptx', 24, NULL, '高端酒红色商务模板', '商务,高端,酒红', '#C00000,#BB1C14,#2B459C', '微软雅黑,Arial', 'numeric-dot', true),
('business-02', '高端商务-深蓝', '5高端商务', 'F:\\ppt模板\\高端商务\\深蓝.pptx', 25, NULL, '高端深蓝商务模板', '商务,高端,深蓝', '#2B459C,#C00000,#FFFFFF', '微软雅黑,Arial', 'numeric-dot', true),
-- 教师课件类
('teacher-01', '教师课件-清新蓝', '7教师课件', 'F:\\ppt模板\\教师课件\\清新蓝.pptx', 24, NULL, '教师课件标准模板', '教师,课件,教育', '#FFFFFF,#ADBACA,#0097A2', 'Arial,微软雅黑', 'numeric-dot', true),
('teacher-02', '教师课件-温馨橙', '7教师课件', 'F:\\ppt模板\\教师课件\\温馨橙.pptx', 23, NULL, '温馨风格教师课件', '教师,课件,温馨', '#FFB850,#FFFFFF,#A6A6A6', '微软雅黑,Arial', 'chinese-clause', true),
-- 学术模板扩展（新增15个学术场景模板）
('academic-paper-01', '学术论文答辩-标准版', '4毕业答辩', 'F:\\ppt模板\\毕业答辩\\论文标准.pptx', 26, NULL, '学术论文答辩标准模板', '学术,论文,答辩', '#FFFFFF,#C00000,#ADBACA', '微软雅黑,Impact', 'chinese-paren', true),
('academic-paper-02', '学术论文答辩-理科版', '4毕业答辩', 'F:\\ppt模板\\毕业答辩\\论文理科.pptx', 28, NULL, '理工科论文答辩模板', '学术,理科,答辩', '#0070C0,#FFFFFF,#A6A6A6', '微软雅黑,Arial', 'chinese-paren', true),
('academic-paper-03', '学术论文答辩-文科版', '4毕业答辩', 'F:\\ppt模板\\毕业答辩\\论文文科.pptx', 24, NULL, '文科论文答辩模板', '学术,文科,答辩', '#D7D7D7,#C00000,#FFFFFF', '方正清刻本悦宋简体,微软雅黑', 'chinese-paren', true),
('academic-review-01', '文献综述答辩', '15开题报告', 'F:\\ppt模板\\开题报告\\文献综述.pptx', 25, NULL, '文献综述答辩专用', '学术,文献,综述', '#000000,#4A4E98,#FFFFFF', '字魂36号-正文宋楷,字魂59号-创粗黑', 'chinese-clause', true),
('academic-project-01', '科研项目汇报', '14项目策划', 'F:\\ppt模板\\项目策划\\科研汇报.pptx', 30, NULL, '科研项目汇报模板', '学术,科研,项目', '#0C86B6,#269FD3,#FFFFFF', '微软雅黑,Arial', 'level-nested', true),
('academic-report-01', '年度报告汇报', '21述职报告', 'F:\\ppt模板\\述职报告\\年度报告.pptx', 28, NULL, '学术研究年度报告', '学术,报告,年度', '#D9D9D9,#1F74AD,#FFFFFF', '思源黑体 CN Bold,微软雅黑', 'chinese-paren', true),
('academic-conference-01', '学术会议报告', '19企业宣传', 'F:\\ppt模板\\企业宣传\\学术会议.pptx', 22, NULL, '学术会议报告模板', '学术,会议,报告', '#A6A6A6,#0070C0,#FFFFFF', 'Arial,微软雅黑', 'numeric-dot', true),
('academic-thesis-01', '毕业论文答辩', '4毕业答辩', 'F:\\ppt模板\\毕业答辩\\毕业论文.pptx', 30, NULL, '毕业论文答辩完整模板', '学术,毕业,论文', '#FFFFFF,#C00000,#E0A9CB', '微软雅黑,Impact', 'chinese-paren', true),
('academic-defense-04', '答辩答辩-典雅风', '4毕业答辩', 'F:\\ppt模板\\毕业答辩\\典雅答辩.pptx', 22, NULL, '典雅风格答辩模板', '学术,答辩,典雅', '#F9F9F9,#C00000,#A6A6A6', '方正清刻本悦宋简体,微软雅黑', 'chinese-paren', true),
('academic-defense-05', '答辩答辩-现代风', '4毕业答辩', 'F:\\ppt模板\\毕业答辩\\现代答辩.pptx', 20, NULL, '现代简约答辩模板', '学术,答辩,现代', '#FFFFFF,#0070C0,#D7D7D7', '微软雅黑,Arial', 'numeric-dot', true),
('academic-project-02', '课题结题汇报', '14项目策划', 'F:\\ppt模板\\项目策划\\课题结题.pptx', 26, NULL, '课题结题汇报模板', '学术,课题,结题', '#269FD3,#FFFFFF,#A6A6A6', '微软雅黑,Arial', 'level-nested', true),
('academic-experiment-01', '实验报告展示', '11培训课件', 'F:\\ppt模板\\培训课件\\实验报告.pptx', 35, NULL, '实验报告展示模板', '学术,实验,报告', '#F9F9F9,#0070C0,#9BBB59', '微软雅黑,Calibri', 'numeric-dot', true),
('academic-data-01', '数据分析报告', '23图表风格', 'F:\\ppt模板\\图表风格\\数据分析.pptx', 24, NULL, '数据分析报告模板', '学术,数据,分析', '#FFC000,#20BA7C,#4CC1D0', '微软雅黑,Calibri', 'numeric-dot', true),
('academic-literature-01', '文献研读分享', '15开题报告', 'F:\\ppt模板\\开题报告\\文献研读.pptx', 18, NULL, '文献研读分享模板', '学术,文献,研读', '#4A4E98,#FFFFFF,#E8E7E3', '字魂36号-正文宋楷,微软雅黑', 'chinese-clause', true),
('academic-presentation-01', '学术演讲模板', '19企业宣传', 'F:\\ppt模板\\企业宣传\\学术演讲.pptx', 20, NULL, '学术演讲通用模板', '学术,演讲,通用', '#A6A6A6,#C00000,#FFFFFF', 'Arial,微软雅黑', 'chinese-paren', true);
