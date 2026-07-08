"""
数据库初始化脚本

创建默认管理员用户和初始数据。
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User as UserModel
from app.db.base_class import Base


def init_data():
    """初始化默认数据"""
    # 创建数据库连接
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        print("✅ 数据表创建成功")

        # 检查是否已存在管理员用户
        admin_user = db.query(UserModel).filter(UserModel.username == "admin").first()
        
        if not admin_user:
            # 创建默认管理员用户
            admin = UserModel(
                username="admin",
                email="admin@example.com",
                full_name="系统管理员",
                role="管理员",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print("✅ 默认管理员创建成功")
            print("   用户名: admin")
            print("   密码: admin123")
        else:
            print("⚠️  管理员用户已存在，跳过创建")

        # 创建其他默认用户
        default_users = [
            {
                "username": "manager",
                "email": "manager@example.com",
                "full_name": "项目经理",
                "role": "项目经理",
                "password": "manager123",
            },
            {
                "username": "sales",
                "email": "sales@example.com",
                "full_name": "销售专员",
                "role": "销售",
                "password": "sales123",
            },
            {
                "username": "ops",
                "email": "ops@example.com",
                "full_name": "运维工程师",
                "role": "运维",
                "password": "ops123",
            },
        ]

        for user_data in default_users:
            existing = db.query(UserModel).filter(UserModel.username == user_data["username"]).first()
            if not existing:
                user = UserModel(
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    hashed_password=get_password_hash(user_data["password"]),
                    is_active=True,
                )
                db.add(user)
                db.commit()
                print(f"✅ 创建用户: {user_data['username']}")
            else:
                print(f"⚠️  用户 {user_data['username']} 已存在，跳过创建")

        print("\n🎉 数据初始化完成！")

    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_data()
