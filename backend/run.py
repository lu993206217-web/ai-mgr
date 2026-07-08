#!/usr/bin/env python3
"""
AI 项目推进控制塔 - 启动脚本

支持以下启动模式：
- dev: 开发模式（自动重载）
- prod: 生产模式（多进程）
- debug: 调试模式（单进程 + 详细日志）
"""

import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from app.core.config import settings


def create_tables():
    """创建数据库表（不使用 Alembic 迁移时使用）"""
    print("📊 正在创建数据库表...")
    from app.db.session import Base, sync_engine
    from app import models  # 必须导入，否则表不会被创建
    
    try:
        Base.metadata.create_all(bind=sync_engine)
        print("✅ 数据库表创建成功")
        return True
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
        return False


def init_database():
    """初始化数据库（创建表 + 初始数据）"""
    print("🚀 正在初始化数据库...")
    
    # 1. 创建表
    if not create_tables():
        return False
    
    # 2. 创建初始数据
    print("📝 正在创建初始数据...")
    from app.db.session import SessionLocal
    from app.core.security import get_password_hash
    from app.models.user import User
    from app.models.warning import WarningRule
    from datetime import datetime
    
    db = SessionLocal()
    try:
        # 创建管理员用户
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@ai-control-tower.com",
                full_name="系统管理员",
                hashed_password=get_password_hash("admin123"),
                role="管理员",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_login_at=None,
            )
            db.add(admin)
            print("  ✓ 创建管理员用户: admin / admin123")
        
        # 创建测试用户
        test_user = db.query(User).filter(User.username == "test").first()
        if not test_user:
            test_user = User(
                username="test",
                email="test@ai-control-tower.com",
                full_name="测试用户",
                hashed_password=get_password_hash("test123"),
                role="项目经理",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                last_login_at=None,
            )
            db.add(test_user)
            print("  ✓ 创建测试用户: test / test123")
        
        # 创建内置预警规则
        rules = [
            {
                "rule_name": "无跟进预警",
                "rule_code": "R001",
                "description": "项目超过7天无活动记录",
                "conditions": {"field": "last_activity_at", "operator": "<", "value": "7d"},
                "severity": "关注",
                "notify_targets": ["project_owner", "pmo"],
                "notify_channels": ["system"],
                "cooldown_days": 7,
            },
            {
                "rule_name": "验收超时预警",
                "rule_code": "R002",
                "description": "项目在验收阶段停留超过30天",
                "conditions": {"field": "current_stage", "operator": "=", "value": "验收", "duration": ">30d"},
                "severity": "风险",
                "notify_targets": ["project_owner", "pmo"],
                "notify_channels": ["system"],
                "cooldown_days": 7,
            },
            {
                "rule_name": "POC超时预警",
                "rule_code": "R003",
                "description": "项目在POC阶段停留超过60天",
                "conditions": {"field": "current_stage", "operator": "=", "value": "POC", "duration": ">60d"},
                "severity": "风险",
                "notify_targets": ["project_owner"],
                "notify_channels": ["system"],
                "cooldown_days": 14,
            },
            {
                "rule_name": "报价后无进展预警",
                "rule_code": "R004",
                "description": "报价超过90天未形成项目",
                "conditions": {"field": "quote_date", "operator": "<", "value": "90d", "no_project": True},
                "severity": "关注",
                "notify_targets": ["project_owner"],
                "notify_channels": ["system"],
                "cooldown_days": 30,
            },
            {
                "rule_name": "渠道沉没预警",
                "rule_code": "R005",
                "description": "渠道超过60天无活动记录",
                "conditions": {"field": "last_contact_date", "operator": "<", "value": "60d"},
                "severity": "关注",
                "notify_targets": ["channel_owner"],
                "notify_channels": ["system"],
                "cooldown_days": 30,
            },
            {
                "rule_name": "假性推进预警",
                "rule_code": "R006",
                "description": "连续3次活动内容为等待客户反馈",
                "conditions": {"field": "next_action", "operator": "=", "value": "等待客户反馈", "consecutive": 3},
                "severity": "风险",
                "notify_targets": ["project_owner", "pmo"],
                "notify_channels": ["system"],
                "cooldown_days": 7,
            },
            {
                "rule_name": "项目长期未验收预警",
                "rule_code": "R007",
                "description": "项目已签约但超过180天未验收",
                "conditions": {"field": "planned_acceptance", "operator": "<", "value": "180d", "status": "进行中"},
                "severity": "严重",
                "notify_targets": ["project_owner", "pmo", "ceo"],
                "notify_channels": ["system", "dingtalk"],
                "cooldown_days": 3,
            },
        ]
        
        for rule_data in rules:
            existing = db.query(WarningRule).filter(WarningRule.rule_code == rule_data["rule_code"]).first()
            if not existing:
                rule = WarningRule(
                    **rule_data,
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    created_by=admin.id if admin else None,
                    updated_by=admin.id if admin else None,
                )
                db.add(rule)
                print(f"  ✓ 创建预警规则: {rule_data['rule_code']} - {rule_data['rule_name']}")
        
        db.commit()
        print("✅ 初始数据创建成功")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ 初始数据创建失败: {e}")
        return False
    finally:
        db.close()


def start_dev():
    """启动开发模式（自动重载）"""
    print(f"🚧 启动开发模式...")
    print(f"📍 地址: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API 文档: http://{settings.HOST}:{settings.PORT}/api/docs")
    print(f"🔄 自动重载: 已启用")
    print("-" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        reload_dirs=[str(PROJECT_ROOT / "app")],
        log_level=settings.LOG_LEVEL.lower(),
    )


def start_prod():
    """启动生产模式（多进程）"""
    print(f"🚀 启动生产模式...")
    print(f"📍 地址: http://{settings.HOST}:{settings.PORT}")
    print(f"👥 工作进程数: {os.cpu_count()}")
    print("-" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=min(os.cpu_count() or 1, 4),
        log_level=settings.LOG_LEVEL.lower(),
    )


def start_debug():
    """启动调试模式（单进程 + 详细日志）"""
    print(f"🐛 启动调试模式...")
    print(f"📍 地址: http://{settings.HOST}:{settings.PORT}")
    print(f"📚 API 文档: http://{settings.HOST}:{settings.PORT}/api/docs")
    print(f"🔍 详细日志: 已启用")
    print("-" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="debug",
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AI 项目推进控制塔 - 启动脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py dev              # 开发模式
  python run.py prod             # 生产模式
  python run.py debug            # 调试模式
  python run.py init-db         # 初始化数据库
  python run.py create-tables   # 仅创建数据库表
        """
    )
    
    parser.add_argument(
        "command",
        choices=["dev", "prod", "debug", "init-db", "create-tables"],
        help="启动命令",
    )
    
    args = parser.parse_args()
    
    if args.command == "init-db":
        # 初始化数据库
        if init_database():
            sys.exit(0)
        else:
            sys.exit(1)
    
    elif args.command == "create-tables":
        # 仅创建数据库表
        if create_tables():
            sys.exit(0)
        else:
            sys.exit(1)
    
    elif args.command == "dev":
        # 开发模式
        start_dev()
    
    elif args.command == "prod":
        # 生产模式
        start_prod()
    
    elif args.command == "debug":
        # 调试模式
        start_debug()


if __name__ == "__main__":
    main()
