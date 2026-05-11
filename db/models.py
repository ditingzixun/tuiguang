"""数据库模型定义"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, ForeignKey, JSON, create_engine, event
)
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.pool import StaticPool

Base = declarative_base()


class AccountGroup(Base):
    """账号分组"""
    __tablename__ = "account_groups"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    daily_limit = Column(Integer, default=20)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    accounts = relationship("Account", back_populates="group", cascade="all, delete-orphan")


class Account(Base):
    """平台账号"""
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("account_groups.id"), nullable=True)
    platform = Column(String(50), nullable=False)
    username = Column(String(100), nullable=False)
    password = Column(String(200), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    cookies_path = Column(String(500))
    profile_path = Column(String(500))
    user_agent = Column(Text)
    fingerprint_config = Column(JSON)
    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=True)
    status = Column(String(20), default="active")  # active / limited / banned / expired
    login_status = Column(String(20), default="pending")  # pending / success / failed
    score = Column(Integer, default=100)  # 账号健康分
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    group = relationship("AccountGroup", back_populates="accounts")
    proxy = relationship("Proxy", back_populates="accounts")
    publish_records = relationship("PublishRecord", back_populates="account")


class Proxy(Base):
    """代理IP"""
    __tablename__ = "proxies"
    id = Column(Integer, primary_key=True, autoincrement=True)
    protocol = Column(String(10), default="http")
    host = Column(String(100), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(100))
    password = Column(String(100))
    region = Column(String(50))
    fail_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    latency = Column(Float)
    last_check_at = Column(DateTime)
    status = Column(String(20), default="available")  # available / failed / expired
    created_at = Column(DateTime, default=datetime.now)
    accounts = relationship("Account", back_populates="proxy")


class PublishTask(Base):
    """发布任务"""
    __tablename__ = "publish_tasks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    platform = Column(String(50), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    content_id = Column(Integer, ForeignKey("contents.id"))
    title = Column(String(200))
    content = Column(Text)
    status = Column(String(20), default="pending")  # pending / running / success / failed / retrying
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    result_url = Column(Text)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    publish_record = relationship("PublishRecord", back_populates="task", uselist=False)


class Content(Base):
    """文案库"""
    __tablename__ = "contents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50))  # soft_article / science_article / comparison_article / policy_article / case_study
    qualification_type = Column(String(100))  # 文网文/ICP/EDI
    keywords = Column(String(500))
    source = Column(String(50), default="ai")  # ai / manual / spin
    original_content_id = Column(Integer)  # 伪原创原始ID
    used_count = Column(Integer, default=0)
    status = Column(String(20), default="approved")  # draft / approved / archived
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class PublishRecord(Base):
    """发布记录"""
    __tablename__ = "publish_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("publish_tasks.id"))
    account_id = Column(Integer, ForeignKey("accounts.id"))
    platform = Column(String(50), nullable=False)
    title = Column(String(200))
    url = Column(Text)
    screenshot_path = Column(String(500))
    status = Column(String(20), default="pending")  # pending / published / failed / deleted
    publish_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    task = relationship("PublishTask", back_populates="publish_record")
    account = relationship("Account", back_populates="publish_records")


class PublishLog(Base):
    """发布日志"""
    __tablename__ = "publish_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("publish_tasks.id"))
    platform = Column(String(50))
    level = Column(String(20), default="INFO")  # INFO / WARNING / ERROR
    message = Column(Text)
    screenshot_path = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)


class SeoKeyword(Base):
    """SEO关键词"""
    __tablename__ = "seo_keywords"
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(200), nullable=False)
    group = Column(String(50))
    search_engine = Column(String(20), default="baidu")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.now)


class SeoRanking(Base):
    """SEO排名记录"""
    __tablename__ = "seo_rankings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword_id = Column(Integer, ForeignKey("seo_keywords.id"))
    keyword = Column(String(200))
    search_engine = Column(String(20))
    rank = Column(Integer)
    url = Column(Text)
    title = Column(String(300))
    is_indexed = Column(Boolean, default=False)
    check_time = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)


class PlatformConfig(Base):
    """平台配置模板"""
    __tablename__ = "platform_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_name = Column(String(50), nullable=False, unique=True)
    plugin_name = Column(String(100), nullable=False)
    platform_type = Column(String(20), default="b2b")  # b2b / classified / media / forum
    login_url = Column(String(500))
    publish_url = Column(String(500))
    form_config = Column(JSON)  # 表单字段映射
    selectors = Column(JSON)  # CSS选择器配置
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SystemConfig(Base):
    """系统配置键值对"""
    __tablename__ = "system_configs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(Text)
    category = Column(String(50))
    description = Column(String(200))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SmsRecord(Base):
    """短信验证码记录"""
    __tablename__ = "sms_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False)
    platform = Column(String(50))
    code = Column(String(10))
    status = Column(String(20), default="pending")  # pending / sent / verified / failed
    response_text = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
