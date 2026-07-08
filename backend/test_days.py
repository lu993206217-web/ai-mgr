from datetime import date, datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.channel import Channel

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

today = date.today()
print(f"Today: {today}")

channels = db.query(Channel).all()
for channel in channels:
    print(f"\nChannel: {channel.channel_name}")
    print(f"  last_contact_date: {channel.last_contact_date}")
    print(f"  created_at: {channel.created_at}")
    
    days_since_last_contact = 0
    
    if channel.last_contact_date:
        try:
            last_contact_date = channel.last_contact_date
            if isinstance(last_contact_date, datetime):
                last_contact_date = last_contact_date.date()
            days_since_last_contact = (today - last_contact_date).days
        except Exception as e:
            print(f"  Error: {e}")
            days_since_last_contact = 0
    print(f"  After last_contact check: {days_since_last_contact}")
    
    if days_since_last_contact <= 0 and not channel.last_contact_date:
        print("  Entering created_at calculation")
        if channel.created_at:
            try:
                created_date = channel.created_at.date() if hasattr(channel.created_at, 'date') else today
                print(f"  created_date: {created_date}")
                days_since_last_contact = (today - created_date).days
                print(f"  days_since_last_contact: {days_since_last_contact}")
            except Exception as e:
                print(f"  Error: {e}")
                days_since_last_contact = 90
    print(f"  Final: {days_since_last_contact}")
