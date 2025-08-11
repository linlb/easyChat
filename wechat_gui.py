#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox, 
                             QCheckBox, QFileDialog, QMessageBox, QTabWidget, QGroupBox,
                             QSplitter, QProgressBar, QSpinBox, QDoubleSpinBox, QFrame,
                             QScrollArea, QGridLayout, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

from ui_auto_wechat import WeChat
from flask_server import WeChatFlaskServer


class WeChatAutomationThread(QThread):
    """微信自动化工作线程"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, wechat_instance, operation_type, **kwargs):
        super().__init__()
        self.wechat = wechat_instance
        self.operation_type = operation_type
        self.kwargs = kwargs
        self.running = True
    
    def run(self):
        try:
            if self.operation_type == "send_msg":
                self.send_messages()
            elif self.operation_type == "send_at_msg":
                self.send_at_messages()
            elif self.operation_type == "load_contacts":
                self.load_contacts()
            elif self.operation_type == "load_groups":
                self.load_groups()
            elif self.operation_type == "load_txt":
                self.load_txt_content()
            elif self.operation_type == "load_users_txt":
                self.load_users_txt()
            
            self.finished_signal.emit(True, "操作完成")
            
        except Exception as e:
            self.finished_signal.emit(False, str(e))
    
    def stop(self):
        self.running = False
    
    def send_messages(self):
        """发送普通消息"""
        recipients = self.kwargs.get('recipients', [])
        message = self.kwargs.get('message', '')
        interval = self.kwargs.get('interval', 1)
        
        total = len(recipients)
        for i, recipient in enumerate(recipients):
            if not self.running:
                break
            
            self.status_updated.emit(f"正在发送给 {recipient}...")
            self.wechat.send_msg(recipient, [], message)
            
            progress = int((i + 1) / total * 100)
            self.progress_updated.emit(progress)
            
            if i < total - 1:
                time.sleep(interval)
    
    def send_at_messages(self):
        """发送@消息"""
        recipients = self.kwargs.get('recipients', [])
        groups = self.kwargs.get('groups', [])
        message = self.kwargs.get('message', '')
        interval = self.kwargs.get('interval', 1)
        
        total = len(recipients) * len(groups)
        count = 0
        
        for group in groups:
            for recipient in recipients:
                if not self.running:
                    break
                
                self.status_updated.emit(f"正在 {group} 中@ {recipient}...")
                self.wechat.send_msg(group, [recipient], message)
                
                count += 1
                progress = int(count / total * 100)
                self.progress_updated.emit(progress)
                
                if count < total:
                    time.sleep(interval)
    
    def load_contacts(self):
        """加载联系人"""
        self.status_updated.emit("正在加载联系人...")
        contacts = self.wechat.get_all_contacts()
        self.finished_signal.emit(True, json.dumps(contacts, ensure_ascii=False))
    
    def load_groups(self):
        """加载群聊"""
        self.status_updated.emit("正在加载群聊...")
        groups = self.wechat.get_all_groups()
        self.finished_signal.emit(True, json.dumps(groups, ensure_ascii=False))
    
    def load_txt_content(self):
        """加载TXT内容"""
        file_path = self.kwargs.get('file_path', '')
        self.status_updated.emit("正在加载TXT文件...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.finished_signal.emit(True, content)
    
    def load_users_txt(self):
        """加载用户列表TXT"""
        file_path = self.kwargs.get('file_path', '')
        self.status_updated.emit("正在加载用户列表...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            users = [line.strip() for line in f if line.strip()]
        
        self.finished_signal.emit(True, json.dumps(users, ensure_ascii=False))


class WeChatGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.wechat = None
        self.http_server = None
        self.settings = QSettings('EasyChat', 'WeChatGUI')
        self.current_thread = None
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle('EasyChat - 微信自动化工具')
        self.setGeometry(100, 100, 1000, 700)
        
        # 设置应用图标（如果有的话）
        # self.setWindowIcon(QIcon('icon.png'))
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(main_widget)
        
        # 创建左侧控制面板
        self.create_left_panel(main_layout)
        
        # 创建右侧标签页
        self.create_right_tabs(main_layout)
        
        # 创建状态栏
        self.create_status_bar()
        
    def create_left_panel(self, main_layout):
        """创建左侧控制面板"""
        left_panel = QGroupBox("控制面板")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # 微信路径设置
        path_group = QGroupBox("微信路径设置")
        path_layout = QVBoxLayout(path_group)
        
        # 路径显示和选择
        path_h_layout = QHBoxLayout()
        self.wechat_path_label = QLabel("微信路径:")
        self.wechat_path_label.setStyleSheet("font-weight: bold;")
        path_h_layout.addWidget(self.wechat_path_label)
        
        self.wechat_path_display = QLineEdit()
        self.wechat_path_display.setReadOnly(True)
        self.wechat_path_display.setPlaceholderText("请选择微信程序路径")
        path_h_layout.addWidget(self.wechat_path_display)
        
        self.select_path_btn = QPushButton("选择路径")
        self.select_path_btn.clicked.connect(self.select_wechat_path)
        path_h_layout.addWidget(self.select_path_btn)
        
        path_layout.addLayout(path_h_layout)
        left_layout.addWidget(path_group)
        
        # 微信连接状态
        self.connection_status = QLabel("微信状态：未连接")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        left_layout.addWidget(self.connection_status)
        
        # 连接/断开按钮
        conn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("连接微信")
        self.connect_btn.clicked.connect(self.connect_wechat)
        self.disconnect_btn = QPushButton("断开连接")
        self.disconnect_btn.clicked.connect(self.disconnect_wechat)
        self.disconnect_btn.setEnabled(False)
        
        conn_layout.addWidget(self.connect_btn)
        conn_layout.addWidget(self.disconnect_btn)
        left_layout.addLayout(conn_layout)
        
        # 操作间隔设置
        interval_group = QGroupBox("操作间隔设置")
        interval_layout = QVBoxLayout(interval_group)
        
        interval_h_layout = QHBoxLayout()
        interval_h_layout.addWidget(QLabel("发送间隔(秒):"))
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.1, 10.0)
        self.interval_spin.setSingleStep(0.1)
        self.interval_spin.setValue(1.0)
        interval_h_layout.addWidget(self.interval_spin)
        interval_layout.addLayout(interval_h_layout)
        
        left_layout.addWidget(interval_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        left_layout.addWidget(self.status_label)
        
        # 停止按钮
        self.stop_btn = QPushButton("停止操作")
        self.stop_btn.clicked.connect(self.stop_operation)
        self.stop_btn.setEnabled(False)
        left_layout.addWidget(self.stop_btn)
        
        left_layout.addStretch(1)
        main_layout.addWidget(left_panel, 1)
        
    def create_right_tabs(self, main_layout):
        """创建右侧标签页"""
        self.tabs = QTabWidget()
        
        # 创建各个标签页
        self.create_send_tab()
        self.create_at_tab()
        self.create_batch_tab()
        self.create_manage_tab()
        self.create_http_tab()
        
        main_layout.addWidget(self.tabs, 2)
    
    def create_send_tab(self):
        """创建发送消息标签页"""
        send_widget = QWidget()
        layout = QVBoxLayout(send_widget)
        
        # 收件人输入
        recipient_group = QGroupBox("收件人")
        recipient_layout = QVBoxLayout(recipient_group)
        
        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("输入收件人姓名，多个用逗号分隔")
        recipient_layout.addWidget(self.recipient_input)
        
        # 常用联系人
        contacts_layout = QHBoxLayout()
        contacts_layout.addWidget(QLabel("常用联系人:"))
        self.contacts_combo = QComboBox()
        self.contacts_combo.setEditable(True)
        self.load_contacts_btn = QPushButton("加载联系人")
        self.load_contacts_btn.clicked.connect(self.load_contacts)
        contacts_layout.addWidget(self.contacts_combo)
        contacts_layout.addWidget(self.load_contacts_btn)
        recipient_layout.addLayout(contacts_layout)
        
        layout.addWidget(recipient_group)
        
        # 消息内容
        message_group = QGroupBox("消息内容")
        message_layout = QVBoxLayout(message_group)
        
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("输入要发送的消息内容...")
        self.message_input.setMaximumHeight(100)
        message_layout.addWidget(self.message_input)
        
        # 消息模板
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("消息模板:"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(["自定义", "问候消息", "通知消息", "节日祝福"])
        self.template_combo.currentTextChanged.connect(self.load_message_template)
        template_layout.addWidget(self.template_combo)
        message_layout.addLayout(template_layout)
        
        layout.addWidget(message_group)
        
        # 发送按钮
        send_btn = QPushButton("发送消息")
        send_btn.clicked.connect(self.send_message)
        layout.addWidget(send_btn)
        
        layout.addStretch(1)
        self.tabs.addTab(send_widget, "发送消息")
    
    def create_at_tab(self):
        """创建@消息标签页"""
        at_widget = QWidget()
        layout = QVBoxLayout(at_widget)
        
        # 群聊选择
        group_group = QGroupBox("选择群聊")
        group_layout = QVBoxLayout(group_group)
        
        self.group_list = QTextEdit()
        self.group_list.setMaximumHeight(80)
        self.group_list.setPlaceholderText("输入群聊名称，每行一个")
        group_layout.addWidget(self.group_list)
        
        # 常用群聊
        groups_layout = QHBoxLayout()
        groups_layout.addWidget(QLabel("常用群聊:"))
        self.groups_combo = QComboBox()
        self.groups_combo.setEditable(True)
        self.load_groups_btn = QPushButton("加载群聊")
        self.load_groups_btn.clicked.connect(self.load_groups)
        groups_layout.addWidget(self.groups_combo)
        groups_layout.addWidget(self.load_groups_btn)
        group_layout.addLayout(groups_layout)
        
        layout.addWidget(group_group)
        
        # @的人
        at_group = QGroupBox("@的人")
        at_layout = QVBoxLayout(at_group)
        
        self.at_list = QTextEdit()
        self.at_list.setMaximumHeight(80)
        self.at_list.setPlaceholderText("输入要@的人名，每行一个")
        at_layout.addWidget(self.at_list)
        
        layout.addWidget(at_group)
        
        # 消息内容
        at_message_group = QGroupBox("消息内容")
        at_message_layout = QVBoxLayout(at_message_group)
        
        self.at_message_input = QTextEdit()
        self.at_message_input.setPlaceholderText("输入要发送的消息内容...")
        self.at_message_input.setMaximumHeight(100)
        at_message_layout.addWidget(self.at_message_input)
        
        layout.addWidget(at_message_group)
        
        # 发送按钮
        at_send_btn = QPushButton("发送@消息")
        at_send_btn.clicked.connect(self.send_at_message)
        layout.addWidget(at_send_btn)
        
        layout.addStretch(1)
        self.tabs.addTab(at_widget, "@消息")
    
    def create_batch_tab(self):
        """创建批量发送标签页"""
        batch_widget = QWidget()
        layout = QVBoxLayout(batch_widget)
        
        # 文件选择
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout(file_group)
        
        # 用户列表文件
        users_layout = QHBoxLayout()
        self.users_file_path = QLineEdit()
        self.users_file_path.setPlaceholderText("选择用户列表文件（TXT格式，每行一个用户）")
        users_layout.addWidget(self.users_file_path)
        users_browse_btn = QPushButton("浏览")
        users_browse_btn.clicked.connect(lambda: self.browse_file("users"))
        users_layout.addWidget(users_browse_btn)
        file_layout.addLayout(users_layout)
        
        load_users_btn = QPushButton("加载用户列表")
        load_users_btn.clicked.connect(self.load_users_txt)
        file_layout.addWidget(load_users_btn)
        
        # 消息内容文件
        content_layout = QHBoxLayout()
        self.content_file_path = QLineEdit()
        self.content_file_path.setPlaceholderText("选择消息内容文件（TXT格式）")
        content_layout.addWidget(self.content_file_path)
        content_browse_btn = QPushButton("浏览")
        content_browse_btn.clicked.connect(lambda: self.browse_file("content"))
        content_layout.addWidget(content_browse_btn)
        file_layout.addLayout(content_layout)
        
        load_content_btn = QPushButton("加载消息内容")
        load_content_btn.clicked.connect(self.load_txt_content)
        file_layout.addWidget(load_content_btn)
        
        layout.addWidget(file_group)
        
        # 预览区域
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        
        # 用户列表预览
        users_preview_layout = QVBoxLayout()
        users_preview_layout.addWidget(QLabel("用户列表:"))
        self.users_preview = QTextEdit()
        self.users_preview.setMaximumHeight(100)
        users_preview_layout.addWidget(self.users_preview)
        preview_layout.addLayout(users_preview_layout)
        
        # 消息内容预览
        content_preview_layout = QVBoxLayout()
        content_preview_layout.addWidget(QLabel("消息内容:"))
        self.content_preview = QTextEdit()
        self.content_preview.setMaximumHeight(100)
        content_preview_layout.addWidget(self.content_preview)
        preview_layout.addLayout(content_preview_layout)
        
        layout.addWidget(preview_group)
        
        # 批量发送按钮
        batch_send_btn = QPushButton("开始批量发送")
        batch_send_btn.clicked.connect(self.batch_send)
        layout.addWidget(batch_send_btn)
        
        layout.addStretch(1)
        self.tabs.addTab(batch_widget, "批量发送")
    
    def create_manage_tab(self):
        """创建管理标签页"""
        manage_widget = QWidget()
        layout = QVBoxLayout(manage_widget)
        
        # 联系人管理
        contacts_group = QGroupBox("联系人管理")
        contacts_layout = QVBoxLayout(contacts_group)
        
        self.contacts_display = QTextEdit()
        self.contacts_display.setMaximumHeight(150)
        contacts_layout.addWidget(self.contacts_display)
        
        contacts_btn_layout = QHBoxLayout()
        refresh_contacts_btn = QPushButton("刷新联系人")
        refresh_contacts_btn.clicked.connect(self.refresh_contacts)
        export_contacts_btn = QPushButton("导出联系人")
        export_contacts_btn.clicked.connect(self.export_contacts)
        contacts_btn_layout.addWidget(refresh_contacts_btn)
        contacts_btn_layout.addWidget(export_contacts_btn)
        contacts_layout.addLayout(contacts_btn_layout)
        
        layout.addWidget(contacts_group)
        
        # 群聊管理
        groups_group = QGroupBox("群聊管理")
        groups_layout = QVBoxLayout(groups_group)
        
        self.groups_display = QTextEdit()
        self.groups_display.setMaximumHeight(150)
        groups_layout.addWidget(self.groups_display)
        
        groups_btn_layout = QHBoxLayout()
        refresh_groups_btn = QPushButton("刷新群聊")
        refresh_groups_btn.clicked.connect(self.refresh_groups)
        export_groups_btn = QPushButton("导出群聊")
        export_groups_btn.clicked.connect(self.export_groups)
        groups_btn_layout.addWidget(refresh_groups_btn)
        groups_btn_layout.addWidget(export_groups_btn)
        groups_layout.addLayout(groups_btn_layout)
        
        layout.addWidget(groups_group)
        
        layout.addStretch(1)
        self.tabs.addTab(manage_widget, "管理")
    
    def create_http_tab(self):
        """创建HTTP服务标签页"""
        http_widget = QWidget()
        layout = QVBoxLayout(http_widget)
        
        http_layout = self.init_http_service()
        layout.addLayout(http_layout)
        
        layout.addStretch(1)
        self.tabs.addTab(http_widget, "HTTP服务")
    
    def create_status_bar(self):
        """创建状态栏"""
        self.statusBar().showMessage("就绪")
    
    def init_http_service(self):
        """HTTP服务界面的初始化"""
        # 启动HTTP服务
        def start_http_server():
            if self.http_server.start():
                status_label.setStyleSheet("color:green")
                status_label.setText("HTTP服务状态：运行中 (端口: 6001)")
                start_btn.setEnabled(False)
                stop_btn.setEnabled(True)
                url_label.setText(f"服务地址: http://localhost:{self.http_server.port}")
                curl_label.setText("使用示例: curl -X POST http://localhost:6001/send -d '{\"recipient\":\"张三\",\"message\":\"你好\"}' -H \"Content-Type: application/json\"")
                curl_label.setWordWrap(True)
                QMessageBox.information(self, "HTTP服务已启动", f"HTTP服务已成功启动！\n\n服务地址: http://localhost:{self.http_server.port}\n\n可以使用API发送消息了！")
            else:
                QMessageBox.warning(self, "启动失败", "HTTP服务启动失败，请检查端口是否被占用！")

        # 停止HTTP服务
        def stop_http_server():
            if self.http_server.stop():
                status_label.setStyleSheet("color:red")
                status_label.setText("HTTP服务状态：已停止")
                start_btn.setEnabled(True)
                stop_btn.setEnabled(False)
                url_label.setText("服务地址: 未启动")
                curl_label.setText("")
                QMessageBox.information(self, "HTTP服务已停止", "HTTP服务已成功停止！")

        hbox = QHBoxLayout()

        # 左边的状态和控制区域
        left_vbox = QVBoxLayout()
        
        info = QLabel("HTTP服务控制")
        info.setStyleSheet("font-weight: bold;")
        
        status_label = QLabel("HTTP服务状态：未启动")
        status_label.setStyleSheet("color:red")
        
        url_label = QLabel("服务地址: 未启动")
        url_label.setStyleSheet("color:blue")
        
        curl_label = QLabel("")
        curl_label.setStyleSheet("color:gray; font-size: 10px;")
        
        button_hbox = QHBoxLayout()
        start_btn = QPushButton("启动HTTP服务")
        start_btn.clicked.connect(start_http_server)
        
        stop_btn = QPushButton("停止HTTP服务")
        stop_btn.clicked.connect(stop_http_server)
        stop_btn.setEnabled(False)
        
        button_hbox.addWidget(start_btn)
        button_hbox.addWidget(stop_btn)
        
        left_vbox.addWidget(info)
        left_vbox.addWidget(status_label)
        left_vbox.addWidget(url_label)
        left_vbox.addLayout(button_hbox)
        left_vbox.addWidget(curl_label)
        left_vbox.addStretch(1)

        # 右边的使用说明区域
        right_vbox = QVBoxLayout()
        
        usage_label = QLabel("HTTP API使用说明")
        usage_label.setStyleSheet("font-weight: bold;")
        
        usage_text = QLabel()
        usage_text.setText(
            "API接口:\n"
            "• GET / - 查看服务信息\n"
            "• GET /status - 查看服务状态\n"
            "• POST /send - 发送消息\n"
            "\n"
            "POST /send 参数:\n"
            "• recipient: 接收人姓名\n"
            "• message: 消息内容\n"
            "\n"
            "示例:\n"
            "curl -X POST http://localhost:6001/send \\\n"
            "  -d '{\"recipient\":\"张三\",\"message\":\"你好\"}' \\\n"
            "  -H \"Content-Type: application/json\""
        )
        usage_text.setStyleSheet("background-color: #f0f0f0; padding: 10px; font-family: monospace; font-size: 11px;")
        usage_text.setWordWrap(True)
        
        right_vbox.addWidget(usage_label)
        right_vbox.addWidget(usage_text)
        right_vbox.addStretch(1)

        hbox.addLayout(left_vbox)
        hbox.addLayout(right_vbox)
        
        return hbox
    
    def select_wechat_path(self):
        """选择微信程序路径"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择微信程序", 
            self.wechat_path_display.text() or "C:\\Program Files (x86)\\Tencent\\WeChat\\WeChat.exe",
            "Executable Files (*.exe)"
        )
        if file_path:
            self.wechat_path_display.setText(file_path)
            self.settings.setValue('wechat_path', file_path)
            self.statusBar().showMessage(f"已选择微信路径: {file_path}")
    
    def connect_wechat(self):
        """连接微信"""
        try:
            # 获取用户选择的微信路径
            wechat_path = self.wechat_path_display.text().strip()
            if not wechat_path:
                QMessageBox.warning(self, "路径错误", "请先选择微信程序路径")
                return
            
            if not os.path.exists(wechat_path):
                QMessageBox.critical(self, "路径错误", f"微信程序路径不存在：{wechat_path}")
                return
            
            # 创建WeChat实例
            self.wechat = WeChat(wechat_path)
            self.http_server = WeChatFlaskServer(self.wechat)
            
            self.wechat.open_wechat()
            self.connection_status.setText("微信状态：已连接")
            self.connection_status.setStyleSheet("color: green; font-weight: bold;")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.statusBar().showMessage("微信已连接")
        except Exception as e:
            QMessageBox.critical(self, "连接失败", f"连接微信失败：{str(e)}")
    
    def disconnect_wechat(self):
        """断开微信连接"""
        try:
            # 清理WeChat实例
            self.wechat = None
            self.http_server = None
            
            self.connection_status.setText("微信状态：未连接")
            self.connection_status.setStyleSheet("color: red; font-weight: bold;")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.statusBar().showMessage("微信已断开")
        except Exception as e:
            QMessageBox.warning(self, "断开失败", f"断开微信失败：{str(e)}")
    
    def load_contacts(self):
        """加载联系人"""
        self.start_operation("load_contacts", "正在加载联系人...")
    
    def load_groups(self):
        """加载群聊"""
        self.start_operation("load_groups", "正在加载群聊...")
    
    def send_message(self):
        """发送消息"""
        recipients_text = self.recipient_input.text().strip()
        if not recipients_text:
            QMessageBox.warning(self, "输入错误", "请输入收件人姓名")
            return
        
        message = self.message_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "输入错误", "请输入消息内容")
            return
        
        recipients = [r.strip() for r in recipients_text.split(",") if r.strip()]
        interval = self.interval_spin.value()
        
        self.start_operation("send_msg", "正在发送消息...", 
                           recipients=recipients, message=message, interval=interval)
    
    def send_at_message(self):
        """发送@消息"""
        groups_text = self.group_list.toPlainText().strip()
        if not groups_text:
            QMessageBox.warning(self, "输入错误", "请输入群聊名称")
            return
        
        at_text = self.at_list.toPlainText().strip()
        if not at_text:
            QMessageBox.warning(self, "输入错误", "请输入要@的人名")
            return
        
        message = self.at_message_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "输入错误", "请输入消息内容")
            return
        
        groups = [g.strip() for g in groups_text.splitlines() if g.strip()]
        recipients = [r.strip() for r in at_text.splitlines() if r.strip()]
        interval = self.interval_spin.value()
        
        self.start_operation("send_at_msg", "正在发送@消息...",
                           recipients=recipients, groups=groups, message=message, interval=interval)
    
    def batch_send(self):
        """批量发送"""
        users_text = self.users_preview.toPlainText().strip()
        content_text = self.content_preview.toPlainText().strip()
        
        if not users_text or not content_text:
            QMessageBox.warning(self, "输入错误", "请先加载用户列表和消息内容")
            return
        
        users = [u.strip() for u in users_text.splitlines() if u.strip()]
        interval = self.interval_spin.value()
        
        self.start_operation("send_msg", "正在批量发送消息...",
                           recipients=users, message=content_text, interval=interval)
    
    def browse_file(self, file_type):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "Text Files (*.txt)")
        if file_path:
            if file_type == "users":
                self.users_file_path.setText(file_path)
            elif file_type == "content":
                self.content_file_path.setText(file_path)
    
    def load_txt_content(self):
        """加载TXT内容"""
        file_path = self.content_file_path.text().strip()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "文件错误", "请选择有效的TXT文件")
            return
        
        self.start_operation("load_txt", "正在加载消息内容...", file_path=file_path)
    
    def load_users_txt(self):
        """加载用户列表TXT"""
        file_path = self.users_file_path.text().strip()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "文件错误", "请选择有效的TXT文件")
            return
        
        self.start_operation("load_users_txt", "正在加载用户列表...", file_path=file_path)
    
    def refresh_contacts(self):
        """刷新联系人"""
        self.start_operation("load_contacts", "正在刷新联系人...")
    
    def refresh_groups(self):
        """刷新群聊"""
        self.start_operation("load_groups", "正在刷新群聊...")
    
    def export_contacts(self):
        """导出联系人"""
        try:
            contacts = self.wechat.get_all_contacts()
            file_path, _ = QFileDialog.getSaveFileName(self, "保存联系人", "contacts.txt", "Text Files (*.txt)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for contact in contacts:
                        f.write(contact + '\n')
                QMessageBox.information(self, "导出成功", f"联系人已导出到 {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出联系人失败：{str(e)}")
    
    def export_groups(self):
        """导出群聊"""
        try:
            groups = self.wechat.get_all_groups()
            file_path, _ = QFileDialog.getSaveFileName(self, "保存群聊", "groups.txt", "Text Files (*.txt)")
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    for group in groups:
                        f.write(group + '\n')
                QMessageBox.information(self, "导出成功", f"群聊已导出到 {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出群聊失败：{str(e)}")
    
    def start_operation(self, operation_type, status_text, **kwargs):
        """开始操作"""
        if not self.wechat:
            QMessageBox.warning(self, "未连接", "请先连接微信")
            return
            
        if self.current_thread and self.current_thread.isRunning():
            QMessageBox.warning(self, "操作进行中", "请等待当前操作完成")
            return
        
        self.current_thread = WeChatAutomationThread(self.wechat, operation_type, **kwargs)
        self.current_thread.progress_updated.connect(self.update_progress)
        self.current_thread.status_updated.connect(self.update_status)
        self.current_thread.finished_signal.connect(self.operation_finished)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(status_text)
        self.stop_btn.setEnabled(True)
        
        self.current_thread.start()
    
    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)
    
    def update_status(self, text):
        """更新状态"""
        self.status_label.setText(text)
        self.statusBar().showMessage(text)
    
    def operation_finished(self, success, result):
        """操作完成"""
        self.progress_bar.setVisible(False)
        self.stop_btn.setEnabled(False)
        
        if success:
            if self.current_thread.operation_type == "load_contacts":
                contacts = json.loads(result)
                self.contacts_display.setText('\n'.join(contacts))
                self.contacts_combo.clear()
                self.contacts_combo.addItems(contacts)
                QMessageBox.information(self, "加载完成", f"已加载 {len(contacts)} 个联系人")
            
            elif self.current_thread.operation_type == "load_groups":
                groups = json.loads(result)
                self.groups_display.setText('\n'.join(groups))
                self.groups_combo.clear()
                self.groups_combo.addItems(groups)
                QMessageBox.information(self, "加载完成", f"已加载 {len(groups)} 个群聊")
            
            elif self.current_thread.operation_type == "load_txt":
                self.content_preview.setText(result)
                QMessageBox.information(self, "加载完成", "消息内容已加载")
            
            elif self.current_thread.operation_type == "load_users_txt":
                users = json.loads(result)
                self.users_preview.setText('\n'.join(users))
                QMessageBox.information(self, "加载完成", f"已加载 {len(users)} 个用户")
            
            else:
                QMessageBox.information(self, "操作完成", result)
        else:
            QMessageBox.critical(self, "操作失败", result)
        
        self.status_label.setText("就绪")
        self.statusBar().showMessage("就绪")
    
    def stop_operation(self):
        """停止操作"""
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.stop()
            self.current_thread.quit()
            self.current_thread.wait()
            self.progress_bar.setVisible(False)
            self.stop_btn.setEnabled(False)
            self.status_label.setText("已停止")
            self.statusBar().showMessage("操作已停止")
    
    def load_message_template(self, template_name):
        """加载消息模板"""
        templates = {
            "问候消息": "你好！这是一条问候消息。",
            "通知消息": "【通知】请查收重要通知。",
            "节日祝福": "祝你节日快乐，万事如意！",
            "自定义": ""
        }
        
        if template_name in templates:
            self.message_input.setText(templates[template_name])
    
    def load_settings(self):
        """加载设置"""
        self.interval_spin.setValue(float(self.settings.value("interval", 1.0)))
        
        # 加载微信路径
        saved_path = self.settings.value('wechat_path', '')
        if saved_path:
            self.wechat_path_display.setText(saved_path)
        
    def save_settings(self):
        """保存设置"""
        self.settings.setValue("interval", self.interval_spin.value())
    
    def closeEvent(self, event):
        """关闭事件"""
        self.save_settings()
        
        if self.current_thread and self.current_thread.isRunning():
            reply = QMessageBox.question(self, '确认退出', '有操作正在进行中，确定要退出吗？',
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.stop_operation()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 设置字体
    font = QFont()
    font.setFamily('Microsoft YaHei')
    font.setPointSize(9)
    app.setFont(font)
    
    window = WeChatGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()