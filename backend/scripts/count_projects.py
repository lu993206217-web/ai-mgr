"""
查询数据库中的项目数量
"""
import sys
sys.path.insert(0, '.')

from sqlalchemy import func
from app.db.session import SessionLocal
from app.models.project import Project
from app.models.customer import Customer
from app.models.channel import Channel

def main():
    db = SessionLocal()
    try:
        # 查询项目总数
        total_projects = db.query(Project).count()
        print(f"项目总数: {total_projects}")

        # 查询项目状态分布
        print("\n项目状态分布:")
        status_counts = db.query(Project.status, func.count(Project.id)).group_by(Project.status).all()
        for status, count in status_counts:
            print(f"  {status}: {count}")

        # 查询所有项目名称
        print("\n所有项目列表:")
        projects = db.query(Project).all()
        for p in projects:
            print(f"  ID: {p.id}, 名称: {p.project_name}, 状态: {p.status}, 客户ID: {p.customer_id}, 渠道ID: {p.channel_id}")

        # 查询所有已归档项目（用字符串值匹配）
        archived_projects = db.query(Project).filter(
            Project.status == '已归档'
        ).all()

        print(f"\n找到 {len(archived_projects)} 个已归档项目:")
        for p in archived_projects:
            print(f"  - ID: {p.id}, 名称: {p.project_name}, 状态: {p.status}")

        if not archived_projects:
            print("没有需要删除的已归档项目")
            return

        # 真实删除
        print("\n开始删除...")
        deleted_count = 0
        for p in archived_projects:
            try:
                db.delete(p)
                db.commit()
                print(f"  ✓ 已删除: {p.project_name}")
                deleted_count += 1
            except Exception as e:
                db.rollback()
                print(f"  ✗ 删除失败: {p.project_name}, 错误: {e}")

        print(f"\n删除完成，共删除 {deleted_count} 个项目")

        # 再次查询
        remaining = db.query(Project).count()
        print(f"剩余项目数量: {remaining}")

    finally:
        db.close()

if __name__ == "__main__":
    main()
