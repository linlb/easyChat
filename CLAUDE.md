# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EasyChat is a PC WeChat automation tool that provides both GUI and programmatic interfaces for bulk messaging, scheduled messaging, and auto-reply functionality. It uses Windows UI Automation (uiautomation) to interact with the desktop WeChat application rather than web-based APIs.

## Architecture

### Core Components

- **`ui_auto_wechat.py`** - Main automation engine with WeChat class containing all core functionality
- **`wechat_gui.py`** - PyQt5-based GUI application that provides user-friendly interface
- **`module.py`** - UI components and threading classes for the GUI
- **`wechat_locale.py`** - Multi-language support for WeChat UI elements (zh-CN, zh-TW, en-US)
- **`automation.py`** - Diagnostic tool for exploring Windows UI automation tree
- **`clipboard.py`** - Windows clipboard utilities for file operations
- **`pack.py`** - PyInstaller packaging script for creating standalone executable

### Key Classes

- **WeChat** (`ui_auto_wechat.py:57`) - Main automation class with methods for:
  - Opening/closing WeChat
  - Sending messages and files
  - Finding contacts and groups
  - Getting chat history
  - Auto-reply functionality

- **WechatGUI** (`wechat_gui.py:15`) - Main GUI window with PyQt5 interface

- **ClockThread** (`module.py:14`) - Background thread for scheduled messaging

### Configuration

- **wechat_config.json** - Auto-generated configuration file storing:
  - WeChat executable path
  - Contact lists
  - Message templates
  - Scheduled tasks
  - Language preferences

## Development Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run GUI application
python wechat_gui.py

# Run automation diagnostics
python automation.py -h
```

### Packaging
```bash
# Create standalone executable
python pack.py
```

### Testing Core Functions
```bash
# Test basic WeChat automation
python -c "from ui_auto_wechat import WeChat; w = WeChat('path/to/wechat'); w.find_all_contacts()"
```

## Key Functionality

### GUI Features
- Bulk messaging to multiple contacts
- Scheduled messaging with custom timing
- Auto-reply configuration
- Contact and group management
- File attachment support
- Multi-language WeChat support

### Programmatic API (ui_auto_wechat.py)
- `send_msg(name, at_names, text)` - Send message to contact, optionally @ mention
- `send_file(name, file_path)` - Send file to contact
- `find_all_contacts()` - Get all contacts with details
- `get_dialogs(name)` - Get chat history for contact
- `set_auto_reply(contacts, message)` - Configure auto-reply

## Important Notes

- **Windows Only**: Uses Windows UI Automation APIs
- **Desktop WeChat Required**: Does not work with web version
- **UI Language**: Supports zh-CN, zh-TW, en-US WeChat versions
- **Security**: Interacts with WeChat GUI elements - ensure proper permissions
- **Dependencies**: Requires uiautomation, PyQt5, pywin32, and other Windows-specific packages

## Common Development Tasks

### Adding New UI Elements
1. Update `wechat_locale.py` with new element mappings
2. Add corresponding automation methods in `ui_auto_wechat.py`
3. Update GUI in `wechat_gui.py` if needed

### Debugging Automation Issues
1. Use `python automation.py -c` to inspect UI elements
2. Check depth values and control types
3. Verify WeChat language settings match locale configuration

### Extending Message Types
1. Add new message type handling in `WeChat.send_msg()`
2. Update GUI message parsing in `wechat_gui.py`