#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
monitor_and_email.py
~~~~~~~~~~~~~~~~~~~~
Telegram 频道 / 群组 / 私聊 → 关键词过滤（或全量） → 邮件转发
支持热更新（每 5 秒轮询一次配置文件）
"""

import asyncio
import hashlib
import os
import smtplib
import subprocess
import sys
import time
from email.mime.text import MIMEText
from pathlib import Path

# 加载环境变量
def install_dotenv():
    """尝试安装python-dotenv，支持不同的安装方式"""
    print("⚠️ 未安装 python-dotenv，正在自动安装...")
    
    install_methods = [
        # 方法1：系统包管理器
        ["apt", "install", "-y", "python3-dotenv"],
        # 方法2：使用--break-system-packages（不推荐但有时必要）
        [sys.executable, "-m", "pip", "install", "python-dotenv", "--break-system-packages"],
        # 方法3：使用--user安装到用户目录
        [sys.executable, "-m", "pip", "install", "python-dotenv", "--user"],
        # 方法4：标准pip安装
        [sys.executable, "-m", "pip", "install", "python-dotenv"],
    ]
    
    for i, cmd in enumerate(install_methods, 1):
        try:
            print(f"尝试方法 {i}: {' '.join(cmd)}")
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"✅ 方法 {i} 安装成功")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"❌ 方法 {i} 失败，尝试下一种方法...")
            continue
    
    print("❌ 所有安装方法都失败，请手动安装:")
    print("   sudo apt install python3-dotenv")
    print("   或")  
    print("   python3 -m pip install python-dotenv --user")
    return False

try:
    from dotenv import load_dotenv
    load_dotenv()  # 从 .env 文件加载环境变量
except ImportError:
    if install_dotenv():
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✅ python-dotenv 加载成功")
        except ImportError:
            print("⚠️ 安装后仍无法导入，将使用系统环境变量")
    else:
        print("将使用系统环境变量")

# --------------------------------------------------------------------------- #
# 1. 常量 & 绝对路径
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent

CHANNELS_FILE = BASE_DIR / "channels.txt"
GROUPS_FILE   = BASE_DIR / "groups.txt"
USERS_FILE    = BASE_DIR / "users.txt"
KEYWORDS_FILE = BASE_DIR / "keywords.txt"

VENV_DIR      = BASE_DIR / "venv"
REQUIREMENTS  = ["telethon", "python-dotenv"]

# SMTP 配置 - 从环境变量获取
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TO_EMAILS = os.getenv("TO_EMAILS", "").split(",") if os.getenv("TO_EMAILS") else []

# --------------------------------------------------------------------------- #
# 2. 虚拟环境管理
# --------------------------------------------------------------------------- #

def create_virtualenv() -> None:
    """若 venv 目录不存在，自动创建并装 Telethon（及其它依赖）"""
    if VENV_DIR.exists():
        return

    print("创建虚拟环境 ...")
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])

    # 修复：根据操作系统选择正确的路径
    if os.name == 'nt':  # Windows
        pip_exe = VENV_DIR / "Scripts" / "pip.exe"
        python_exe = VENV_DIR / "Scripts" / "python.exe"
    else:  # Unix/Linux/Mac
        pip_exe = VENV_DIR / "bin" / "pip"
        python_exe = VENV_DIR / "bin" / "python"
    
    print("安装依赖 ...")
    subprocess.check_call([str(pip_exe), "install", "--upgrade", "pip"])
    subprocess.check_call([str(pip_exe), "install"] + REQUIREMENTS)


def run_main_script() -> None:
    """在子进程中以 venv 环境启动本脚本 (带 run 参数)"""
    # 修复：根据操作系统选择正确的路径
    if os.name == 'nt':  # Windows
        python_exe = VENV_DIR / "Scripts" / "python.exe"
    else:  # Unix/Linux/Mac
        python_exe = VENV_DIR / "bin" / "python"
    
    subprocess.check_call([str(python_exe), str(BASE_DIR / "monitor_and_email.py"), "run"])

# --------------------------------------------------------------------------- #
# 3. 配置文件读取帮助
# --------------------------------------------------------------------------- #

def file_hash(path: Path) -> str:
    """返回文件的 SHA‑256 码，如果不存在返回空字符串."""
    if not path.exists():
        return ""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


class Config:
    """自动监控配置文件变化，按需重新加载。"""

    def __init__(self) -> None:
        # 当前文件内容哈希，用于快速判断是否变动
        self._hashes = {
            "channels": "",
            "groups": "",
            "users": "",
            "keywords": "",
        }
        self._data = {
            "channels": [],
            "groups": [],
            "users": [],
            "keywords": [],
        }

    # --------- 内部统一读取 ----------
    def _load_file(self, path: Path, key: str):
        # 修复：文件不存在时创建空文件
        if not path.exists():
            path.touch()
        
        h = file_hash(path)
        if h == self._hashes[key]:
            return self._data[key]  # 无变动，直接返回缓存

        # 重新读取文件
        try:
            lines = [
                l.strip()
                for l in path.read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")
            ]
        except Exception as e:
            print(f"⚠️ 读取文件 {path} 失败: {e}")
            lines = []

        if key in ("channels", "groups"):
            items = []
            for l in lines:
                l = l.lstrip("@")
                if l.startswith("-"):
                    try:
                        items.append(int(l))
                    except Exception:
                        print(f"⚠️ 无效的 chat_id: {l}")
                else:
                    items.append(l)
        else:
            items = lines

        self._hashes[key] = h
        self._data[key] = items
        return items

    # --------- 公开 API ----------
    @property
    def channels(self):
        return self._load_file(CHANNELS_FILE, "channels")

    @property
    def groups(self):
        return self._load_file(GROUPS_FILE, "groups")

    @property
    def users(self):
        return self._load_file(USERS_FILE, "users")

    @property
    def keywords(self):
        kw = self._load_file(KEYWORDS_FILE, "keywords")
        monitor_all = len(kw) == 0
        return kw, monitor_all

    # 修复：缺失的方法定义
    def all_chats(self):
        """频道 + 群组 的完整列表 (可直接用作 chats= 参数)"""
        return self.channels + self.groups

# --------------------------------------------------------------------------- #
# 4. 邮件发送工具
# --------------------------------------------------------------------------- #

def test_email_config() -> bool:
    """测试邮件配置是否正常"""
    print("正在测试邮件配置...")
    try:
        subject = "【测试邮件】Telegram监控脚本"
        body = f"这是一封测试邮件，用于验证SMTP配置。\n\n测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        send_email(subject, body)
        return True
    except Exception as e:
        print(f"邮件测试失败: {e}")
        return False


def send_email(subject: str, body: str) -> None:
    """SMTP 发送邮件（同步），自动尝试SSL和TLS连接。"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(TO_EMAILS)
    msg["Subject"] = subject

    # 尝试不同的连接方式
    configs = [
        ("SSL", 465, True),
        ("TLS", 587, False),
    ]
    
    if not SMTP_USE_SSL:
        configs = configs[::-1]  # 如果配置不使用SSL，先尝试TLS
    
    last_error = None
    for method, port, use_ssl in configs:
        try:
            print(f"正在连接到 {SMTP_HOST}:{port}...")
            print(f"使用 {method} 连接")
            
            if use_ssl:
                # 使用SSL连接
                import ssl
                context = ssl.create_default_context()
                
                print("建立SSL连接...")
                server = smtplib.SMTP_SSL(SMTP_HOST, port, context=context)
                print("正在登录...")
                server.login(SMTP_USER, SMTP_PASS)
                
                print("正在发送邮件...")
                result = server.send_message(msg)
                server.quit()
                
                # 检查发送结果
                if not result:  # 空字典表示发送成功
                    print("邮件已发送")
                    return
                else:
                    print(f"部分发送失败: {result}")
                    return
            else:
                # 使用TLS连接
                print("建立TLS连接...")
                server = smtplib.SMTP(SMTP_HOST, port)
                
                print("启用TLS加密...")
                server.starttls()
                
                print("正在登录...")
                server.login(SMTP_USER, SMTP_PASS)
                
                print("正在发送邮件...")
                result = server.send_message(msg)
                server.quit()
                
                # 检查发送结果
                if not result:  # 空字典表示发送成功
                    print("邮件已发送")
                    return
                else:
                    print(f"部分发送失败: {result}")
                    return
                    
        except smtplib.SMTPException as e:
            last_error = e
            print(f"{method} SMTP错误: {e}")
        except Exception as e:
            last_error = e
            print(f"{method} 连接失败: {e}")
            
        # 如果是SSL失败且还有TLS选项，继续尝试
        if method == "SSL" and len(configs) > 1:
            print("尝试使用TLS连接...")
            continue
            
    # 如果所有方式都失败，显示详细错误信息
    print("所有连接方式都失败了")
    if isinstance(last_error, smtplib.SMTPAuthenticationError):
        print(f"SMTP 认证失败: {last_error}")
        print("请检查邮箱密码或授权码是否正确")
    elif isinstance(last_error, smtplib.SMTPConnectError):
        print(f"SMTP 连接失败: {last_error}")
        print("请检查网络连接和SMTP服务器设置")
    elif isinstance(last_error, smtplib.SMTPServerDisconnected):
        print(f"SMTP 服务器连接断开: {last_error}")
        print("请稍后重试")
    else:
        print(f"邮件发送失败: {last_error}")
        import traceback
        traceback.print_exc()

# --------------------------------------------------------------------------- #
# 5. 主程序（真正跑监听器）
# --------------------------------------------------------------------------- #

def main() -> None:
    """真正的运行逻辑（在 venv 里被调用）。"""
    # ---- 验证必要的环境变量 ----
    missing_vars = []
    
    # Telegram API 配置验证
    API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
    API_HASH = os.getenv("TELEGRAM_API_HASH", "")
    
    if API_ID == 0:
        missing_vars.append("TELEGRAM_API_ID")
    if not API_HASH:
        missing_vars.append("TELEGRAM_API_HASH")
    if not SMTP_USER:
        missing_vars.append("SMTP_USER")
    if not SMTP_PASS:
        missing_vars.append("SMTP_PASS")
    if not TO_EMAILS:
        missing_vars.append("TO_EMAILS")
    
    if missing_vars:
        print("缺少必要的环境变量:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n请创建 .env 文件或设置系统环境变量")
        sys.exit(1)
        
    try:
        from telethon import TelegramClient, events
    except ImportError:
        print("无法导入 telethon，请确保在正确的虚拟环境中运行")
        sys.exit(1)
    
    import traceback

    # ---- Telegram 登录参数 ----
    SESSION  = os.getenv("TELEGRAM_SESSION", "monitor_session")

    # ---- 创建设定文件模板 ----
    def create_templates() -> None:
        templates = {
            CHANNELS_FILE: (
                "# 频道（每行一个）\n"
                "# 例子：\n"
                "# your_channel_name\n"
                "# -1001234567890\n"
            ),
            GROUPS_FILE: (
                "# 群组（每行一个）\n"
                "# 例子：\n"
                "# mygroup\n"
                "# -1001234567890\n"
            ),
            USERS_FILE: (
                "# 私聊目标（每行一个）\n"
                "# 例子：\n"
                "# @username\n"
                "# 123456789\n"
            ),
            KEYWORDS_FILE: (
                "# 关键词（每行一个）\n"
                "# 留空即全量转发\n"
                "# 空投\n"
                "# 暴涨\n"
            ),
        }
        for path, content in templates.items():
            if not path.exists():
                path.write_text(content, encoding="utf-8")
                print(f"📁 已创建 {path.name}，请根据注释填入内容")

    create_templates()

    config = Config()
    user_cache: dict = {}       # 本地缓存用户 id -> entity
    sent_messages: set = set()  # 防止重复发送邮件的缓存
    start_time = time.time()    # 记录启动时间，避免处理历史消息

    client = TelegramClient(SESSION, API_ID, API_HASH)

    # --------- 监听器注册/更新 ----------
    async def reload_all_handlers() -> None:
        """在任何配置变化时，重新注册所有 NewMessage 处理器。"""
        nonlocal sent_messages, start_time  # 确保可以访问外部变量
        
        print("🧹 正在清理所有旧的事件处理器...")
        
        # 更新启动时间，防止配置重载时的历史消息干扰
        start_time = time.time()
        
        # 方法1: 尝试使用标准API移除所有NewMessage处理器
        removed_count = 0
        try:
            handlers_list = list(client.list_event_handlers())
            for callback, event in handlers_list:
                if isinstance(event, events.NewMessage):
                    client.remove_event_handler(callback, event)
                    removed_count += 1
            print(f"✅ 通过标准API移除了 {removed_count} 个处理器")
        except Exception as e:
            print(f"⚠️ 标准API移除失败: {e}")
        
        # 方法2: 直接清理内部数据结构（强制清理）
        try:
            # 清理 _event_builders (事件构建器)
            if hasattr(client, '_event_builders'):
                old_count = len(client._event_builders)
                builders_to_remove = []
                
                # 修复：检查 _event_builders 的类型
                if isinstance(client._event_builders, dict):
                    # 如果是字典，使用 keys() 方法
                    for key in client._event_builders.keys():
                        event_builder = key[0] if isinstance(key, tuple) else key
                        if isinstance(event_builder, events.NewMessage):
                            builders_to_remove.append(key)
                    
                    for key in builders_to_remove:
                        del client._event_builders[key]
                elif isinstance(client._event_builders, list):
                    # 如果是列表，直接遍历索引
                    for i in range(len(client._event_builders) - 1, -1, -1):
                        item = client._event_builders[i]
                        event_builder = item[0] if isinstance(item, tuple) else item
                        if isinstance(event_builder, events.NewMessage):
                            client._event_builders.pop(i)
                
                new_count = len(client._event_builders)
                print(f"🧹 从 _event_builders 清理了 {old_count - new_count} 个构建器")
            
            # 清理 _events_pending_resolve (待解析事件)
            if hasattr(client, '_events_pending_resolve'):
                client._events_pending_resolve.clear()
                print("🧹 清理了待解析事件")
                
            # 清理 handlers 字典中的 NewMessage 处理器
            if hasattr(client, 'handlers') and events.NewMessage in client.handlers:
                old_handlers = len(client.handlers[events.NewMessage])
                client.handlers[events.NewMessage].clear()
                print(f"🧹 清理了 {old_handlers} 个NewMessage处理器")
                
        except Exception as e:
            print(f"⚠️ 内部清理出错: {e}")
        
        print("✅ 事件处理器清理完成")
        
        # 清理消息去重缓存
        sent_messages.clear()
        print("🧹 清理消息缓存")

        # 频道 / 群组监听
        chats = config.all_chats()
        if chats:
            print(f"📺 重新注册频道/群组监听: {chats}")
            
            # 直接注册处理器，避免函数嵌套问题
            @client.on(events.NewMessage(chats=chats))
            async def channel_group_handler(event):
                try:
                    # 忽略启动前30秒的消息（避免处理历史消息）
                    if event.message.date.timestamp() < start_time - 30:
                        return
                        
                    chat = await event.get_chat()
                    msg_text = event.message.message
                    if not msg_text:
                        return

                    # 实时获取最新配置，防止使用过期配置
                    current_keywords, monitor_all = config.keywords
                    current_chats = config.all_chats()
                    
                    # 双重检查：确保当前聊天仍在配置列表中
                    chat_id = chat.id
                    chat_username = getattr(chat, "username", None)
                    
                    is_still_monitored = False
                    for monitored_chat in current_chats:
                        if isinstance(monitored_chat, int) and monitored_chat == chat_id:
                            is_still_monitored = True
                            break
                        elif isinstance(monitored_chat, str) and chat_username and monitored_chat == chat_username:
                            is_still_monitored = True
                            break
                    
                    if not is_still_monitored:
                        print(f"⏭️ 忽略已移除频道 {chat_username or chat_id} 的消息")
                        return

                    # 判定聊天类型（简化为频道/群组）
                    chat_type = "频道"
                    if getattr(chat, "megagroup", False):
                        chat_type = "群组"
                    elif getattr(chat, "title", None):
                        chat_type = "群组"

                    chat_name = chat_username or getattr(chat, "title", str(chat.id))

                    # 判断是否需要转发
                    if monitor_all or any(k.lower() in msg_text.lower() for k in current_keywords):
                        # 创建消息唯一标识符防重复发送
                        msg_id = f"{chat.id}_{event.message.id}_{time.strftime('%Y%m%d%H%M')}"
                        if msg_id in sent_messages:
                            print(f"⏭️ 跳过重复消息: {msg_id}")
                            return
                        
                        sent_messages.add(msg_id)
                        # 限制缓存大小，保留最近1000条
                        if len(sent_messages) > 1000:
                            sent_messages.pop()
                        
                        print(f"📬 发送邮件: 【Telegram{chat_type}】{chat_name} (消息时间: {event.message.date})")
                        subject = f"【Telegram{chat_type}】{chat_name}"
                        body = (
                            f"{chat_type}: {chat_name}\n"
                            f"ID: {chat.id}\n"
                            f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"内容:\n{msg_text}"
                        )
                        send_email(subject, body)
                except Exception:
                    print("❌ 处理频道/群组消息时错误:")
                    traceback.print_exc()
        else:
            print("📺 未配置频道/群组监听")

        # 私聊监听
        users_count = len(config.users)
        if users_count > 0:
            print(f"👤 重新注册私聊监听: {config.users}")
            
            # 直接注册私聊处理器
            @client.on(events.NewMessage(incoming=True))
            async def private_handler(event):
                try:
                    # 忽略启动前30秒的消息（避免处理历史消息）
                    if event.message.date.timestamp() < start_time - 30:
                        return
                        
                    if not event.is_private:
                        return
                    sender = await event.get_sender()
                    msg_text = event.message.message
                    if not msg_text:
                        return

                    # 实时获取最新用户配置
                    current_users = config.users
                    if not current_users:  # 如果没有配置用户，直接返回
                        return

                    # 判断发送者是否在关注列表
                    matched = False
                    for uid in current_users:
                        target = await get_user_entity(uid)
                        if target and target.id == sender.id:
                            matched = True
                            break
                    if not matched:
                        return

                    current_keywords, monitor_all = config.keywords
                    if monitor_all or any(k.lower() in msg_text.lower() for k in current_keywords):
                        # 创建消息唯一标识符防重复发送
                        msg_id = f"{sender.id}_{event.message.id}_{time.strftime('%Y%m%d%H%M')}"
                        if msg_id in sent_messages:
                            print(f"⏭️ 跳过重复私聊消息: {msg_id}")
                            return
                        
                        sent_messages.add(msg_id)
                        # 限制缓存大小，保留最近1000条
                        if len(sent_messages) > 1000:
                            sent_messages.pop()
                        
                        sender_name = (
                            getattr(sender, "username", None)
                            or f"{getattr(sender, 'first_name', '')} {getattr(sender, 'last_name', '')}".strip()
                        ).strip() or f"ID:{sender.id}"
                        
                        print(f"📬 发送邮件: 【Telegram私聊】{sender_name} (消息时间: {event.message.date})")
                        subject = f"【Telegram私聊】{sender_name}"
                        body = (
                            f"发送者: {sender_name}\n"
                            f"ID: {sender.id}\n"
                            f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"内容:\n{msg_text}"
                        )
                        send_email(subject, body)
                except Exception:
                    print("❌ 处理私聊消息时错误:")
                    traceback.print_exc()
        else:
            print("👤 未配置私聊用户监听")
        
        print("🎯 所有事件处理器重新注册完成")

    # --------- 监控配置 ----------
    async def monitor_config() -> None:
        """每 5 秒检查一次四个配置文件，变动即刷新监听器。"""
        # 初始化时等待一小段时间，避免启动时的文件操作干扰
        await asyncio.sleep(2)
        
        last_hashes = {
            "channels": file_hash(CHANNELS_FILE),
            "groups": file_hash(GROUPS_FILE),
            "users": file_hash(USERS_FILE),
            "keywords": file_hash(KEYWORDS_FILE),
        }
        
        print(f"📋 开始监控配置文件变化...")

        while True:
            try:
                await asyncio.sleep(5)   # 每5秒检查一次
                
                changed = False
                changed_files = []
                for key, path in [
                    ("channels", CHANNELS_FILE),
                    ("groups", GROUPS_FILE),
                    ("users", USERS_FILE),
                    ("keywords", KEYWORDS_FILE),
                ]:
                    h = file_hash(path)
                    if h != last_hashes[key]:
                        changed = True
                        changed_files.append(path.name)
                        last_hashes[key] = h

                if changed:
                    print(f"🔄 配置文件 {', '.join(changed_files)} 发生变化，重新注册监听器…")
                    await reload_all_handlers()
            except Exception:
                print("❌ 监控配置时异常:")
                traceback.print_exc()

    # --------- 用户实体缓存 ----------
    async def get_user_entity(user_identifier):
        """返回用户实体，支持 int、@username、姓名等。"""
        if user_identifier in user_cache:
            return user_cache[user_identifier]
        try:
            # 修复：处理不同类型的用户标识符
            if isinstance(user_identifier, str) and user_identifier.isdigit():
                user_identifier = int(user_identifier)
            elif isinstance(user_identifier, str) and user_identifier.startswith("@"):
                user_identifier = user_identifier[1:]
            
            entity = await client.get_entity(user_identifier)
            user_cache[user_identifier] = entity
            return entity
        except Exception as exc:
            print(f"⚠️ 无法获取用户 {user_identifier}: {exc}")
            return None

    # --------- 主循环 ----------
    async def main_loop() -> None:
        try:
            await client.start()
            print("✅ 已连接到 Telegram")
        except Exception as e:
            print(f"❌ 连接 Telegram 失败: {e}")
            return

        await reload_all_handlers()          # 初始注册
        config_task = asyncio.create_task(monitor_config())

        print("✅ Telegram 监听已启动！")
        try:
            await client.run_until_disconnected()
        finally:
            config_task.cancel()
            try:
                await config_task
            except asyncio.CancelledError:
                pass

    # 修复：使用正确的异步运行方式
    async def run_async():
        async with client:
            await main_loop()

    asyncio.run(run_async())

# --------------------------------------------------------------------------- #
# 6. CLI 入口
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        # 已经在 venv 环境下启动 → 直接跑主程序
        main()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # 测试邮件配置
        create_virtualenv()
        # 在venv环境中测试邮件
        if os.name == 'nt':  # Windows
            python_exe = VENV_DIR / "Scripts" / "python.exe"
        else:  # Unix/Linux/Mac
            python_exe = VENV_DIR / "bin" / "python"
        
        # 创建临时测试脚本
        test_script = f'''
import sys
sys.path.insert(0, r"{BASE_DIR}")
from monitor_and_email import test_email_config
test_email_config()
'''
        test_file = BASE_DIR / "temp_test.py"
        test_file.write_text(test_script, encoding="utf-8")
        
        try:
            subprocess.run([str(python_exe), str(test_file)], check=True)
        finally:
            if test_file.exists():
                test_file.unlink()
    else:
        # 第一阶段：创建/更新 venv，并以子进程方式重新启动
        create_virtualenv()
        # 若你想使用 watchdog，只需把它加到 REQUIREMENTS 并在 run_main_script() 内安装
        run_main_script()