# Telegram Monitor 📱📧

[English](#english) | [中文](#中文)

---

## English

A secure and powerful Telegram monitoring script that forwards messages from channels, groups, and private chats to email with keyword filtering capabilities.

### ✨ Features

- **Multi-source Monitoring**: Monitor Telegram channels, groups, and private messages
- **Keyword Filtering**: Filter messages by keywords or forward all messages
- **Email Forwarding**: Automatic email notifications via SMTP
- **Hot Configuration Reload**: Update settings without restarting (checks every 5 seconds)
- **Environment Variables**: Secure configuration using `.env` files
- **Auto Dependency Management**: Automatically installs required dependencies
- **Cross-platform Support**: Works on Windows, Linux, and macOS
- **Virtual Environment**: Automatic virtual environment creation and management
- **Externally-managed Python**: Supports modern Python environments with multiple installation methods

### 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/william08190/telegram-monitor.git
   cd telegram-monitor
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual configuration
   ```

3. **Set up your configuration**
   - Get your Telegram API credentials from https://my.telegram.org/apps
   - Configure your SMTP email settings
   - Add channels/groups/users to monitor

### 📋 Configuration

#### Environment Variables (`.env` file)

```env
# Telegram API Configuration
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_SESSION=monitor_session

# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_SSL=false
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_app_password
TO_EMAILS=recipient1@example.com,recipient2@example.com
```

#### Configuration Files

- **`channels.txt`**: List Telegram channels to monitor (one per line)
- **`groups.txt`**: List Telegram groups to monitor (one per line)
- **`users.txt`**: List users for private message monitoring (one per line)
- **`keywords.txt`**: Keywords to filter messages (leave empty to forward all messages)

#### Example Configuration Files

**channels.txt**:
```
# Channels (one per line)
# Examples:
your_channel_name
-1001234567890
```

**keywords.txt**:
```
# Keywords (one per line)
# Leave empty for all messages
crypto
bitcoin
alert
```

### 🚀 Usage

1. **Run the script**
   ```bash
   python3 monitor_and_email.py
   ```

2. **Test email configuration**
   ```bash
   python3 monitor_and_email.py test
   ```

3. **First run**: The script will automatically:
   - Create a virtual environment
   - Install required dependencies (`telethon`, `python-dotenv`)
   - Create template configuration files
   - Prompt for Telegram authentication

### 🔒 Security Features

- **Environment Variables**: All sensitive data stored in environment variables
- **Git Ignored**: Sensitive files automatically excluded from version control
- **No Hardcoded Credentials**: Zero hardcoded API keys or passwords
- **Session Protection**: Telegram session files are git-ignored
- **Clean History**: No sensitive information in git history

### 📁 File Structure

```
telegram-monitor/
├── monitor_and_email.py    # Main script
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore rules
├── channels.txt           # Channels to monitor
├── groups.txt             # Groups to monitor
├── users.txt              # Users to monitor
├── keywords.txt           # Keyword filters
└── README.md              # This file
```

### 🛠 Requirements

- Python 3.7+
- Internet connection
- Telegram API credentials
- SMTP email account

### 📝 License

MIT License - feel free to use and modify for your needs.

### 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 中文

一个安全强大的 Telegram 监控脚本，可以将频道、群组和私聊消息通过关键词过滤转发到邮箱。

### ✨ 功能特点

- **多源监控**：监控 Telegram 频道、群组和私聊消息
- **关键词过滤**：根据关键词过滤消息或转发所有消息
- **邮件转发**：通过 SMTP 自动发送邮件通知
- **热配置重载**：无需重启即可更新设置（每5秒检查一次）
- **环境变量**：使用 `.env` 文件安全配置
- **自动依赖管理**：自动安装所需依赖
- **跨平台支持**：支持 Windows、Linux 和 macOS
- **虚拟环境**：自动创建和管理虚拟环境
- **外部管理的 Python**：支持现代 Python 环境，提供多种安装方法

### 🔧 安装

1. **克隆仓库**
   ```bash
   git clone https://github.com/william08190/telegram-monitor.git
   cd telegram-monitor
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入你的实际配置
   ```

3. **设置配置**
   - 从 https://my.telegram.org/apps 获取 Telegram API 凭据
   - 配置 SMTP 邮件设置
   - 添加要监控的频道/群组/用户

### 📋 配置说明

#### 环境变量（`.env` 文件）

```env
# Telegram API 配置
TELEGRAM_API_ID=your_api_id_here
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_SESSION=monitor_session

# SMTP 邮件配置
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USE_SSL=true
SMTP_USER=your_email@qq.com
SMTP_PASS=your_email_password_or_app_key
TO_EMAILS=recipient1@example.com,recipient2@example.com
```

#### 配置文件

- **`channels.txt`**：要监控的 Telegram 频道列表（每行一个）
- **`groups.txt`**：要监控的 Telegram 群组列表（每行一个）
- **`users.txt`**：私聊消息监控的用户列表（每行一个）
- **`keywords.txt`**：消息过滤关键词（留空则转发所有消息）

#### 配置文件示例

**channels.txt**：
```
# 频道（每行一个）
# 例子：
your_channel_name
-1001234567890
```

**keywords.txt**：
```
# 关键词（每行一个）
# 留空即全量转发
空投
暴涨
预警
```

### 🚀 使用方法

1. **运行脚本**
   ```bash
   python3 monitor_and_email.py
   ```

2. **测试邮件配置**
   ```bash
   python3 monitor_and_email.py test
   ```

3. **首次运行**：脚本会自动：
   - 创建虚拟环境
   - 安装所需依赖（`telethon`、`python-dotenv`）
   - 创建配置文件模板
   - 提示进行 Telegram 认证

### 🔒 安全特性

- **环境变量**：所有敏感数据存储在环境变量中
- **Git 忽略**：敏感文件自动排除在版本控制之外
- **无硬编码凭据**：零硬编码 API 密钥或密码
- **会话保护**：Telegram 会话文件被 git 忽略
- **干净历史**：git 历史中无敏感信息

### 📁 文件结构

```
telegram-monitor/
├── monitor_and_email.py    # 主脚本
├── .env.example           # 环境变量模板
├── .gitignore             # Git 忽略规则
├── channels.txt           # 监控频道
├── groups.txt             # 监控群组
├── users.txt              # 监控用户
├── keywords.txt           # 关键词过滤
└── README.md              # 本文件
```

### 🛠 系统要求

- Python 3.7+
- 网络连接
- Telegram API 凭据
- SMTP 邮箱账户

### 📝 许可证

MIT 许可证 - 可自由使用和修改。

### 🤝 贡献

欢迎贡献！请随时提交 Pull Request。

---

## 🔗 Links

- **Repository**: https://github.com/william08190/telegram-monitor
- **Issues**: https://github.com/william08190/telegram-monitor/issues
- **Telegram API**: https://my.telegram.org/apps

## 🏷️ Tags

`telegram` `monitor` `email` `python` `automation` `messaging` `notification` `security`