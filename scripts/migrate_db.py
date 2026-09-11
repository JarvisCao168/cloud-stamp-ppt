#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Database migration script"""

import sqlite3

src_db = r'D:\yzppt\yunzhang.db'
dst_db = r'D:\yzppt\backend\yunzhang.db'

def migrate_table(cursor_src, cursor_dst, table_name, src_cols, dst_cols):
    """迁移单个表的数据"""
    # 清空目标表
    cursor_dst.execute(f"DELETE FROM {table_name}")
    
    # 读取源数据
    cursor_src.execute(f"SELECT {','.join(src_cols)} FROM {table_name}")
    rows = cursor_src.fetchall()
    
    # 插入目标表（添加id列）
    placeholders = ','.join(['?'] * len(dst_cols))
    for i, row in enumerate(rows, 1):
        values = (i,) + row
        cursor_dst.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", values)
    
    print(f"  OK {table_name}: {len(rows)} rows")
    return len(rows)

def main():
    print("=" * 50)
    print("Database Migration Script")
    print("=" * 50)
    
    # 连接源数据库
    conn_src = sqlite3.connect(src_db)
    cursor_src = conn_src.cursor()
    
    # 连接目标数据库
    for attempt in range(10):
        try:
            conn_dst = sqlite3.connect(dst_db, timeout=30)
            cursor_dst = conn_dst.cursor()
            break
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                import time
                time.sleep(2)
            else:
                raise
    
    print("\nStarting migration...\n")
    
    try:
        # 1. color_palettes
        print("1. Migrating color_palettes")
        src_cols = ['hex_color', 'category', 'tags', 'usage_count', 'created_at']
        dst_cols = ['id', 'hex_color', 'category', 'tags', 'usage_count', 'created_at']
        count = migrate_table(cursor_src, cursor_dst, 'color_palettes', src_cols, dst_cols)
        
        # 2. font_library
        print("\n2. Migrating font_library")
        src_cols = ['font_name', 'font_type', 'tags', 'usage_count', 'created_at']
        dst_cols = ['id', 'font_name', 'font_type', 'tags', 'usage_count', 'created_at']
        count = migrate_table(cursor_src, cursor_dst, 'font_library', src_cols, dst_cols)
        
        # 3. template_categories
        print("\n3. Migrating template_categories")
        src_cols = ['category_name', 'description', 'default_colors', 'default_fonts', 'template_count', 'avg_slides', 'created_at']
        dst_cols = ['id', 'category_name', 'description', 'default_colors', 'default_fonts', 'template_count', 'avg_slides', 'created_at']
        count = migrate_table(cursor_src, cursor_dst, 'template_categories', src_cols, dst_cols)
        
        # 提交更改
        conn_dst.commit()
        print("\nData migration completed!")
        
        # 验证
        print("\nVerification:")
        for table in ['color_palettes', 'font_library', 'template_categories', 'numbering_styles', 'templates']:
            try:
                cursor_dst.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor_dst.fetchone()[0]
                print(f"  {table}: {count} rows")
            except Exception as e:
                print(f"  {table}: ERROR - {e}")
        
    finally:
        conn_src.close()
        conn_dst.close()
    
    print("\n" + "=" * 50)

if __name__ == '__main__':
    main()
