import sys
import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
import ctypes
import json
import uuid
import re
import traceback
import platform
import base64
import webbrowser
import random
import string
import socket
import ssl
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import paramiko
import requests

# 管理员权限检查
def is_admin():
    """检查是否具有管理员权限"""
    try:
        return os.name == 'nt' and ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False
def run_as_admin():
    """请求管理员权限并重新启动程序"""
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + sys.argv[1:])
    
    try:
        # 使用Windows API请求管理员权限
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("权限错误", f"无法获取管理员权限: {str(e)}\n\n请右键点击程序，选择'以管理员身份运行'")
        sys.exit(1)
def install_libraries():
    """安装必需库的友好界面 - 按照要求修改"""
    # 创建安装窗口
    install_window = tk.Tk()
    install_window.title("安装依赖库")
    install_window.geometry("700x500")
    install_window.resizable(False, False)
    
    # 设置关闭事件处理
    install_window.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
    # 设置样式
    style = ttk.Style()
    style.configure('.', font=('微软雅黑', 10), background="#f2f2f2")
    style.configure('TLabel', font=('微软雅黑', 10), background="#f2f2f2")
    style.configure('TButton', font=('微软雅黑', 10), padding=5)
    # 添加说明标签
    label = ttk.Label(
        install_window, 
        text="正在安装必需的库，这是程序运行必需的组件...\n\n"
             "安装过程可能需要几分钟，请耐心等待。\n\n"
             "如果安装失败，请尝试以下手动解决方案：\n"
             "1. 以管理员身份打开命令提示符\n"
             "2. 输入命令: pip install paramiko requests\n"
             "3. 按回车键执行安装",
        padding=20,
        wraplength=650,
        justify="left"
    )
    label.pack(fill=tk.X)
    
    # 添加进度条
    progress = ttk.Progressbar(
        install_window, 
        orient="horizontal",
        length=600, 
        mode="indeterminate"
    )
    progress.pack(pady=10)
    progress.start()
    
    # 添加日志区域
    log_frame = ttk.Frame(install_window)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    log_label = ttk.Label(log_frame, text="安装日志:", anchor="w")
    log_label.pack(fill=tk.X)
    
    log_text = scrolledtext.ScrolledText(log_frame, height=12, font=("Consolas", 9))
    log_text.pack(fill=tk.BOTH, expand=True)
    log_text.config(state=tk.DISABLED)
    
    def log(message):
        """添加日志消息"""
        log_text.config(state=tk.NORMAL)
        log_text.insert(tk.END, message + "\n")
        log_text.see(tk.END)
        log_text.config(state=tk.DISABLED)
        install_window.update()
    
    # 添加完成按钮容器（初始隐藏）
    button_frame = ttk.Frame(install_window)
    
    # 安装线程
    def install_thread():
        try:
            log("准备安装必需的库...")
            
            # 检查pip是否可用
            pip_check = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if pip_check.returncode != 0:
                log("未找到pip，正在尝试安装pip...")
                ensurepip = subprocess.run(
                    [sys.executable, "-m", "ensurepip", "--default-pip"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                log(ensurepip.stdout)
                if ensurepip.returncode != 0:
                    log("pip安装失败，请手动安装pip")
                    raise Exception("pip安装失败")
            
            # 安装命令 - 安装paramiko和requests
            libraries = ["paramiko", "requests"]
            success = True
            
            for lib in libraries:
                command = [sys.executable, "-m", "pip", "install", lib]
                log(f"执行命令: {' '.join(command)}")
                
                # 运行安装命令
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # 实时读取输出
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        log(output.strip())
                
                # 检查安装结果
                return_code = process.poll()
                if return_code != 0:
                    log(f"安装{lib}失败，错误代码: {return_code}")
                    success = False
                else:
                    log(f"{lib}安装成功!")
            
            if success:
                log("\n所有库安装成功！")
                progress.stop()
                progress.config(mode="determinate")
                progress["value"] = 100
                
                # 显示完成按钮
                button_frame.pack(pady=15)
                
                # 添加完成按钮
                def finish_installation():
                    install_window.destroy()
                    messagebox.showinfo("安装完成", "所有必需的库已成功安装！请重新启动程序。")
                    sys.exit(0)
                
                finish_button = tk.Button(
                    button_frame, 
                    text="完成", 
                    command=finish_installation,
                    width=15,
                    height=2,
                    bg="#4CAF50",
                    fg="white",
                    font=("微软雅黑", 10, "bold")
                )
                finish_button.pack()
            else:
                log("\n部分库安装失败，请查看日志")
                
                # 提供手动安装选项
                def manual_install():
                    try:
                        if os.name == 'nt':
                            # 创建批处理文件
                            batch_content = "@echo off\n"
                            batch_content += "echo 正在安装必需的库...\n"
                            batch_content += "pip install paramiko requests\n"
                            batch_content += "echo 安装完成，按任意键退出...\n"
                            batch_content += "pause\n"
                            
                            batch_path = os.path.join(os.getcwd(), "install_dependencies.bat")
                            with open(batch_path, "w") as f:
                                f.write(batch_content)
                            
                            # 以管理员身份运行批处理
                            subprocess.run(
                                ['powershell', 'Start-Process', 'cmd', 
                                 f'/k "{batch_path}"', '-Verb', 'RunAs'],
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                    except Exception as e:
                        messagebox.showinfo("手动安装", "请以管理员身份打开命令提示符并执行:\npip install paramiko requests")
                
                manual_button = tk.Button(
                    button_frame, 
                    text="创建手动安装脚本", 
                    command=manual_install,
                    width=20,
                    height=2,
                    bg="#FF9800",
                    fg="white",
                    font=("微软雅黑", 10)
                )
                manual_button.pack(pady=10)
                
                # 添加重试按钮
                def retry_installation():
                    install_window.destroy()
                    install_libraries()
                
                retry_button = tk.Button(
                    button_frame, 
                    text="重试安装", 
                    command=retry_installation,
                    width=15,
                    height=2,
                    bg="#2196F3",
                    fg="white",
                    font=("微软雅黑", 10)
                )
                retry_button.pack(pady=5)
                
                # 显示按钮容器
                button_frame.pack(pady=15)
                
        except Exception as e:
            log(f"\n安装过程中出错: {str(e)}")
            
            # 显示错误按钮
            def show_error():
                messagebox.showerror("安装错误", f"安装过程中发生错误: {str(e)}\n\n请尝试手动安装或联系支持。")
                install_window.destroy()
                sys.exit(1)
            
            error_button = tk.Button(
                button_frame, 
                text="错误详情", 
                command=show_error,
                width=15,
                height=2,
                bg="#F44336",
                fg="white",
                font=("微软雅黑", 10)
            )
            error_button.pack(pady=15)
            button_frame.pack(pady=15)
    
    # 启动安装线程
    threading.Thread(target=install_thread, daemon=True).start()
    
    install_window.mainloop()
    
# ==================== V2Ray 部署工具主程序 - 优化UI版本 ====================
class V2RayDeployer:
    def __init__(self, master):
        self.master = master
        master.title("一键部署 V2Ray 工具")
        master.geometry("1100x654")
        master.resizable(False, False)
        master.configure(bg="#f2f2f2")
        
        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # 配置样式
        self.style.configure('.', font=('微软雅黑', 10), background="#f2f2f2")
        self.style.configure('TFrame', background="#f2f2f2")
        self.style.configure('Title.TLabel', font=('微软雅黑', 12, 'bold'), background="#f2f2f2")
        self.style.configure('Group.TLabelframe', font=('微软雅黑', 11, 'bold'), background="#ffffff", 
                             relief="solid", borderwidth=1)
        self.style.configure('Group.TLabelframe.Label', font=('微软雅黑', 11, 'bold'), background="#ffffff")
        self.style.configure('TButton', font=('微软雅黑', 10), padding=5)
        self.style.configure('Primary.TButton', font=('微软雅黑', 10, 'bold'), 
                             background="#4CAF50", foreground="white")
        self.style.configure('Secondary.TButton', font=('微软雅黑', 10), 
                             background="#607D8B", foreground="white")
        self.style.configure('Danger.TButton', font=('微软雅黑', 10, 'bold'), 
                             background="#F44336", foreground="white")
        self.style.configure('Info.TButton', font=('微软雅黑', 10), 
                             background="#2196F3", foreground="white")
        self.style.configure('TEntry', font=('微软雅黑', 10), padding=5)
        self.style.configure('TCombobox', font=('微软雅黑', 10), padding=5)
        self.style.configure('TLabel', font=('微软雅黑', 10), background="#f2f2f2")
        self.style.configure('TRadiobutton', font=('微软雅黑', 10), background="#f2f2f2")
        self.style.configure('TCheckbutton', font=('微软雅黑', 10), background="#f2f2f2")
        
        # 新增：子域名缓存
        self.prefix_cache = {}
        self.existing_subdomains_cache = {}
        
        # 设置主窗口关闭事件处理
        master.protocol("WM_DELETE_WINDOW", self.on_close)

        # 在初始化时添加内部端口变量
        self.internal_v2ray_port = random.randint(10000, 65000)
        self.server_port = 443  # 默认用户访问端口

        # IPv6状态
        self.ipv6_status = tk.BooleanVar(value=False)

        # 设置相关变量
        self.cf_proxy_enabled = tk.BooleanVar(value=True)  # 默认启用代理
        self.deploy_mode = tk.StringVar(value="single")    # 部署模式：single/batch
        self.task_queue = Queue()                          # 任务队列
        self.running_tasks = 0                             # 正在运行的任务数
        self.max_workers = 5                               # 最大并发任务数
        
        # 子域名验证相关变量
        self.subdomain_warning_var = tk.StringVar()
        self.subdomain_warning_label = None

        # 子域名变量
        self.cf_subdomain = tk.StringVar(value="v2ray")
        
        # 添加对子域名变量的跟踪
        self.cf_subdomain.trace_add("write", self.sync_cf_subdomain)

        # 批量部署前缀
        self.batch_prefix = None
        
        # 创建配置目录
        self.app_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_dir = os.path.join(self.app_dir, "config")
        self.resources_dir = os.path.join(self.app_dir, "resources")
        
        # 确保目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.resources_dir, exist_ok=True)
        
        # 配置管理变量
        self.config_files = []
        self.current_config_name = tk.StringVar()
        
        # ============== 任务列表区域 ==============
        frame_tasks = tk.LabelFrame(master, text="任务列表", padx=5, pady=5)
        frame_tasks.place(x=10, y=10, width=700, height=400)
        
        # 任务列表 - 表格（Treeview实现）
        columns = ("序号", "IP", "端口", "用户名", "密码", "子域名", "连接状态", "任务状态")
        self.task_tree = ttk.Treeview(
            frame_tasks, 
            columns=columns, 
            show="headings", 
            height=16,
            selectmode="extended"
        )
        
        # 初始化 task_configs
        self.task_configs = {}

        # 绑定双击事件
        self.task_tree.bind("<Double-1>", self.on_task_double_click)

        # 配置列
        col_widths = [40, 120, 60, 80, 120, 60, 80, 100]
        for idx, col in enumerate(columns):
            self.task_tree.heading(col, text=col)
            self.task_tree.column(col, width=col_widths[idx], anchor='center')
        
        # 配置标签颜色
        self.task_tree.tag_configure("conn_ok", foreground="green")
        self.task_tree.tag_configure("conn_fail", foreground="red")
        self.task_tree.tag_configure("pending", foreground="black")   # 等待部署
        self.task_tree.tag_configure("deploying", foreground="blue")  # 正在部署
        self.task_tree.tag_configure("success", foreground="green")   # 部署完成
        self.task_tree.tag_configure("failed", foreground="red")      # 部署失败
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(frame_tasks, orient="vertical", command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.task_tree.pack(fill="both", expand=True)
        
        # 添加示例数据
        self.add_sample_tasks()
        
        # ============== 日志区域 ==============
        frame_log = tk.LabelFrame(master, text="操作日志", padx=5, pady=5)
        frame_log.place(x=10, y=420, width=700, height=200)
        
        self.log_text = scrolledtext.ScrolledText(
            frame_log, 
            wrap=tk.WORD,
            font=("Consolas", 10),
            padx=10,
            pady=10
        )
        self.log_text.pack(fill="both", expand=True)
        self.log_text.config(state=tk.DISABLED)

        # 设置日志文本标签
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("info", foreground="black")
        self.log_text.tag_config("timestamp", foreground="#666666")
        
        # 添加初始日志消息
        self.log_message("[14:24:34] 已加载默认配置")
        
        # ============== 右侧配置区域 ==============
        frame_right = tk.Frame(master, relief="solid")
        frame_right.place(x=720, y=10, width=370, height=400)
        
        # 创建标签页
        self.notebook = ttk.Notebook(frame_right)
        self.notebook.pack(fill="both", expand=True)
        
        # Cloudflare 配置标签页
        cf_frame = ttk.Frame(self.notebook)
        self.notebook.add(cf_frame, text="Cloudflare 配置")
        self.setup_cf_frame(cf_frame)
        
        # 服务器配置标签页
        server_frame = ttk.Frame(self.notebook)
        self.notebook.add(server_frame, text="服务器配置")
        self.setup_server_frame(server_frame)
        
        # V2Ray 配置标签页
        v2ray_frame = ttk.Frame(self.notebook)
        self.notebook.add(v2ray_frame, text="V2Ray 配置")
        self.setup_v2ray_frame(v2ray_frame)
        
        # 设置标签页
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="设置")
        self.setup_settings_frame(settings_frame)
        
        # ============== 部署模式选择 ==============
        frame_deploymode = tk.LabelFrame(master, text="部署模式", padx=5, pady=5)
        frame_deploymode.place(x=720, y=420, width=370, height=55)
        
        # 部署模式选择
        self.deploy_mode = tk.StringVar(value="single")
        ttk.Radiobutton(
            frame_deploymode, 
            text="单服务器部署", 
            variable=self.deploy_mode, 
            value="single",
            command=self.update_deploy_ui
        ).pack(side=tk.LEFT, padx=8)
        
        ttk.Radiobutton(
            frame_deploymode, 
            text="批量部署", 
            variable=self.deploy_mode, 
            value="batch",
            command=self.update_deploy_ui
        ).pack(side=tk.LEFT, padx=20)
        
        # ============== 操作按钮区域 ==============
        frame_buttons = tk.Frame(master)
        frame_buttons.place(x=720, y=480, width=370, height=55)
        
        self.deploy_button = tk.Button(
            frame_buttons, 
            text="开始部署", 
            command=self.start_deployment,
            bg="#24b24b", 
            fg="white", 
            font=("微软雅黑", 13, "bold"),
            width=18,
            height=2
        )
        self.deploy_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(
            frame_buttons, 
            text="停止部署", 
            command=self.stop_deployment,
            bg="#cccccc", 
            fg="#555", 
            font=("微软雅黑", 13, "bold"),
            width=18,
            height=2,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # ============== 配置管理区域 ==============
        frame_cfg = tk.LabelFrame(master, text="配置管理", padx=5, pady=5)
        frame_cfg.place(x=720, y=540, width=370, height=80)
        
        # 配置选择框
        self.config_combo = ttk.Combobox(
            frame_cfg,
            textvariable=self.current_config_name,
            width=10,
            state="readonly"
        )
        self.config_combo.place(x=8, y=8)
        self.config_combo.bind("<<ComboboxSelected>>", self.load_selected_config)
        
        # 配置操作按钮
        refresh_btn = ttk.Button(
            frame_cfg,
            text="刷新",
            command=self.refresh_config_list,
            width=5,
            style="Secondary.TButton"
        )
        refresh_btn.place(x=110, y=6)
        
        load_btn = ttk.Button(
            frame_cfg,
            text="加载",
            command=self.load_selected_config,
            width=5,
            style="Info.TButton"
        )
        load_btn.place(x=170, y=6)
        
        save_btn = ttk.Button(
            frame_cfg,
            text="保存",
            command=self.save_config,
            width=5,
            style="Primary.TButton"
        )
        save_btn.place(x=230, y=6)
        
        # 修改为清空按钮
        clear_btn = ttk.Button(
            frame_cfg,
            text="清空",
            command=self.clear_configuration,
            width=5,
            style="Danger.TButton"
        )
        clear_btn.place(x=290, y=6)
        
        # ============== 状态栏 ==============
        # 状态栏框架
        status_frame = ttk.Frame(master, padding=(0, 2))
        status_frame.place(x=0, y=628, relwidth=1.0, height=26)
        
        # 状态文本标签（左侧）
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var,
            anchor=tk.W,
            padding=(10, 0)
        )
        status_label.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        
        # 添加更新提示标签（在状态文本和进度条之间）
        self.update_hint_label = ttk.Label(
            status_frame,
            text="",
            foreground="blue",
            font=("微软雅黑", 9),
            padding=(0, 0, 10, 0)  # 右边距10像素
        )
        self.update_hint_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # 进度条（右侧）- 初始隐藏
        self.progress_bar = ttk.Progressbar(
            status_frame, 
            orient="horizontal", 
            mode="indeterminate",
            length=150
        )
        
        # ============== 系统配置 ==============

        # 部署线程控制变量
        self.deployment_thread = None
        self.stop_deployment_flag = False
        
        # 初始化UI
        self.update_deploy_ui()
        
        # 初始刷新配置列表
        self.refresh_config_list()
        
        # 跟踪服务器配置变化
        self.server_ip.trace_add("write", self.sync_single_server_to_list)
        self.ssh_port.trace_add("write", self.sync_single_server_to_list)
        self.ssh_username.trace_add("write", self.sync_single_server_to_list)
        self.auth_method.trace_add("write", self.sync_single_server_to_list)
        self.ssh_password.trace_add("write", self.sync_single_server_to_list)
        self.ssh_key_path.trace_add("write", self.sync_single_server_to_list)
        self.ssh_key_pass.trace_add("write", self.sync_single_server_to_list)
    
    def update_deploy_ui(self):
        """更新部署模式UI"""
        if self.deploy_mode.get() == "single":
            self.single_server_frame.pack(fill="both", expand=True)
            self.batch_server_frame.pack_forget()
        else:
            self.single_server_frame.pack_forget()
            self.batch_server_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    def setup_settings_frame(self, frame):
        """设置标签页 - 全部使用pack布局"""
        frame.configure(style='TFrame')
        padx, pady = 6, 6
        
        # 日志级别
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill="x", padx=padx, pady=pady)
        
        ttk.Label(log_frame, text="日志级别:").pack(side="left", padx=padx)
        self.log_level = tk.StringVar(value="info")
        
        log_levels = [
            ("调试", "debug"),
            ("信息", "info"),
            ("警告", "warning"),
            ("错误", "error"),
            ("无", "none")
        ]
        
        for text, value in log_levels:
            ttk.Radiobutton(
                log_frame, 
                text=text, 
                variable=self.log_level, 
                value=value,
            ).pack(side="left", padx=5)
        
        # 并发任务数
        workers_frame = ttk.Frame(frame)
        workers_frame.pack(fill="x", padx=padx, pady=pady)
        
        ttk.Label(workers_frame, text="最大并发任务数:").pack(side="left", padx=padx)
        self.max_workers_var = tk.IntVar(value=5)
        spinbox = ttk.Spinbox(
            workers_frame,
            from_=1,
            to=10,
            textvariable=self.max_workers_var,
            width=5,
        )
        spinbox.pack(side="left", padx=5)
        
        # 其他设置
        other_frame = ttk.Frame(frame)
        other_frame.pack(fill="x", padx=padx, pady=pady)
        
        # 启用BBR
        self.enable_bbr = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            other_frame,
            text="启用BBR加速",
            variable=self.enable_bbr
        ).pack(side="left", padx=5)
        
        # 启用IPV6
        self.ipv6_status = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            other_frame,
            text="启用IPV6",
            variable=self.ipv6_status
        ).pack(side="left", padx=5)
        
        # 自定义配置
        custom_frame = ttk.Frame(frame)
        custom_frame.pack(fill="both", expand=True, padx=padx, pady=pady)
        
        # 自定义配置标签和按钮放在同一行
        custom_label_frame = ttk.Frame(custom_frame)
        custom_label_frame.pack(fill="x", pady=(0,5))
        
        ttk.Label(custom_label_frame, text="自定义V2Ray配置:").pack(side="left", padx=padx)
        
        # 添加"加载默认配置"按钮
        ttk.Button(
            custom_label_frame, 
            text="加载默认配置", 
            command=self.load_default_config,
            style="Secondary.TButton",
            width=15
        ).pack(side="right", padx=5)
        
        self.custom_config_text = scrolledtext.ScrolledText(
            custom_frame, 
            height=5,  # 高度缩小一半
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.custom_config_text.pack(
            fill="both",
            expand=True,
            padx=padx,
            pady=(0,5),  # 调整垂直间距
            ipady=5
        )
    
    def clear_configuration(self):
        """清空所有配置和任务列表"""
        # 清空任务列表
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        # 清空配置存储
        self.task_configs = {}

        # 清空配置信息
        self.cf_api_token.set("")
        self.cf_domain.set("")
        self.cf_subdomain.set("v2ray")
        self.cf_proxy_enabled.set(True)
        
        self.server_ip.set("")
        self.ssh_port.set(22)
        self.ssh_username.set("root")
        self.auth_method.set("password")
        self.ssh_password.set("")
        self.ssh_key_path.set("")
        self.ssh_key_pass.set("")
        
        self.v2ray_protocol.set("vmess_tcp_tls")
        self.v2ray_port.set(443)
        self.v2ray_uuid.set(str(uuid.uuid4()))
        self.ws_path_var.set("/v2ray")
        self.trojan_password_var.set("")
        
        self.custom_config_text.delete(1.0, tk.END)
        
        # 清空批量服务器文本框
        if hasattr(self, 'batch_server_text'):
            self.batch_server_text.delete(1.0, tk.END)
        
        # 清空子域名警告
        self.subdomain_warning_var.set("")
        
        self.log_message("配置已清空")
    
    def add_sample_tasks(self):
        """添加示例任务到任务列表"""
        sample_tasks = [
            ("1", "192.168.1.100", "22", "root", "******", "", "连接正常", "等待部署"),
            ("2", "192.168.1.101", "22", "admin", "******", "", "连接正常", "等待部署"),
            ("3", "192.168.1.102", "22", "ubuntu", "密钥认证", "", "连接失败", "等待部署"),
            ("4", "192.168.1.103", "22", "centos", "密钥认证", "", "连接正常", "等待部署")
        ]
        
        for task in sample_tasks:
            self.task_tree.insert("", "end", values=task)
    
    def center_window(self, window):
        """将窗口居中显示，参照主窗口"""
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        # 获取主窗口位置
        x = self.master.winfo_x()
        y = self.master.winfo_y()
        main_width = self.master.winfo_width()
        main_height = self.master.winfo_height()
        # 计算居中位置
        x = x + (main_width - width) // 2
        y = y + (main_height - height) // 2
        window.geometry(f'+{x}+{y}')
    
    def refresh_config_list(self):
        """刷新配置文件列表"""
        self.config_files = []
        if os.path.exists(self.config_dir):
            for file in os.listdir(self.config_dir):
                if file.startswith("config_") and file.endswith(".json"):
                    # 提取配置名称（去掉前缀和后缀）
                    config_name = file[7:-5]
                    self.config_files.append((config_name, os.path.join(self.config_dir, file)))
        
        # 更新组合框
        self.config_combo["values"] = [name for name, _ in self.config_files]
        
        # 如果当前有域名配置，尝试自动选择
        current_domain = self.cf_domain.get().strip()
        if current_domain:
            # 提取域名主名称（去掉后缀）
            domain_parts = current_domain.split('.')
            if len(domain_parts) > 1:
                main_domain = domain_parts[0]  # 获取主名称，如 example.com -> example
                if main_domain in [name for name, _ in self.config_files]:
                    self.current_config_name.set(main_domain)
    
    def get_config_filename(self):
        """获取当前配置对应的文件名"""
        domain = self.cf_domain.get().strip()
        if not domain:
            return None
        
        # 提取域名主名称（去掉后缀）
        domain_parts = domain.split('.')
        if len(domain_parts) < 2:
            return None
        
        main_domain = domain_parts[0]  # 获取主名称，如 example.com -> example
        return os.path.join(self.config_dir, f"config_{main_domain}.json")
    
    def auto_load_config(self):
        """自动加载当前域名的配置文件（如果存在）"""
        config_path = self.get_config_filename()
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                
                # 设置Cloudflare配置
                self.cf_api_token.set(config.get("cf_api_token", ""))
                self.cf_domain.set(config.get("cf_domain", ""))
                self.cf_subdomain.set(config.get("cf_subdomain", "v2ray"))
                self.cf_proxy_enabled.set(config.get("cf_proxy", True))
                
                # 设置服务器配置
                self.server_ip.set(config.get("server_ip", ""))
                self.ssh_port.set(config.get("ssh_port", 22))
                self.ssh_username.set(config.get("ssh_username", "root"))
                self.auth_method.set(config.get("auth_method", "password"))
                self.ssh_password.set(config.get("ssh_password", ""))
                self.ssh_key_path.set(config.get("ssh_key_path", ""))
                self.ssh_key_pass.set(config.get("ssh_key_pass", ""))
                
                # 设置V2Ray配置
                self.v2ray_protocol.set(config.get("protocol", "vmess_tcp_tls"))
                self.v2ray_port.set(config.get("v2ray_port", 443))
                self.v2ray_uuid.set(config.get("uuid", str(uuid.uuid4())))
                self.ws_path_var.set(config.get("ws_path", "/v2ray"))
                self.trojan_password_var.set(config.get("trojan_password", ""))
                self.log_level.set(config.get("log_level", "info"))
                
                # 设置自定义配置
                custom_config = config.get("custom_config", "")
                self.custom_config_text.delete(1.0, tk.END)
                self.custom_config_text.insert(tk.END, custom_config)
                
                self.log_message(f"已自动加载配置: {os.path.basename(config_path)}")
                
                # 更新配置列表选择
                domain_parts = self.cf_domain.get().split('.')
                if len(domain_parts) > 1:
                    main_domain = domain_parts[0]
                    self.current_config_name.set(main_domain)
            except Exception as e:
                self.log_message(f"自动加载配置失败: {str(e)}", "error")
    
    def save_config(self):
        """保存配置到文件（静默保存到当前域名对应的文件）"""
        config_path = self.get_config_filename()
        if not config_path:
            self.log_message("无法保存配置: 未设置域名", "error")
            return
        
        try:
            # 收集配置信息
            config = self.collect_config()
            
            # 移除敏感信息
            sensitive_keys = ["cf_subdomain"]
            for key in sensitive_keys:
                if key in config:
                    config[key] = ""
            
            # 保存到文件
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            
            # 更新配置列表
            self.refresh_config_list()
            
            self.log_message(f"配置已保存到: {os.path.basename(config_path)}")
        except Exception as e:
            self.log_message(f"保存配置失败: {str(e)}", "error")
    
    def load_selected_config(self, event=None):
        """加载选定的配置"""
        config_name = self.current_config_name.get()
        if not config_name:
            return
        
        # 查找对应的配置文件路径
        config_path = None
        for name, path in self.config_files:
            if name == config_name:
                config_path = path
                break
        
        if not config_path or not os.path.exists(config_path):
            self.log_message(f"配置 {config_name} 不存在", "error")
            return
        
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            
            # 设置Cloudflare配置
            self.cf_api_token.set(config.get("cf_api_token", ""))
            self.cf_domain.set(config.get("cf_domain", ""))
            self.cf_subdomain.set(config.get("cf_subdomain", "us"))
            self.cf_proxy_enabled.set(config.get("cf_proxy", True))
            
            # 设置服务器配置
            self.server_ip.set(config.get("server_ip", ""))
            self.ssh_port.set(config.get("ssh_port", 22))
            self.ssh_username.set(config.get("ssh_username", "root"))
            self.auth_method.set(config.get("auth_method", "password"))
            self.ssh_password.set(config.get("ssh_password", ""))
            self.ssh_key_path.set(config.get("ssh_key_path", ""))
            self.ssh_key_pass.set(config.get("ssh_key_pass", ""))
            
            # 设置V2Ray配置
            self.v2ray_protocol.set(config.get("protocol", "vmess_tcp_tls"))
            self.v2ray_port.set(config.get("v2ray_port", 443))
            self.v2ray_uuid.set(config.get("uuid", str(uuid.uuid4())))
            self.ws_path_var.set(config.get("ws_path", "/v2ray"))
            self.trojan_password_var.set(config.get("trojan_password", ""))
            self.log_level.set(config.get("log_level", "info"))
            
            # 设置自定义配置
            custom_config = config.get("custom_config", "")
            self.custom_config_text.delete(1.0, tk.END)
            self.custom_config_text.insert(tk.END, custom_config)
            
            self.log_message(f"已加载配置: {config_name}")
        except Exception as e:
            self.log_message(f"加载配置失败: {str(e)}", "error")
    
    def setup_cf_frame(self, frame):
        """设置Cloudflare配置标签页 - 全部使用pack布局"""
        frame.configure(style='TFrame')
        padx, pady = 10, 8
        
        # 标题
        title_label = ttk.Label(frame, text="Cloudflare 配置", style="Title.TLabel")
        title_label.pack(pady=(5, 1), anchor="center")
        
        # 主容器 - 使用pack布局
        container = ttk.Frame(frame)
        container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # API 令牌
        api_frame = ttk.Frame(container)
        api_frame.pack(fill="x", pady=5)
        
        ttk.Label(api_frame, text="Cloudflare API令牌:").pack(side="left", padx=padx)
        self.cf_api_token = tk.StringVar()
        api_entry = ttk.Entry(api_frame, textvariable=self.cf_api_token, width=40)
        api_entry.pack(side="left", fill="x", expand=True, padx=padx)
        
        # 域名
        domain_frame = ttk.Frame(container)
        domain_frame.pack(fill="x", pady=5)
        
        ttk.Label(domain_frame, text="主域名:").pack(side="left", padx=padx)
        self.cf_domain = tk.StringVar()
        domain_entry = ttk.Entry(domain_frame, textvariable=self.cf_domain, width=40)
        domain_entry.pack(side="left", fill="x", expand=True, padx=padx)
        
        # 子域名
        subdomain_frame = ttk.Frame(container)
        subdomain_frame.pack(fill="x", pady=5)
        
        ttk.Label(subdomain_frame, text="子域名:").pack(side="left", padx=padx)
        self.cf_subdomain = tk.StringVar(value="v2ray")
        subdomain_entry = ttk.Entry(subdomain_frame, textvariable=self.cf_subdomain, width=20)
        subdomain_entry.pack(side="left", fill="x", expand=True, padx=padx)
        
        # 添加验证按钮
        validate_btn = ttk.Button(
            subdomain_frame,
            text="验证",
            command=self.validate_subdomain,
            width=5,
            style="Secondary.TButton"
        )
        validate_btn.pack(side="left", padx=10)
        
        # 添加警告标签 - 移动到子域名输入框下方
        warning_frame = ttk.Frame(container)
        warning_frame.pack(fill="x", pady=(0, 5))  # 放在子域名输入框下方
        
        self.subdomain_warning_var = tk.StringVar()
        self.subdomain_warning_label = ttk.Label(
            warning_frame, 
            textvariable=self.subdomain_warning_var,
            foreground="red",
            font=("微软雅黑", 9),
            anchor="w"  # 左对齐
        )
        self.subdomain_warning_label.pack(side="left", padx=padx)
        
        # 绑定事件
        subdomain_entry.bind("<KeyRelease>", lambda e: self.sync_single_server_to_list())
        subdomain_entry.bind("<FocusOut>", lambda e: self.sync_single_server_to_list())
        
        # 代理状态
        proxy_frame = ttk.Frame(container)
        proxy_frame.pack(fill="x", pady=5)
        
        ttk.Label(proxy_frame, text="Cloudflare代理:").pack(side="left", padx=padx)
        self.cf_proxy_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            proxy_frame, 
            text="启用代理(橙色云)", 
            variable=self.cf_proxy_enabled,
        ).pack(side="left", padx=10)
        
        # 测试按钮
        test_frame = ttk.Frame(container)
        test_frame.pack(fill="x", pady=10)
        
        test_button = ttk.Button(
            test_frame, 
            text="测试Cloudflare连接", 
            command=self.test_cf_connection,
            style="Secondary.TButton"
        )
        test_button.pack(side="left", padx=padx)
        
        # 帮助链接
        help_frame = ttk.Frame(container)
        help_frame.pack(fill="x", pady=5)
        
        help_link = tk.Label(
            help_frame, 
            text="如何获取Cloudflare API令牌?", 
            foreground="blue", 
            cursor="hand2",
            font=("微软雅黑", 9)
        )
        help_link.pack(side="left", padx=padx)
        help_link.bind("<Button-1>", lambda e: webbrowser.open("https://dash.cloudflare.com/profile/api-tokens"))
    
    def validate_subdomain(self):
        # 在后台线程执行验证
        threading.Thread(target=self._validate_subdomain_thread, daemon=True).start()

    def _validate_subdomain_thread(self):
        """后台线程执行子域名验证 - 优化逻辑"""
        subdomain = self.cf_subdomain.get().strip()
        domain = self.cf_domain.get().strip()
        
        if not subdomain or not domain:
            self.master.after(0, lambda: self.subdomain_warning_var.set("请先填写主域名和子域名"))
            self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="red"))
            return
        
        full_domain = f"{subdomain}.{domain}"
        prefix = subdomain[0].lower()  # 获取子域名的第一个字符作为前缀
        
        # 在UI线程更新状态
        self.master.after(0, lambda: self.subdomain_warning_var.set("正在验证子域名..."))
        self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="blue"))
        
        try:
            # 第一步：检查缓存
            cache_key = f"{domain}_{prefix}"
            cached_subdomains = None
            cache_time = 0
            
            if cache_key in self.existing_subdomains_cache:
                cached_subdomains, cache_time = self.existing_subdomains_cache[cache_key]
                # 检查缓存是否过期（5分钟内有效）
                if time.time() - cache_time < 300:
                    self.log_message(f"使用缓存的前缀 '{prefix}' 子域名列表")
            
            # 第二步：快速DNS解析检查（优先显示）
            dns_result = self.quick_dns_check(full_domain)
            
            if dns_result is False:
                # DNS解析存在记录 - 立即显示
                self.master.after(0, lambda: self.subdomain_warning_var.set("⚠ DNS解析存在记录，可能已被占用"))
                self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="orange"))
            else:
                # 没有DNS记录 - 显示临时状态
                self.master.after(0, lambda: self.subdomain_warning_var.set("✓ DNS未解析，可能可用..."))
                self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="green"))
            
            # 第三步：Cloudflare API检查（后台更新缓存）
            if cached_subdomains is None or time.time() - cache_time >= 300:
                # 后台获取该前缀的所有子域名
                threading.Thread(
                    target=self.fetch_and_cache_subdomains,
                    args=(domain, prefix),
                    daemon=True
                ).start()
            
            # 第四步：使用缓存或API结果进行最终验证
            if cached_subdomains is not None:
                if subdomain.lower() in cached_subdomains:
                    # 确保总是传递有效的 existing_subdomains
                    suggestion = self.generate_unique_subdomain(prefix, cached_subdomains)
                    self.master.after(0, lambda: self.subdomain_warning_var.set(f"⚠ 子域名已被占用 (缓存确认)! 推荐: {suggestion}"))
                    self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="red"))
                else:
                    self.master.after(0, lambda: self.subdomain_warning_var.set("✓ 子域名可用 (缓存确认)"))
                    self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="green"))
            else:
                # 没有缓存时使用API检查单个子域名
                api_result = self.is_subdomain_available(full_domain)
                
                if api_result is False:
                    # Cloudflare API确认已被占用
                    # 使用空集合作为现有域名
                    suggestion = self.generate_unique_subdomain(prefix, set())
                    self.master.after(0, lambda: self.subdomain_warning_var.set(f"⚠ 子域名已被占用! 推荐: {suggestion}"))
                    self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="red"))
                elif api_result is True:
                    # Cloudflare API确认可用
                    self.master.after(0, lambda: self.subdomain_warning_var.set("✓ 子域名可用（API确认）"))
                    self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="green"))
                else:
                    # 无法确定状态
                    self.master.after(0, lambda: self.subdomain_warning_var.set("ℹ 子域名状态未知，请手动验证"))
                    self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="blue"))
        
        except Exception as e:
            error_msg = f"验证失败: {str(e)}"
            self.log_message(error_msg, "error")
            self.master.after(0, lambda: self.subdomain_warning_var.set(error_msg))
            self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="red"))

    def fetch_and_cache_subdomains(self, domain, prefix):
        """获取并缓存指定前缀的子域名"""
        try:
            self.log_message(f"获取 '{prefix}' 前缀的子域名列表...")
            subdomains = self.get_subdomains_by_prefix(domain, prefix)
            
            # 更新缓存
            cache_key = f"{domain}_{prefix}"
            self.existing_subdomains_cache[cache_key] = (subdomains, time.time())
            self.log_message(f"已缓存 {len(subdomains)} 个 '{prefix}' 前缀的子域名")
            
            # 检查当前子域名是否在新获取的列表中
            current_subdomain = self.cf_subdomain.get().strip().lower()
            if current_subdomain in subdomains:
                suggestion = self.generate_unique_subdomain(prefix, subdomains)
                self.master.after(0, lambda: self.subdomain_warning_var.set(f"⚠ 子域名已被占用 (最新确认)! 推荐: {suggestion}"))
                self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="red"))
        
        except Exception as e:
            self.log_message(f"获取子域名列表失败: {str(e)}", "error")
            # 尝试使用空集合并生成建议
            try:
                suggestion = self.generate_unique_subdomain(prefix, set())
                self.master.after(0, lambda: self.subdomain_warning_var.set(f"⚠ 验证失败! 推荐使用: {suggestion}"))
                self.master.after(0, lambda: self.subdomain_warning_label.configure(foreground="red"))
            except Exception as e2:
                self.log_message(f"生成推荐子域名失败: {str(e2)}", "error")

    def quick_dns_check(self, full_domain):
        """快速DNS检查 - 优先返回结果"""
        try:
            # 尝试解析A记录
            start_time = time.time()
            resolved_ips = socket.getaddrinfo(full_domain, 443, type=socket.SOCK_STREAM)
            elapsed = time.time() - start_time
            
            if resolved_ips:
                ip = resolved_ips[0][4][0]
                self.log_message(f"DNS解析成功: {full_domain} -> {ip} ({elapsed:.3f}s)", "info")
                return False
            return True
        except socket.gaierror:
            # 无法解析表示可能可用
            return True
        except Exception as e:
            self.log_message(f"DNS解析出错: {str(e)}", "warning")
            return None  # 不确定状态

    def check_subdomain_available(self, full_domain):
        """检查子域名是否可用，并返回推荐列表"""
        api_token = self.cf_api_token.get().strip()
        if not api_token:
            return True, []  # 没有API令牌时跳过检查
            
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # 获取区域ID
            url = "https://api.cloudflare.com/client/v4/zones"
            params = {"name": full_domain.split('.', 1)[1]}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            if not (response.status_code == 200 and data.get("success", False) and data["result"]):
                return True, []  # 无法获取区域信息时跳过检查
                
            zone_id = data["result"][0]["id"]
            
            # 检查DNS记录
            url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
            params = {"name": full_domain, "type": "A"}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            if data["success"] and data["result"]:
                # 子域名已存在，生成推荐
                suggestions = self.generate_subdomain_suggestions(full_domain)
                return False, suggestions
            else:
                return True, []
        except Exception as e:
            self.log_message(f"子域名验证失败: {str(e)}", "error")
            return True, []
    
    def generate_subdomain(self, prefix, existing_subdomains):
        """生成符合格式的可用子域名"""
        # 尝试从001到999生成
        for num in range(1, 1000):
            candidate = f"{prefix}{num:03d}"  # 格式: 字母+3位数字
            
            # 检查是否已存在
            if candidate not in existing_subdomains:
                return candidate
        
        # 如果所有数字组合都被占用，尝试添加随机后缀
        for _ in range(20):
            rand_suffix = ''.join(random.choices(string.ascii_lowercase, k=2))
            candidate = f"{prefix}{random.randint(1, 999):03d}_{rand_suffix}"
            
            if candidate not in existing_subdomains:
                return candidate
        
        # 作为最后手段，生成完全随机的
        rand_prefix = random.choice('abcdefghjkmnpqrstuvwxyz')
        rand_num = random.randint(1, 999)
        return f"{rand_prefix}{rand_num:03d}"
    
    def is_subdomain_available(self, full_domain):
        """检查子域名是否可用"""
        # 首先检查本地缓存
        if "." in full_domain:
            # 修复：使用full_domain而不是未定义的name
            domain = full_domain.split(".", 1)[1]
            subdomain = full_domain.split(".", 1)[0]
            
            if domain in self.existing_subdomains_cache:
                return subdomain not in self.existing_subdomains_cache[domain]
        
        # 没有缓存时调用API
        api_token = self.cf_api_token.get().strip()
        if not api_token:
            return True  # 没有API令牌时假设可用
            
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # 获取区域ID
            url = "https://api.cloudflare.com/client/v4/zones"
            if "." not in full_domain:
                return True
                
            domain = full_domain.split(".", 1)[1]
            params = {"name": domain}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            if not (response.status_code == 200 and data.get("success", False) and data["result"]):
                return True  # 无法获取区域信息时假设可用
                
            zone_id = data["result"][0]["id"]
            
            # 检查DNS记录
            url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
            params = {"name": full_domain, "type": "A"}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            return not (data["success"] and data["result"] and len(data["result"]) > 0)
            
        except Exception as e:
            self.log_message(f"子域名验证失败: {str(e)}", "error")
            return True  # 验证失败时假设可用
        
    def collect_base_config(self):
        """收集基本配置（不包含服务器特定信息）"""
        # 获取子域名值
        subdomain = self.cf_subdomain.get().strip()
        subdomain = subdomain if subdomain else "v2ray"
        
        config = {
            # Cloudflare配置
            "cf_api_token": self.cf_api_token.get().strip(),
            "cf_domain": self.cf_domain.get().strip(),
            "cf_subdomain": subdomain,
            "cf_proxy": self.cf_proxy_enabled.get(),
            
            # V2Ray配置
            "protocol": self.v2ray_protocol.get(),
            "v2ray_port": self.v2ray_port.get(),
            "uuid": self.v2ray_uuid.get(),
            "ws_path": self.ws_path_var.get(),
            "trojan_password": self.trojan_password_var.get(),
            "log_level": self.log_level.get(),
            "custom_config": self.custom_config_text.get("1.0", tk.END).strip(),
            
            # 其他设置
            "enable_bbr": self.enable_bbr.get(),
            "enable_ipv6": self.ipv6_status.get()
        }
        
        # 生成完整域名
        config["full_domain"] = f"{config['cf_subdomain']}.{config['cf_domain']}"
        
        return config
    def setup_server_frame(self, frame):
        """设置服务器配置标签页 - 全部使用pack布局"""
        frame.configure(style='TFrame')
        padx, pady = 10, 8
        
        # 标题
        title_label = ttk.Label(frame, text="服务器配置", style="Title.TLabel")
        title_label.pack(pady=(5, 1), anchor="center")
        
        # 单服务器配置框架
        self.single_server_frame = ttk.Frame(frame)
        self.single_server_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 服务器地址
        ip_frame = ttk.Frame(self.single_server_frame)
        ip_frame.pack(fill="x", pady=5)
        
        ttk.Label(ip_frame, text="服务器IP地址:").pack(side="left", padx=padx)
        self.server_ip = tk.StringVar()
        ip_entry = ttk.Entry(ip_frame, textvariable=self.server_ip, width=30)
        ip_entry.pack(side="left", padx=padx)
        
        # SSH端口
        port_frame = ttk.Frame(self.single_server_frame)
        port_frame.pack(fill="x", pady=5)
        
        ttk.Label(port_frame, text="SSH端口:").pack(side="left", padx=padx)
        self.ssh_port = tk.IntVar(value=22)
        port_entry = ttk.Entry(port_frame, textvariable=self.ssh_port, width=10)
        port_entry.pack(side="left", padx=padx)
        
        # 用户名
        user_frame = ttk.Frame(self.single_server_frame)
        user_frame.pack(fill="x", pady=5)
        
        ttk.Label(user_frame, text="用户名:").pack(side="left", padx=padx)
        self.ssh_username = tk.StringVar(value="root")
        user_entry = ttk.Entry(user_frame, textvariable=self.ssh_username, width=20)
        user_entry.pack(side="left", padx=padx)
        
        # 认证方式
        auth_frame = ttk.Frame(self.single_server_frame)
        auth_frame.pack(fill="x", pady=5)
        
        ttk.Label(auth_frame, text="认证方式:").pack(side="left", padx=padx)
        self.auth_method = tk.StringVar(value="password")
        
        ttk.Radiobutton(
            auth_frame, 
            text="密码", 
            variable=self.auth_method, 
            value="password",
        ).pack(side="left", padx=10)
        
        ttk.Radiobutton(
            auth_frame, 
            text="密钥文件", 
            variable=self.auth_method, 
            value="key",
        ).pack(side="left", padx=10)
        
        # 密码输入框
        self.password_frame = ttk.Frame(self.single_server_frame)
        self.password_frame.pack(fill="x", pady=5)
        
        ttk.Label(self.password_frame, text="密码:").pack(side="left", padx=padx)
        self.ssh_password = tk.StringVar()
        password_entry = ttk.Entry(self.password_frame, textvariable=self.ssh_password, width=20, show="*")
        password_entry.pack(side="left", padx=padx)
        
        # 密钥文件输入框
        self.key_frame = ttk.Frame(self.single_server_frame)
        
        ttk.Label(self.key_frame, text="密钥文件路径:").pack(side="left", padx=padx)
        self.ssh_key_path = tk.StringVar()
        key_entry = ttk.Entry(self.key_frame, textvariable=self.ssh_key_path, width=20)
        key_entry.pack(side="left", padx=padx)
        ttk.Button(
            self.key_frame, 
            text="浏览", 
            command=self.browse_key_file,
            width=8,
            style="Secondary.TButton"
        ).pack(side="left", padx=padx)
        
        # 密钥密码（可选）
        self.key_pass_frame = ttk.Frame(self.single_server_frame)
        
        ttk.Label(self.key_pass_frame, text="密钥密码 (可选):").pack(side="left", padx=padx)
        self.ssh_key_pass = tk.StringVar()
        key_pass_entry = ttk.Entry(self.key_pass_frame, textvariable=self.ssh_key_pass, width=15, show="*")
        key_pass_entry.pack(side="left", padx=padx)
        
        # 测试按钮
        test_frame = ttk.Frame(self.single_server_frame)
        test_frame.pack(fill="x", pady=10)
        
        test_button = ttk.Button(
            test_frame, 
            text="测试服务器连接", 
            command=self.test_server_connection,
            style="Secondary.TButton"
        )
        test_button.pack(side="left", padx=padx)
        # 新增：卸载V2Ray按钮（初始隐藏）
        self.uninstall_button = ttk.Button(
            test_frame,
            text="卸载V2Ray",
            command=self.uninstall_v2ray,
            style="Danger.TButton",
            state=tk.DISABLED  # 初始禁用
        )
        self.uninstall_button.pack(side="left", padx=5)
        
        # 批量服务器配置框架
        self.batch_server_frame = ttk.Frame(frame)
        
        # 批量服务器输入框
        batch_label = ttk.Label(self.batch_server_frame, text="批量服务器配置 (每行一个服务器):")
        batch_label.pack(anchor="w", padx=padx, pady=pady)
        
        self.batch_server_text = scrolledtext.ScrolledText(
            self.batch_server_frame,
            height=10,  # 默认15行
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.batch_server_text.pack(
            fill="both",
            expand=True,
            padx=padx,
            pady=pady,
            ipady=5  # 增加内部垂直间距使视觉更舒适
        )
        
        # 导入按钮
        import_frame = ttk.Frame(self.batch_server_frame)
        import_frame.pack(fill="x", pady=5)
        
        import_button = ttk.Button(
            import_frame,
            text="导入服务器列表",
            command=self.import_batch_servers,
            style="Primary.TButton"
        )
        import_button.pack(side="left", padx=padx)
        
        # 示例按钮
        example_button = ttk.Button(
            import_frame,
            text="查看示例格式",
            command=self.show_batch_example,
            style="Secondary.TButton"
        )
        example_button.pack(side="left", padx=padx)
        
        # 根据认证方式显示相应控件
        self.auth_method.trace_add("write", self.update_auth_ui)
        self.update_auth_ui()
    
    def import_batch_servers(self):
        """导入批量服务器列表到任务列表并验证子域名"""
        batch_text = self.batch_server_text.get("1.0", tk.END).strip()
        if not batch_text:
            messagebox.showwarning("警告", "请输入服务器列表")
            return
        
        servers = self.parse_batch_servers(batch_text)
        if not servers:
            messagebox.showwarning("警告", "未解析到有效的服务器配置")
            return
        
        # 清空任务列表
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        # 添加服务器到任务列表，初始状态为"子域名验证中"
        for i, server in enumerate(servers, 1):
            # 密码或密钥显示
            if server["auth_method"] == "password":
                auth_display = server["ssh_password"]
            else:
                auth_display = server["ssh_key_path"]
            
            # 注意列顺序:
            # 0:序号, 1:IP, 2:端口, 3:用户名, 4:密码, 5:子域名, 6:连接状态, 7:任务状态
            values = (
                str(i),             # 序号
                server["server_ip"], # IP
                str(server["ssh_port"]), # 端口
                server["ssh_username"], # 用户名
                auth_display,       # 密码
                "验证中...",        # 子域名
                "测试中...",        # 连接状态
                "子域名验证中"      # 任务状态
            )
            self.task_tree.insert("", "end", values=values, tags=("pending",))
        
        self.log_message(f"已导入 {len(servers)} 台服务器，开始验证子域名...")
        
        # 启动子域名验证线程
        threading.Thread(
            target=self.validate_batch_subdomains,
            args=(servers,),
            daemon=True
        ).start()

    def validate_batch_subdomains(self, servers):
        """验证批量服务器的子域名"""
        # 创建进度窗口
        progress_window = tk.Toplevel(self.master)
        progress_window.title("子域名验证")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)
        progress_window.grab_set()  # 模态对话框
        self.center_window(progress_window)
        
        # 添加进度标签
        progress_label = ttk.Label(
            progress_window, 
            text="正在验证子域名...",
            font=("微软雅黑", 11)
        )
        progress_label.pack(pady=15)
        
        # 添加进度条
        progress_bar = ttk.Progressbar(
            progress_window, 
            orient="horizontal",
            length=350, 
            mode="indeterminate"
        )
        progress_bar.pack(pady=5)
        progress_bar.start()
        
        # 添加状态标签
        status_var = tk.StringVar(value="正在生成子域名前缀...")
        status_label = ttk.Label(
            progress_window, 
            textvariable=status_var,
            font=("微软雅黑", 9)
        )
        status_label.pack(pady=5)
        
        # 更新UI
        self.master.update()
        
        try:
            # 生成批量部署前缀（单个字母）
            batch_prefix = self.generate_batch_prefix()
            status_var.set(f"使用前缀: {batch_prefix}*")
            self.master.update()
            
            # 获取当前域名
            domain = self.cf_domain.get().strip()
            if not domain:
                raise ValueError("请先设置主域名")
            
            # 获取该前缀的所有子域名
            status_var.set(f"查询 {batch_prefix}* 子域名...")
            self.master.update()
            
            subdomains = self.get_subdomains_by_prefix(domain, batch_prefix)
            
            # 生成可用子域名列表
            status_var.set(f"生成可用子域名...")
            self.master.update()
            
            available_subdomains = self.generate_available_subdomains(
                batch_prefix, 
                subdomains, 
                len(servers)
            )
            
            # 更新任务列表
            status_var.set("更新服务器配置...")
            self.master.update()
            
            for idx, item in enumerate(self.task_tree.get_children()):
                if idx < len(available_subdomains):
                    values = list(self.task_tree.item(item, "values"))
                    # 确保有足够列
                    if len(values) < 8:
                        values.append("")  # 添加子域名列
                    # 更新子域名
                    values[5] = available_subdomains[idx]  # 第五列是子域名
                    # 更新任务状态
                    values[7] = "等待部署"
                    # 更新Treeview项
                    self.task_tree.item(item, values=values)
            
            # 启动连接测试
            for idx, item in enumerate(self.task_tree.get_children()):
                values = self.task_tree.item(item, "values")
                server_ip = values[1]
                
                # 查找对应的服务器配置
                server_config = None
                for server in servers:
                    if server["server_ip"] == server_ip:
                        server_config = server
                        break
                
                if server_config:
                    # 保存子域名
                    server_config["cf_subdomain"] = values[5]
                    # 启动连接测试
                    threading.Thread(
                        target=self.test_server_connection_in_list,
                        args=(item, server_config),
                        daemon=True
                    ).start()
            
            self.log_message(f"为 {len(servers)} 台服务器分配子域名: {', '.join(available_subdomains)}")
            
            # 关闭进度窗口
            progress_window.destroy()
            
        except Exception as e:
            # 出错时关闭进度窗口并显示错误
            progress_window.destroy()
            self.log_message(f"子域名验证失败: {str(e)}", "error")
            messagebox.showerror("错误", f"子域名验证失败: {str(e)}", parent=self.master)

    def test_server_connection_in_list(self, item, server_config):
        """测试任务列表中指定服务器的连接状态"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 设置超时为10秒
            paramiko.util.log_to_file("paramiko.log")  # 可选：记录SSH日志
            
            if server_config["auth_method"] == "password":
                ssh.connect(
                    server_config["server_ip"],
                    port=server_config["ssh_port"],
                    username=server_config["ssh_username"],
                    password=server_config["ssh_password"],
                    timeout=10,
                    banner_timeout=20
                )
            else:
                key_path = server_config["ssh_key_path"]
                key_pass = server_config.get("ssh_key_pass") or None
                key = paramiko.RSAKey.from_private_key_file(key_path, password=key_pass)
                ssh.connect(
                    server_config["server_ip"],
                    port=server_config["ssh_port"],
                    username=server_config["ssh_username"],
                    pkey=key,
                    timeout=10,
                    banner_timeout=20
                )
            
            # 连接成功
            ssh.close()
            # 使用after方法在主线程中更新UI
            self.master.after(0, lambda: self.update_task_item(
                item, 
                connection_status="连接正常"
            ))
        except Exception as e:
            error_msg = str(e)
            # 使用after方法在主线程中更新UI
            self.master.after(0, lambda: self.update_task_item(
                item, 
                connection_status=f"连接失败: {error_msg[:30]}"
            ))
    
    def update_task_item(self, item, subdomain=None, connection_status=None, task_status=None):
        """更新任务列表中的项 - 修正列顺序"""
        # 首先检查项是否仍然存在
        if item not in self.task_tree.get_children():
            return  # 如果项已被删除，直接返回
        
        values = list(self.task_tree.item(item, "values"))
        
        # 确保有足够列
        if len(values) < 8:
            # 插入缺少的列
            # 注意：列顺序：序号、IP、端口、用户名、密码、子域名、连接状态、任务状态
            # 初始可能只有7列，我们插入一列
            values.insert(5, "")  # 插入子域名列（第6列）
        
        # 更新子域名
        if subdomain is not None:
            values[5] = subdomain  # 第六列是子域名
        
        # 更新连接状态
        if connection_status is not None:
            values[6] = connection_status  # 第七列是连接状态
        
        # 更新任务状态
        if task_status is not None:
            values[7] = task_status  # 第八列是任务状态
        
        tags = list(self.task_tree.item(item, "tags"))
        
        # 清除旧的状态标签
        for state in ["conn_ok", "conn_fail", "pending", "deploying", "success", "failed"]:
            if state in tags:
                tags.remove(state)
        
        # 添加新的状态标签
        if connection_status == "连接正常":
            tags.append("conn_ok")
        elif connection_status and "连接失败" in connection_status:
            tags.append("conn_fail")
        
        if task_status == "等待部署":
            tags.append("pending")
        elif task_status == "正在部署":
            tags.append("deploying")
        elif task_status == "部署完成":
            tags.append("success")
        elif task_status == "部署失败":
            tags.append("failed")
        
        # 更新Treeview项
        self.task_tree.item(item, values=values, tags=tags)
        
        # 强制刷新UI
        self.task_tree.update()
      
        # 添加新的状态标签
        if connection_status == "连接正常":
            tags.append("conn_ok")
        elif connection_status and "连接失败" in connection_status:
            tags.append("conn_fail")
      
        if task_status == "等待部署":
            tags.append("pending")
        elif task_status == "正在部署":
            tags.append("deploying")
        elif task_status == "部署完成":
            tags.append("success")
        elif task_status == "部署失败":
            tags.append("failed")
      
        # 更新Treeview项
        self.task_tree.item(item, values=values, tags=tags)
      
        # 强制刷新UI
        self.task_tree.update()
    
    def sync_cf_subdomain(self, *args):
        """当子域名变化时同步到任务列表"""
        if self.deploy_mode.get() == "single":
            self.sync_single_server_to_list()

    def sync_single_server_to_list(self, *args):
        """将单服务器配置同步到任务列表 - 使用用户输入的子域名"""
        if self.deploy_mode.get() != "single":
            return
        
        # 清空任务列表
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        # 获取配置
        ip = self.server_ip.get().strip()
        port = self.ssh_port.get()
        username = self.ssh_username.get().strip()
        auth_method = self.auth_method.get()
        
        if not ip:
            return
        
        # 密码或密钥显示
        if auth_method == "password":
            auth_display = self.ssh_password.get()
        else:
            auth_display = self.ssh_key_path.get()
        
        # 获取用户输入的子域名（新增）
        subdomain = self.cf_subdomain.get().strip()
        
        # 注意列顺序:
        # 0:序号, 1:IP, 2:端口, 3:用户名, 4:密码, 5:子域名, 6:连接状态, 7:任务状态
        values = (
            "1",           # 序号
            ip,            # IP
            str(port),     # 端口
            username,      # 用户名
            auth_display,  # 密码
            subdomain,     # 子域名（新增）
            "测试中...",   # 连接状态
            "等待部署"     # 任务状态
        )
        item = self.task_tree.insert("", "end", values=values, tags=("pending",))
        
        # 启动线程测试连接状态
        server_config = {
            "server_ip": ip,
            "ssh_port": port,
            "ssh_username": username,
            "auth_method": auth_method,
            "cf_subdomain": subdomain  # 保存子域名
        }
        if auth_method == "password":
            server_config["ssh_password"] = self.ssh_password.get()
        else:
            server_config["ssh_key_path"] = self.ssh_key_path.get()
            server_config["ssh_key_pass"] = self.ssh_key_pass.get()
        
        threading.Thread(
            target=self.test_server_connection_in_list, 
            args=(item, server_config),
            daemon=True
        ).start()
    
    def setup_v2ray_frame(self, frame):
        """设置V2Ray配置标签页 - 使用预设方案（带滚动条）"""
        frame.configure(style='TFrame')
        
        # 创建滚动条框架
        scroll_frame = ttk.Frame(frame)
        scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(scroll_frame)
        scrollbar.pack(side="right", fill="y")
        
        # 创建Canvas
        canvas = tk.Canvas(
            scroll_frame, 
            yscrollcommand=scrollbar.set,
            highlightthickness=0,
            bd=0
        )
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=canvas.yview)
        
        # 创建内部框架（实际内容容器）
        container = ttk.Frame(canvas)
        container_id = canvas.create_window((0, 0), window=container, anchor="nw")
        
        # 配置Canvas滚动
        def configure_canvas(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas_width = event.width
            canvas.itemconfig(container_id, width=canvas_width)
        
        container.bind("<Configure>", configure_canvas)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(container_id, width=e.width))
        
        # 绑定鼠标滚轮事件
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # ============== 以下是原来的配置内容，稍作修改 ==============
        padx, pady = 5, 2  # 统一行间距
        
        # 协议方案选择
        protocol_frame = ttk.Frame(container)
        protocol_frame.pack(fill="x", padx=padx, pady=pady)
        
        ttk.Label(protocol_frame, text="协议方案:").pack(side="left", padx=padx)
        self.v2ray_protocol = tk.StringVar(value="vmess_tcp_tls")
        
        protocols = [
            ("VMess+TCP+TLS", "vmess_tcp_tls"),
            ("VMess+WS+TLS", "vmess_ws_tls"),
            ("VLESS+TCP+TLS", "vless_tcp_tls"),
            ("VLESS+WS+TLS", "vless_ws_tls"),
            ("VLESS+TCP+xtls-rprx-direct", "vless_tcp_xtls"),
            ("Trojan+WS+TLS", "trojan_ws_tls"),
            ("Trojan-Go+WS+TLS", "trojango_ws_tls"),
            ("VLESS+Reality+uTLS+Vision", "vless_reality_utls")
        ]
        
        protocol_combo = ttk.Combobox(
            protocol_frame,
            textvariable=self.v2ray_protocol,
            values=[p[1] for p in protocols],
            state="readonly",
            width=25
        )
        protocol_combo.pack(side="left", padx=5)
        
        # 端口设置
        port_frame = ttk.Frame(container)
        port_frame.pack(fill="x", padx=padx, pady=pady)
        
        self.port_label = ttk.Label(port_frame, text="访问端口:")
        self.port_label.pack(side="left", padx=padx)
        
        self.v2ray_port = tk.IntVar(value=443)
        port_entry = ttk.Entry(port_frame, textvariable=self.v2ray_port, width=5)
        port_entry.pack(side="left", padx=padx)

        self.port_info = ttk.Label(
            port_frame, 
            text="(用户访问的端口，通常为443)",
            foreground="#666",
            font=("微软雅黑", 9)
        )
        self.port_info.pack(side="left", padx=5)

        # UUID设置
        uuid_frame = ttk.Frame(container)
        uuid_frame.pack(fill="x", padx=padx, pady=pady)
        
        ttk.Label(uuid_frame, text="UUID:").pack(side="left", padx=padx)
        self.v2ray_uuid = tk.StringVar(value=str(uuid.uuid4()))
        uuid_entry = ttk.Entry(uuid_frame, textvariable=self.v2ray_uuid, width=25)
        uuid_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        gen_button = ttk.Button(
            uuid_frame, 
            text="生成", 
            command=lambda: self.v2ray_uuid.set(str(uuid.uuid4())),
            width=8,
            style="Secondary.TButton"
        )
        gen_button.pack(side="left", padx=5)
        
        # WebSocket路径
        self.ws_frame = ttk.Frame(container)
        ttk.Label(self.ws_frame, text="WebSocket路径:").pack(side="left", padx=10)
        self.ws_path_var = tk.StringVar(value="/v2ray")
        self.ws_path_entry = ttk.Entry(self.ws_frame, textvariable=self.ws_path_var, width=30)
        self.ws_path_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Trojan密码
        self.trojan_frame = ttk.Frame(container)
        ttk.Label(self.trojan_frame, text="Trojan密码:").pack(side="left", padx=10)
        self.trojan_password_var = tk.StringVar(value="")
        self.trojan_password_entry = ttk.Entry(self.trojan_frame, textvariable=self.trojan_password_var, width=30)
        self.trojan_password_entry.pack(side="left", padx=5, fill="x", expand=True)

        # 初始隐藏可选字段
        self.ws_frame.pack_forget()
        self.trojan_frame.pack_forget()

        # Socks5配置
        socks5_frame = ttk.Frame(container)
        socks5_frame.pack(fill="x", padx=padx, pady=pady)
        
        self.enable_socks5 = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            socks5_frame,
            text="启用 Socks5 协议 (与主协议共存)",
            variable=self.enable_socks5,
            command=self.toggle_socks5_fields
        ).pack(anchor="w", padx=5)
        
        # Socks5 配置容器
        self.socks5_container = ttk.Frame(container)
        
        # Socks5 端口
        socks5_port_frame = ttk.Frame(self.socks5_container)
        socks5_port_frame.pack(fill="x", padx=5, pady=pady)
        ttk.Label(socks5_port_frame, text="Socks5 端口:").pack(side="left", padx=5)
        self.socks5_port = tk.IntVar(value=1080)
        self.socks5_port_entry = ttk.Entry(socks5_port_frame, textvariable=self.socks5_port, width=8)
        self.socks5_port_entry.pack(side="left", padx=5)
        
        self.port_conflict_label = ttk.Label(
            socks5_port_frame, 
            text="", 
            foreground="red",
            font=("微软雅黑", 9)
        )
        self.port_conflict_label.pack(side="left", padx=5)
        
        # 认证方式
        socks5_auth_frame = ttk.Frame(self.socks5_container)
        socks5_auth_frame.pack(fill="x", padx=5, pady=pady)
        ttk.Label(socks5_auth_frame, text="认证方式:").pack(side="left", padx=5)
        self.socks5_auth = tk.StringVar(value="none")
        ttk.Radiobutton(
            socks5_auth_frame, 
            text="无认证", 
            variable=self.socks5_auth, 
            value="none"
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            socks5_auth_frame, 
            text="用户名/密码", 
            variable=self.socks5_auth, 
            value="password"
        ).pack(side="left", padx=5)
        
        # 用户名和密码
        self.socks5_auth_fields = ttk.Frame(self.socks5_container)
        ttk.Label(self.socks5_auth_fields, text="用户名:").pack(side="left", padx=5)
        self.socks5_username = tk.StringVar(value="")
        ttk.Entry(self.socks5_auth_fields, textvariable=self.socks5_username, width=15).pack(side="left", padx=5)
        ttk.Label(self.socks5_auth_fields, text="密码:").pack(side="left", padx=5)
        self.socks5_password = tk.StringVar(value="")
        ttk.Entry(self.socks5_auth_fields, textvariable=self.socks5_password, width=15, show="*").pack(side="left", padx=5)
        
        # 初始隐藏Socks5配置
        self.socks5_container.pack_forget()
        self.socks5_auth_fields.pack_forget()

        # 伪装网站配置
        proxy_frame = ttk.Frame(container)
        proxy_frame.pack(fill="x", padx=padx, pady=pady)
        
        # 伪装网站和允许爬虫放在同一行
        left_col = ttk.Frame(proxy_frame)
        left_col.pack(side="left", fill="x", expand=True)
        
        ttk.Label(left_col, text="伪装网站:").pack(side="left", padx=padx)
        self.proxy_url_var = tk.StringVar()
        proxy_combo = ttk.Combobox(
            left_col,
            textvariable=self.proxy_url_var,
            values=[
                "无",
                "静态网站(默认)",
                "小说站(随机)",
                "美女站(http://www.kimiss.com)",
                "高清壁纸站(https://www.wallpaperstock.net)",
                "自定义"
            ],
            state="readonly",
            width=20
        )
        proxy_combo.pack(side="left", padx=5, fill="x", expand=True)
        proxy_combo.set("无")
        
        # 允许爬虫放在右侧
        right_col = ttk.Frame(proxy_frame)
        right_col.pack(side="right", padx=(10, 0))
        
        self.allow_spider_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            right_col,
            text="允许爬虫",
            variable=self.allow_spider_var
        ).pack(side="left", padx=5)
        
        # 自定义伪装网站输入框
        self.custom_proxy_frame = ttk.Frame(container)
        ttk.Label(self.custom_proxy_frame, text="自定义URL:").pack(side="left", padx=10)
        self.custom_proxy_entry = ttk.Entry(self.custom_proxy_frame, width=30)
        self.custom_proxy_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.custom_proxy_frame.pack_forget()
        
        # ============== 事件绑定 ==============
        # 根据协议方案更新UI
        self.update_protocol_ui()
        self.v2ray_protocol.trace_add("write", self.update_protocol_ui)
        
        # 绑定认证方式变化
        self.socks5_auth.trace_add("write", self.toggle_socks5_auth_fields)
        self.socks5_port.trace_add("write", self.check_port_conflict)
        self.socks5_port_entry.bind("<FocusOut>", self.check_port_conflict)
        self.v2ray_port.trace_add("write", self.check_port_conflict)
        
        # 绑定伪装网站变化
        proxy_combo.bind("<<ComboboxSelected>>", self.on_proxy_change)
        
        # 绑定端口信息更新
        self.v2ray_protocol.trace_add("write", self.update_port_info)
        
        # 初始更新Canvas尺寸
        container.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def toggle_socks5_fields(self):
        """切换 Socks5 配置字段的可见性"""
        if self.enable_socks5.get():
            self.socks5_container.pack(fill="x", padx=5, pady=2)
            self.toggle_socks5_auth_fields()
        else:
            self.socks5_container.pack_forget()
    
    def toggle_socks5_auth_fields(self, *args):
        """切换 Socks5 认证字段的可见性"""
        if self.socks5_auth.get() == "password":
            self.socks5_auth_fields.pack(fill="x", padx=5, pady=2)
        else:
            self.socks5_auth_fields.pack_forget()

    def check_port_conflict(self, *args):
        """检查端口是否冲突"""
        # 只有在启用Socks5时才检查
        if not self.enable_socks5.get():
            self.port_conflict_label.config(text="")
            return
            
        try:
            # 获取当前输入的端口值
            socks5_port = self.socks5_port.get()
            v2ray_port = self.v2ray_port.get()
            
            # 检查端口范围是否有效 (1-65535)
            if not (1 <= socks5_port <= 65535):
                self.port_conflict_label.config(text="⚠ 端口必须在1-65535范围内")
                return
                
            # 常见冲突端口（系统端口和应用常用端口）
            common_ports = {
                21, 22, 23, 25, 53, 80, 110, 123, 143, 161, 194, 443, 445, 514, 
                587, 993, 995, 1025, 1080, 1194, 1433, 1521, 3000, 3306, 3389, 
                5432, 5900, 5901, 6379, 8080, 8443, 9050, 27017, 50000
            }
            
            # 构建所有需要检查冲突的端口集合
            conflicting_ports = {v2ray_port}  # 主V2Ray端口
            conflicting_ports.update(common_ports)  # 常见系统和应用端口
            
            # 如果启用了其他协议，也加入检查（示例：WebSocket端口）
            # 这里可以根据实际支持的协议扩展
            
            # 检查冲突
            if socks5_port in conflicting_ports:
                if socks5_port == v2ray_port:
                    self.port_conflict_label.config(text="⚠ 与主协议端口冲突", foreground="red")
                elif socks5_port in common_ports:
                    self.port_conflict_label.config(text="⚠ 常用端口，可能被占用", foreground="orange")
                else:
                    self.port_conflict_label.config(text="⚠ 端口可能冲突", foreground="orange")
            else:
                self.port_conflict_label.config(text="✓ 端口可用", foreground="green")
                
        except tk.TclError:
            # 处理非数字输入
            self.port_conflict_label.config(text="⚠ 请输入有效数字")
        except Exception as e:
            self.port_conflict_label.config(text="⚠ 检查失败")

    def update_port_info(self, *args):
        """更新端口说明信息"""
        protocol = self.v2ray_protocol.get()
        
        if "ws" in protocol:
            text = "(Nginx监听端口，用户访问的端口)"
        else:
            text = "(V2Ray监听端口，用户访问的端口)"
        
        self.port_info.config(text=text)

    def on_proxy_change(self, event):
        padx, pady = 5, 5
        """当伪装网站选择变化时显示/隐藏自定义输入框"""
        if self.proxy_url_var.get() == "自定义":
            self.custom_proxy_frame.pack(fill="x", padx=padx, pady=2)
        else:
            self.custom_proxy_frame.pack_forget()

    def update_protocol_ui(self, *args):
        """根据协议方案更新UI"""
        protocol = self.v2ray_protocol.get()
        
        # 显示/隐藏WebSocket路径
        if "ws_" in protocol:
            self.ws_frame.pack(fill="x", padx=5, pady=2)
        else:
            self.ws_frame.pack_forget()
        
        # 显示/隐藏Trojan密码
        if "trojan" in protocol:
            self.trojan_frame.pack(fill="x", padx=5, pady=2)
        else:
            self.trojan_frame.pack_forget()
    
    def update_auth_ui(self, *args):
        """根据认证方式更新UI - 使用pack_forget"""
        method = self.auth_method.get()
        
        # 隐藏所有框架
        self.password_frame.pack_forget()
        self.key_frame.pack_forget()
        self.key_pass_frame.pack_forget()
        
        if method == "password":
            self.password_frame.pack(fill="x", pady=5)
        else:
            self.key_frame.pack(fill="x", pady=5)
            self.key_pass_frame.pack(fill="x", pady=5)
    
    def show_batch_example(self):
        """显示批量部署示例"""
        example = """# 每行一个服务器，格式为: IP 端口 用户名 密码/密钥路径 [密钥密码]
# 使用密码认证:
192.168.1.100 22 root mypassword
192.168.1.101 22 admin admin123

# 使用密钥认证:
192.168.1.102 22 ubuntu /path/to/key.pem
192.168.1.103 22 centos /path/to/key.pem mykeypassword"""
        
        # 创建居中对话框
        example_window = tk.Toplevel(self.master)
        example_window.title("批量部署示例")
        example_window.geometry("600x400")
        self.center_window(example_window)
        
        # 添加文本区域
        text_area = scrolledtext.ScrolledText(example_window, wrap=tk.WORD)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_area.insert(tk.END, example)
        text_area.config(state=tk.DISABLED)
        
        # 添加关闭按钮
        close_button = ttk.Button(
            example_window, 
            text="关闭", 
            command=example_window.destroy,
            style="Secondary.TButton"
        )
        close_button.pack(pady=10)
    
    def browse_key_file(self):
        """浏览密钥文件"""
        file_path = filedialog.askopenfilename(
            title="选择SSH密钥文件",
            filetypes=[("SSH密钥文件", "*.pem"), ("所有文件", "*.*")]
        )
        if file_path:
            self.ssh_key_path.set(file_path)
    
    def test_cf_connection(self):
        """测试Cloudflare连接"""
        threading.Thread(target=self._test_cf_connection, daemon=True).start()
    
    def test_server_connection(self):
        """测试服务器连接"""
        if self.deploy_mode.get() == "single":
            threading.Thread(target=self._test_server_connection, daemon=True).start()
        else:
            # 创建居中对话框
            self.center_window(self.master)
            messagebox.showinfo("提示", "批量模式下请直接开始部署", parent=self.master)
    
    def _test_cf_connection(self):
        """实际测试Cloudflare连接"""
        self.log_message("正在测试Cloudflare连接...")
        
        api_token = self.cf_api_token.get().strip()
        domain = self.cf_domain.get().strip()
        
        if not api_token or not domain:
            self.log_message("错误: 请填写Cloudflare API令牌和域名", "error")
            return
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # 获取区域列表
            url = "https://api.cloudflare.com/client/v4/zones"
            params = {"name": domain}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get("success", False) and data["result"]:
                zone_id = data["result"][0]["id"]
                self.log_message(f"Cloudflare连接成功! 域名: {domain}")
                self.log_message(f"账户: {data['result'][0]['account']['name']}")
                self.log_message(f"状态: {data['result'][0]['status']}")
                self.log_message(f"名称服务器: {', '.join(data['result'][0]['name_servers'])}")
            else:
                errors = data.get("errors", [])
                error_msgs = [e["message"] for e in errors] if errors else ["未知错误"]
                self.log_message(f"Cloudflare连接失败: {', '.join(error_msgs)}", "error")
        except Exception as e:
            self.log_message(f"测试Cloudflare连接时出错: {str(e)}", "error")
    
    def _test_server_connection(self):
        """实际测试服务器连接"""
        self.log_message("正在测试服务器连接...")
        
        ip = self.server_ip.get().strip()
        port = self.ssh_port.get()
        username = self.ssh_username.get().strip()
        auth_method = self.auth_method.get()
        
        if not ip:
            self.log_message("错误: 请填写服务器IP地址", "error")
            return
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if auth_method == "password":
                password = self.ssh_password.get()
                ssh.connect(ip, port=port, username=username, password=password, timeout=10)
            else:
                key_path = self.ssh_key_path.get()
                key_pass = self.ssh_key_pass.get() or None
                
                # 尝试加载密钥
                try:
                    key = paramiko.RSAKey.from_private_key_file(key_path, password=key_pass)
                except paramiko.ssh_exception.PasswordRequiredException:
                    self.log_message("错误: 密钥文件需要密码", "error")
                    return
                except Exception as e:
                    self.log_message(f"加载密钥文件时出错: {str(e)}", "error")
                    return
                
                ssh.connect(ip, port=port, username=username, pkey=key, timeout=10)
            
            # 执行简单命令测试
            stdin, stdout, stderr = ssh.exec_command("uname -a")
            output = stdout.read().decode().strip()
            
            if output:
                self.log_message(f"服务器连接成功! 系统信息: {output}")
                
                # 检查系统版本
                stdin, stdout, stderr = ssh.exec_command("cat /etc/os-release | grep PRETTY_NAME")
                os_info = stdout.read().decode().strip()
                if os_info:
                    os_version = os_info.split('=')[1].strip('"')
                    self.log_message(f"操作系统: {os_version}")
                
                # 检查是否安装过V2Ray
                stdin, stdout, stderr = ssh.exec_command("command -v v2ray")
                v2ray_installed = bool(stdout.read().decode().strip())
                self.log_message(f"V2Ray已安装: {'是' if v2ray_installed else '否'}")
                
                # 更新卸载按钮状态
                self.master.after(0, lambda: self.update_uninstall_button(v2ray_installed))
                
                # 检查80和443端口是否被占用
                stdin, stdout, stderr = ssh.exec_command("ss -tuln | grep -E ':80\\b|:443\\b' || true")
                ports_used = stdout.read().decode().strip()
                if ports_used:
                    self.log_message("警告: 以下端口已被占用，可能会影响部署:", "warning")
                    self.log_message(ports_used)
            else:
                self.log_message("服务器连接成功，但无法获取系统信息", "warning")
            
            ssh.close()
        except Exception as e:
            # 连接失败时禁用卸载按钮
            self.master.after(0, lambda: self.update_uninstall_button(False))
            self.log_message(f"服务器连接失败: {str(e)}", "error")
    
    # 添加卸载按钮状态更新方法
    def update_uninstall_button(self, installed):
        """更新卸载按钮状态"""
        if installed:
            self.uninstall_button.config(state=tk.NORMAL)
            self.uninstall_button["text"] = "卸载V2Ray"
        else:
            self.uninstall_button.config(state=tk.DISABLED)
            self.uninstall_button["text"] = "V2Ray未安装"
    # 添加卸载V2Ray功能
    def uninstall_v2ray(self):
        """卸载服务器上的V2Ray"""
        # 确认操作
        if not messagebox.askyesno("确认卸载", "确定要卸载服务器上的V2Ray吗？此操作不可逆！"):
            return
        
        # 收集服务器配置
        config = self.collect_config()
        
        # 使用单独的线程执行卸载
        threading.Thread(target=self._uninstall_v2ray, args=(config,), daemon=True).start()
    def _uninstall_v2ray(self, config):
        """实际卸载V2Ray"""
        server_ip = config["server_ip"]
        ssh = None
        
        try:
            # 连接到服务器
            ssh = self.connect_to_server(config)
            self.log_message(f"开始卸载服务器 {server_ip} 上的V2Ray...")
            
            # 停止V2Ray服务
            self.run_ssh_command(ssh, "sudo systemctl stop v2ray", ignore_errors=True)
            
            # 执行卸载脚本（官方提供的卸载脚本）
            uninstall_cmd = "sudo bash -c \"$(curl -L https://raw.githubusercontent.com/v2fly/fhs-install-v2ray/master/install-release.sh)\" @ --remove"
            self.run_ssh_command(ssh, uninstall_cmd, timeout=300)
            
            # 删除相关文件和目录
            self.run_ssh_command(ssh, "sudo rm -rf /usr/local/bin/v2ray /usr/local/etc/v2ray /var/log/v2ray", ignore_errors=True)
            
            # 删除systemd服务文件
            self.run_ssh_command(ssh, "sudo rm -f /etc/systemd/system/v2ray.service /etc/systemd/system/v2ray@.service", ignore_errors=True)
            
            # 删除日志轮转配置
            self.run_ssh_command(ssh, "sudo rm -f /etc/logrotate.d/v2ray", ignore_errors=True)
            
            # 清理残留文件
            self.run_ssh_command(ssh, "sudo rm -f /usr/local/bin/v2ctl", ignore_errors=True)
            
            # 重新加载systemd
            self.run_ssh_command(ssh, "sudo systemctl daemon-reload")
            
            self.log_message(f"服务器 {server_ip} 上的V2Ray已成功卸载!", "success")
            
            # 更新卸载按钮状态
            self.master.after(0, lambda: self.update_uninstall_button(False))
            
        except Exception as e:
            self.log_message(f"卸载V2Ray失败: {str(e)}", "error")
        finally:
            try:
                if ssh:
                    ssh.close()
            except:
                pass
    def log_message(self, message, level="info"):
        """向日志区域添加消息"""
        self.log_text.config(state=tk.NORMAL)
        
        # 添加时间戳
        timestamp = time.strftime("%H:%M:%S")
        
        # 添加消息
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.log_text.insert(tk.END, message + "\n", level)
        
        # 滚动到底部
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 更新状态栏
        if level in ("error", "warning", "success"):
            self.status_var.set(message)

    def start_deployment(self):
        """开始部署"""
        self.stop_deployment_flag = False
        self.deploy_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        
        # 更新所有任务状态为"正在部署"
        for item in self.task_tree.get_children():
            self.update_task_item(item, task_status="正在部署")
        
        if self.deploy_mode.get() == "single":
            self.log_message("开始单服务器部署...")
            self.running_tasks = 1  # 标记有任务正在运行
            threading.Thread(target=self._start_single_deployment, daemon=True).start()
        else:
            self.log_message("开始批量部署...")
            threading.Thread(target=self._start_batch_deployment, daemon=True).start()
    
    def _start_single_deployment(self):
        """执行单服务器部署"""
        try:
            # 收集配置信息
            config = self.collect_config()

            # 为单服务器生成 server_id
            config["server_id"] = f"{config['server_ip']}_{int(time.time())}"
            
            # 验证配置
            self.validate_config()
            
            # 执行部署
            self.deploy_to_server(config)
            
            self.log_message("单服务器部署完成!", "success")
        except Exception as e:
            self.log_message(f"部署过程中出错: {str(e)}", "error")
            self.log_message(traceback.format_exc(), "error")
        finally:
            self.running_tasks = 0  # 标记任务完成
            self.deploy_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)

    def _start_batch_deployment(self):
        """执行批量部署 - 使用经过验证的子域名"""
        try:
            # 生成批量部署前缀（单个字母）
            self.batch_prefix = self.generate_batch_prefix()
            self.log_message(f"批量部署前缀: {self.batch_prefix}")
            
            # 获取服务器数量
            server_count = len(self.task_tree.get_children())
            if server_count == 0:
                raise ValueError("没有可部署的服务器")
            
            # 创建进度窗口
            progress_window = tk.Toplevel(self.master)
            progress_window.title("子域名验证")
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)
            progress_window.grab_set()  # 模态对话框
            self.center_window(progress_window)
            
            # 添加进度标签
            progress_label = ttk.Label(
                progress_window, 
                text=f"正在验证 {self.batch_prefix}* 子域名...",
                font=("微软雅黑", 11)
            )
            progress_label.pack(pady=15)
            
            # 添加进度条
            progress_bar = ttk.Progressbar(
                progress_window, 
                orient="horizontal",
                length=350, 
                mode="indeterminate"
            )
            progress_bar.pack(pady=5)
            progress_bar.start()
            
            # 添加日志标签
            status_var = tk.StringVar(value="正在查询Cloudflare API...")
            status_label = ttk.Label(
                progress_window, 
                textvariable=status_var,
                font=("微软雅黑", 9)
            )
            status_label.pack(pady=5)
            
            # 更新UI
            self.master.update()
            
            # 在后台线程中获取子域名
            def fetch_subdomains():
                try:
                    # 获取当前域名的所有子域名（使用缓存）
                    domain = self.cf_domain.get().strip()
                    if not domain:
                        raise ValueError("请先设置主域名")
                    
                    # 获取该前缀的所有子域名
                    subdomains = self.get_subdomains_by_prefix(domain, self.batch_prefix)
                    
                    # 生成可用子域名列表
                    available_subdomains = self.generate_available_subdomains(
                        self.batch_prefix, 
                        subdomains, 
                        server_count
                    )
                    
                    # 更新任务列表
                    self.master.after(0, lambda: self.update_batch_tasks(available_subdomains))
                    
                    # 关闭进度窗口
                    progress_window.destroy()
                    
                except Exception as e:
                    # 出错时关闭进度窗口并显示错误
                    progress_window.destroy()
                    self.log_message(f"子域名验证失败: {str(e)}", "error")
                    messagebox.showerror("错误", f"子域名验证失败: {str(e)}", parent=self.master)
            
            # 启动后台线程
            threading.Thread(target=fetch_subdomains, daemon=True).start()
            
            # 等待进度窗口关闭
            self.master.wait_window(progress_window)
            
            # 获取当前配置
            base_config = self.collect_base_config()
            
            # 为每个服务器构建配置
            servers = []
            for idx, item in enumerate(self.task_tree.get_children(), 1):
                if self.stop_deployment_flag:
                    break
                
                values = self.task_tree.item(item, "values")
                server_ip = values[1]
                
                # 获取分配的子域名
                subdomain = values[5]  # 第五列是子域名
                
                # 构建服务器配置
                server_config = {
                    "server_ip": server_ip,
                    "ssh_port": int(values[2]),
                    "ssh_username": values[3],
                    "auth_method": self.auth_method.get(),
                    "cf_subdomain": subdomain,
                    "server_id": f"{server_ip}_{int(time.time())}"
                }
                
                # 添加认证信息
                if server_config["auth_method"] == "password":
                    server_config["ssh_password"] = self.ssh_password.get()
                else:
                    server_config["ssh_key_path"] = self.ssh_key_path.get()
                    server_config["ssh_key_pass"] = self.ssh_key_pass.get()
                
                # 合并基础配置
                server_config = {**base_config, **server_config}
                
                # 添加到服务器列表
                servers.append(server_config)
            
            # 记录生成的子域名
            subdomains = [s["cf_subdomain"] for s in servers]
            self.log_message(f"为 {len(servers)} 台服务器分配验证过的子域名: {', '.join(subdomains)}")
            
            if not servers:
                raise ValueError("没有可部署的服务器")
            
            # 使用线程池执行批量部署
            self.running_tasks = len(servers)
            self.max_workers = min(self.max_workers_var.get(), 10)
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                
                for server in servers:
                    if self.stop_deployment_flag:
                        break
                    
                    # 提交任务
                    futures.append(executor.submit(self.deploy_to_server, server))
                
                # 等待所有任务完成
                for future in as_completed(futures):
                    self.running_tasks -= 1
                    try:
                        future.result()
                    except Exception as e:
                        self.log_message(f"任务执行出错: {str(e)}", "error")
            
            if not self.stop_deployment_flag:
                self.log_message("批量部署完成!", "success")
            else:
                self.log_message("批量部署已停止", "warning")
                
        except Exception as e:
            self.log_message(f"批量部署过程中出错: {str(e)}", "error")
            self.log_message(traceback.format_exc(), "error")
        finally:
            self.deploy_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.running_tasks = 0
            self.batch_prefix = None

    def update_batch_tasks(self, subdomains):
        """更新任务列表中的子域名"""
        for idx, item in enumerate(self.task_tree.get_children()):
            if idx < len(subdomains):
                values = list(self.task_tree.item(item, "values"))
                # 确保有足够列
                if len(values) < 8:
                    values.append("")  # 添加子域名列
                # 更新子域名
                values[5] = subdomains[idx]  # 第五列是子域名
                # 更新任务状态
                values[7] = "等待部署"
                # 更新Treeview项
                self.task_tree.item(item, values=values)

    def generate_batch_prefix(self):
        """生成批量部署前缀（单个字母）"""
        # 避免使用易混淆的字母 i, o, l, 1
        valid_letters = [c for c in 'abcdefghjkmnpqrstuvwxyz' if c not in 'ilo1']
        return random.choice(valid_letters).upper()

    def get_subdomains_by_prefix(self, domain, prefix):
        """获取指定前缀的子域名"""
        # 检查缓存
        cache_key = f"{domain}_{prefix}"
        if hasattr(self, 'prefix_cache') and cache_key in self.prefix_cache:
            cache_data, timestamp = self.prefix_cache[cache_key]
            if time.time() - timestamp < 300:  # 5分钟缓存
                self.log_message(f"使用缓存的前缀 '{prefix}' 子域名列表")
                return cache_data
        
        self.log_message(f"从Cloudflare API获取 '{prefix}*' 子域名...")
        
        api_token = self.cf_api_token.get().strip()
        if not api_token:
            self.log_message("警告: 未设置Cloudflare API令牌，将无法验证子域名", "warning")
            return set()
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # 获取区域ID
            url = "https://api.cloudflare.com/client/v4/zones"
            params = {"name": domain}
            response = requests.get(url, headers=headers, params=params, timeout=15)
            data = response.json()
            
            if not (response.status_code == 200 and data.get("success", False) and data["result"]):
                error_msg = data.get("errors", [{}])[0].get("message", "未知错误")
                raise Exception(f"获取Zone ID失败: {error_msg}")
            
            zone_id = data["result"][0]["id"]
            
            # 获取所有匹配前缀的DNS记录
            all_subdomains = set()
            page = 1
            per_page = 100
            
            while True:
                url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
                params = {
                    "type": "A",
                    "per_page": per_page,
                    "page": page,
                    "match": "all"
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=15)
                data = response.json()
                
                if not data["success"]:
                    error_msg = data.get("errors", [{}])[0].get("message", "未知错误")
                    raise Exception(f"获取DNS记录失败: {error_msg}")
                
                for record in data["result"]:
                    name = record["name"]
                    if name.endswith(domain):
                        # 提取子域名部分
                        subdomain_part = name.replace(f".{domain}", "")
                        # 检查是否以指定前缀开头（不区分大小写）
                        if subdomain_part.lower().startswith(prefix.lower()):
                            all_subdomains.add(subdomain_part.lower())
                
                # 检查是否有更多页面
                if len(data["result"]) < per_page:
                    break
                    
                page += 1
            
            # 更新缓存
            if not hasattr(self, 'prefix_cache'):
                self.prefix_cache = {}
            self.prefix_cache[cache_key] = (all_subdomains, time.time())
            self.log_message(f"成功获取 {len(all_subdomains)} 个 '{prefix}*' 子域名")
            return all_subdomains
            
        except Exception as e:
            self.log_message(f"获取子域名失败: {str(e)} - 将使用空集合", "warning")
            # 返回空集合
            return set()

    def generate_available_subdomains(self, prefix, existing_subdomains, count):
        """生成指定数量的可用子域名"""
        available_subdomains = []
        used_subdomains = set()
        
        # 尝试生成连续数字子域名
        for i in range(1, count + 1):
            candidate = f"{prefix}{i:03d}"  # 格式: 前缀+3位数字
            
            # 检查是否可用
            if (candidate.lower() not in existing_subdomains and 
                candidate.lower() not in used_subdomains):
                available_subdomains.append(candidate)
                used_subdomains.add(candidate.lower())
            else:
                # 如果不可用，尝试其他方案
                subdomain = self.generate_unique_subdomain(prefix, existing_subdomains, used_subdomains)
                available_subdomains.append(subdomain)
                used_subdomains.add(subdomain.lower())
        
        return available_subdomains

    def find_available_subdomain(self, idx, existing_subdomains, used_subdomains, max_attempts=20):
        """查找可用的子域名"""
        domain = self.cf_domain.get().strip()
        if not domain:
            return None
        
        # 首选方案：基础子域名 (前缀+两位数字)
        base_subdomain = f"{self.batch_prefix}{idx:02d}"
        
        # 检查是否可用
        if (base_subdomain not in existing_subdomains and 
            base_subdomain not in used_subdomains and
            self.is_subdomain_available(f"{base_subdomain}.{domain}")):
            return base_subdomain
        
        # 备选方案1：添加随机后缀
        for _ in range(max_attempts):
            rand_suffix = ''.join(random.choices(string.ascii_lowercase, k=3))
            candidate = f"{base_subdomain}_{rand_suffix}"
            
            if (candidate not in existing_subdomains and 
                candidate not in used_subdomains and
                self.is_subdomain_available(f"{candidate}.{domain}")):
                return candidate
        
        # 备选方案2：增加数字后缀
        for num in range(1, 100):
            candidate = f"{self.batch_prefix}{idx:02d}_{num:02d}"
            
            if (candidate not in existing_subdomains and 
                candidate not in used_subdomains and
                self.is_subdomain_available(f"{candidate}.{domain}")):
                return candidate
        
        return None
    
    def generate_unique_subdomain(self, prefix, existing_subdomains=None, max_attempts=50):
        """生成唯一的子域名"""
        # 确保 existing_subdomains 是可迭代的，即使是空
        if existing_subdomains is None:
            existing_subdomains = set()
        
        # 转换所有现有子域名为小写以便比较
        existing_lower = {s.lower() for s in existing_subdomains}
        
        # 尝试生成连续数字子域名
        for num in range(1, max_attempts + 1):
            candidate = f"{prefix}{num:03d}"  # 格式: 前缀+3位数字
            
            # 检查是否可用（不在现有列表中）
            if candidate.lower() not in existing_lower:
                return candidate
        
        # 如果连续数字用完，尝试添加随机后缀
        for _ in range(max_attempts):
            rand_suffix = ''.join(random.choices(string.ascii_lowercase, k=2))
            candidate = f"{prefix}{random.randint(1, max_attempts):03d}_{rand_suffix}"
            
            if candidate.lower() not in existing_lower:
                return candidate
        
        # 作为最后手段，生成完全随机的
        rand_prefix = random.choice('abcdefghjkmnpqrstuvwxyz')
        rand_num = random.randint(1, max_attempts)
        return f"{rand_prefix}{rand_num:03d}"

    def parse_batch_servers(self, batch_text):
        """解析批量服务器配置"""
        servers = []
        
        for line in batch_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            parts = line.split()
            if len(parts) < 4:
                continue
                
            server = {
                "server_ip": parts[0],
                "ssh_port": int(parts[1]),
                "ssh_username": parts[2],
                "auth_method": "password",
                "ssh_password": parts[3]
            }
            
            # 检查是否是密钥认证
            if len(parts) >= 4 and os.path.exists(parts[3]):
                server["auth_method"] = "key"
                server["ssh_key_path"] = parts[3]
                server.pop("ssh_password", None)
                
                if len(parts) >= 5:
                    server["ssh_key_pass"] = parts[4]
            
            servers.append(server)
        
        return servers
    
    def stop_deployment(self):
        """停止部署过程"""
        self.stop_deployment_flag = True
        self.log_message("正在停止部署...", "warning")
        self.stop_button.config(state=tk.DISABLED)
    
    def deploy_to_server(self, config):
        """部署到单个服务器"""
        ssh = None
        server_ip = config["server_ip"]
        
        try:
            # 确保子域名存在且符合格式
            if "cf_subdomain" not in config or not config["cf_subdomain"]:
                # 获取用户输入的子域名
                subdomain = self.cf_subdomain.get().strip()
                
                # 验证子域名格式
                """if not re.match(r"^[a-zA-Z]\d{3}$", subdomain):
                    # 如果格式不正确，生成一个随机子域名并更新UI
                    prefix = self.generate_batch_prefix().lower()
                    subdomain = f"{prefix}{random.randint(1, 999):03d}"
                    self.cf_subdomain.set(subdomain)
                    self.log_message(f"生成随机子域名: {subdomain}")"""
                
                config["cf_subdomain"] = subdomain
            
            # 构建完整域名
            config["full_domain"] = f"{config['cf_subdomain']}.{config['cf_domain']}"
            
            # 记录部署信息
            self.log_message(f"开始部署服务器: {server_ip}")
            self.log_message(f"使用子域名: {config['cf_subdomain']}")
            self.log_message(f"完整域名: {config['full_domain']}")
            self.log_message(f"协议方案: {config['protocol']}")

            # 更新任务状态
            if self.deploy_mode.get() == "single":
                # 单服务器部署不需要任务列表
                pass
            else:
                # 多服务器部署更新任务列表
                selected_items = self.task_list.selection()
                if selected_items:
                    item = selected_items[0]
                    self.task_list.item(item, values=("部署中", "进行中"))
                    
                    # 确保使用 self.task_configs
                    self.task_configs[item] = config  # 存储配置

            # 连接到服务器
            ssh = self.connect_to_server(config)
            self.fix_apt_locks(ssh)

            # 1. 更新DNS记录
            self.update_dns(config)

            # 2. 配置防火墙
            self.configure_firewall(ssh, config)

            # 3. 设置SELinux
            self.set_selinux(ssh)
            
            # 4. 系统更新
            self.update_system(ssh)
            
            # 5. 安装必要组件
            self.install_dependencies(ssh)
            
            # 6. 申请证书（如果需要）
            if "tls" in config["protocol"] or "xtls" in config["protocol"]:
                config["tls_cert"], config["tls_key"] = self.get_cert(ssh, config)
            
            # 7. 配置Nginx
            self.configure_nginx(ssh, config)

            # 8. 安装V2Ray
            self.install_v2ray(ssh, config)
            
            # 9. 配置V2Ray
            self.configure_v2ray(ssh, config)
            
            # 10. 启动服务
            self.start_services(ssh, config)

            # 11. 测试连接
            # self.test_v2ray_connection(config)
            
            # 12. 开启BBR加速
            if config["enable_bbr"]:
                self.enable_bbr_acceleration(ssh)
            
            # 13. 显示连接信息
            self.show_connection_info(config)

            self.log_message(f"服务器 {server_ip} 部署成功!", "success")
            self.update_task_status(server_ip, "部署完成")

            # 保存配置信息
            # 在任务树中查找与当前服务器IP匹配的项
            for item in self.task_tree.get_children():
                values = self.task_tree.item(item, "values")
                # 第二列是IP
                if len(values) > 1 and values[1] == server_ip:
                    self.task_configs[item] = config
                    break

        except Exception as e:
            """# 更友好的错误处理
            error_details = f"服务器 {server_ip} 部署失败: {str(e)}"
            self.log_message(error_details, "error")
            self.log_message(traceback.format_exc(), "error")
            self.update_task_status(server_ip, "部署失败")"""
            # 错误处理
            self.log_message(f"部署失败: {str(e)}", "error")
            # 更新任务状态为失败
            if self.deploy_mode.get() != "single" and selected_items:
                item = selected_items[0]
                self.task_list.item(item, values=("失败", str(e)))
            
        finally:
            if ssh:
                ssh.close()
    
    def update_task_status(self, server_ip, task_status):
        """根据服务器IP更新任务状态"""
        for item in self.task_tree.get_children():
            values = self.task_tree.item(item, "values")
            if values[1] == server_ip:  # 第二列是IP
                self.update_task_item(item, task_status=task_status)
                break
    
    def collect_config(self):
        """收集所有配置信息（确保子域名格式正确）"""
        # 获取子域名值
        subdomain = self.cf_subdomain.get().strip()
        
        # 验证子域名格式
        """if not re.match(r"^[a-zA-Z]\d{3}$", subdomain):
            # 如果格式不正确，生成一个随机子域名并更新UI
            prefix = self.generate_batch_prefix().lower()
            subdomain = f"{prefix}{random.randint(1, 999):03d}"
            self.cf_subdomain.set(subdomain)  # 更新UI
            self.log_message(f"生成随机子域名: {subdomain}", "warning")"""
        
        config = {
            # Cloudflare配置
            "cf_api_token": self.cf_api_token.get().strip(),
            "cf_domain": self.cf_domain.get().strip(),
            "cf_subdomain": subdomain,  # 使用验证后的子域名
            "cf_proxy": self.cf_proxy_enabled.get(), 
            
            # V2Ray配置
            "protocol": self.v2ray_protocol.get(),
            "v2ray_port": self.v2ray_port.get(),
            "uuid": self.v2ray_uuid.get(),
            "ws_path": self.ws_path_var.get(),
            "trojan_password": self.trojan_password_var.get(),
            "log_level": self.log_level.get(),
            "custom_config": self.custom_config_text.get("1.0", tk.END).strip(),
            "protocol": self.v2ray_protocol.get(),  # 这里保持用户友好名称

            # Socks5 配置
            "enable_socks5": self.enable_socks5.get(),
            "socks5_port": self.socks5_port.get(),
            "socks5_auth": self.socks5_auth.get(),
            "socks5_username": self.socks5_username.get(),
            "socks5_password": self.socks5_password.get(),
            
            # 其他设置
            "enable_bbr": self.enable_bbr.get(),
            "enable_ipv6": self.ipv6_status.get(),
            "proxy_type": self.proxy_url_var.get(),
            "proxy_url": self.custom_proxy_entry.get() if self.proxy_url_var.get() == "自定义" else "",
            "allow_spider": self.allow_spider_var.get()
        }
        
        # 如果是单服务器模式，添加服务器配置
        if self.deploy_mode.get() == "single":
            config.update({
                "server_ip": self.server_ip.get().strip(),
                "ssh_port": self.ssh_port.get(),
                "ssh_username": self.ssh_username.get().strip(),
                "auth_method": self.auth_method.get(),
                "ssh_password": self.ssh_password.get(),
                "ssh_key_path": self.ssh_key_path.get(),
                "ssh_key_pass": self.ssh_key_pass.get()
            })
        
        # 生成完整域名
        config["full_domain"] = f"{config['cf_subdomain']}.{config['cf_domain']}"
        
        return config
    
    def validate_config(self):
        """验证配置是否完整"""
        # 验证Cloudflare配置
        if not self.cf_api_token.get().strip():
            raise ValueError("Cloudflare API令牌不能为空")
        if not self.cf_domain.get().strip():
            raise ValueError("主域名不能为空")
        
        # 验证V2Ray配置
        if "trojan" in self.v2ray_protocol.get() and not self.trojan_password_var.get():
            raise ValueError("Trojan密码不能为空")
        
        # 验证端口范围
        if not (1 <= self.ssh_port.get() <= 65535):
            raise ValueError("SSH端口必须在1-65535范围内")
        if not (1 <= self.v2ray_port.get() <= 65535):
            raise ValueError("V2Ray端口必须在1-65535范围内")
        
        # 验证UUID格式
        if "vmess" in self.v2ray_protocol.get() or "vless" in self.v2ray_protocol.get():
            uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
            if not uuid_pattern.match(self.v2ray_uuid.get()):
                raise ValueError("UUID格式不正确")

        # 验证Socks5配置
        if self.enable_socks5.get():
            try:
                socks5_port = self.socks5_port.get()
                
                # 检查端口范围
                if not (1 <= socks5_port <= 65535):
                    raise ValueError(f"Socks5端口必须在1-65535范围内，当前: {socks5_port}")
                    
                # 检查与主端口冲突
                if socks5_port == self.v2ray_port.get():
                    raise ValueError(f"Socks5端口({socks5_port})不能与主协议端口相同")
                    
                # 检查认证配置
                if self.socks5_auth.get() == "password":
                    if not self.socks5_username.get().strip():
                        raise ValueError("启用Socks5密码认证时，用户名不能为空")
                    if not self.socks5_password.get().strip():
                        raise ValueError("启用Socks5密码认证时，密码不能为空")
                        
            except tk.TclError:
                raise ValueError("Socks5端口必须是有效的数字")
    
    def update_dns(self, config):
        """更新Cloudflare DNS记录"""
        if self.stop_deployment_flag:
            raise Exception("部署已取消")
        
        # 安全获取必要的配置值
        api_token = config.get("cf_api_token", "").strip()
        domain = config.get("cf_domain", "").strip()
        subdomain = config.get("cf_subdomain", "v2ray").strip()
        server_ip = config.get("server_ip", "")
        cf_proxy = config.get("cf_proxy", True)  # 默认启用代理
        
        if not api_token:
            raise ValueError("Cloudflare API令牌不能为空")
        if not domain:
            raise ValueError("主域名不能为空")
        if not server_ip:
            raise ValueError("服务器IP地址不能为空")
        
        full_domain = f"{subdomain}.{domain}"
        
        self.log_message(f"正在更新DNS记录: {full_domain} -> {server_ip}")
        
        # 提前定义 headers 变量
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # 获取区域ID
            url = "https://api.cloudflare.com/client/v4/zones"
            params = {"name": domain}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            if not (response.status_code == 200 and data.get("success", False) and data["result"]):
                raise Exception("获取Zone ID失败")
            
            zone_id = data["result"][0]["id"]
            
            # 检查DNS记录是否已存在
            url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
            params = {"name": full_domain, "type": "A"}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            record_id = None
            if data["success"] and data["result"]:
                record_id = data["result"][0]["id"]
                self.log_message(f"找到现有DNS记录: {record_id}")
            
            # 创建或更新DNS记录
            record_data = {
                "type": "A",
                "name": subdomain,
                "content": server_ip,
                "ttl": 1,  # 自动TTL
                "proxied": cf_proxy
            }
            
            if record_id:
                # 更新现有记录
                url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
                response = requests.put(url, headers=headers, json=record_data, timeout=10)
            else:
                # 创建新记录
                url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
                response = requests.post(url, headers=headers, json=record_data, timeout=10)
            
            data = response.json()
            
            if data["success"]:
                result = data["result"]
                self.log_message(f"DNS记录更新成功! 域名: {result['name']}")
                self.log_message(f"IP地址: {result['content']}")
                self.log_message(f"代理状态: {'开启' if result['proxied'] else '关闭'}")
            else:
                errors = data.get("errors", [])
                error_msgs = [e["message"] for e in errors] if errors else ["未知错误"]
                raise Exception(f"更新DNS记录失败: {', '.join(error_msgs)}")
        except Exception as e:
            # 在异常处理中安全地使用 headers
            error_details = f"DNS记录更新失败: {str(e)}"
            
            # 尝试添加更多调试信息
            try:
                if 'response' in locals():
                    error_details += f"\n状态码: {response.status_code}"
                    if hasattr(response, 'text'):
                        error_details += f"\n响应内容: {response.text[:200]}"
            except:
                pass
            
            # 确保 headers 变量存在
            try:
                if headers:
                    error_details += f"\n使用的API令牌: {headers['Authorization'][:20]}..."
            except:
                pass
            
            self.log_message(error_details, "error")
            raise Exception(error_details)
    
    def connect_to_server(self, config):
        """连接到服务器"""
        if self.stop_deployment_flag:
            raise Exception("部署已取消")
        
        server_ip = config["server_ip"]
        port = config["ssh_port"]
        username = config["ssh_username"]
        auth_method = config["auth_method"]
        
        self.log_message(f"正在连接到服务器 {server_ip}:{port}...")
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if auth_method == "password":
                password = config["ssh_password"]
                ssh.connect(server_ip, port=port, username=username, password=password, timeout=30)
            else:
                key_path = config["ssh_key_path"]
                key_pass = config.get("ssh_key_pass") or None
                
                # 尝试加载密钥
                try:
                    key = paramiko.RSAKey.from_private_key_file(key_path, password=key_pass)
                except paramiko.ssh_exception.PasswordRequiredException:
                    raise Exception("SSH密钥需要密码，请提供密码")
                except Exception as e:
                    raise Exception(f"加载SSH密钥失败: {str(e)}")
                
                ssh.connect(server_ip, port=port, username=username, pkey=key, timeout=30)
            
            self.log_message(f"服务器 {server_ip} 连接成功!")
            return ssh
        except Exception as e:
            raise Exception(f"连接服务器 {server_ip} 失败: {str(e)}")
    
    def update_system(self, ssh):
        """更新系统 - 仅使用状态栏显示进度"""
        if self.stop_deployment_flag:
            raise Exception("部署已取消")
        
        # 初始状态设置
        self.log_message("正在更新系统...")
        self.status_var.set("正在更新系统...")
        self.show_progress_indicator()
        
        # 添加提示语到状态栏
        self.master.after(0, lambda: self.update_hint_label.config(
            text="系统更新需要一些时间，请耐心等待...",
            foreground="blue"
        ))
        
        try:
            # 检测包管理器
            self.status_var.set("检测包管理器...")
            stdin, stdout, stderr = ssh.exec_command("command -v apt-get || command -v yum || echo unknown")
            pkg_manager = stdout.read().decode('utf-8', errors='replace').strip()
            
            if "apt-get" in pkg_manager:
                # APT更新流程
                self.status_var.set("使用APT更新系统...")
                commands = [
                    "sudo apt-get update -y",
                    "sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::=\"--force-confold\"",
                    "sudo apt-get autoremove -y",
                    "sudo apt-get clean"
                ]
                
                for idx, cmd in enumerate(commands):
                    if self.stop_deployment_flag:
                        raise Exception("部署已取消")
                    
                    self.status_var.set(f"APT更新: 步骤 {idx+1}/{len(commands)}")
                    self.log_message(f"执行命令: {cmd.split()[0]}...")
                    
                    # 执行命令
                    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
                    
                    # 等待完成（不使用实时输出，避免日志干扰）
                    stdout.channel.recv_exit_status()
            
            elif "yum" in pkg_manager:
                # YUM更新流程
                self.status_var.set("使用YUM更新系统...")
                commands = [
                    "sudo yum update -y",
                    "sudo yum clean all"
                ]
                
                for idx, cmd in enumerate(commands):
                    self.run_ssh_command(ssh, cmd, timeout=600, ignore_errors=True)
                    self.status_var.set(f"YUM更新: 步骤 {idx+1}/{len(commands)}")
            
            else:
                self.log_message("无法确定包管理器，跳过系统更新", "warning")
                self.status_var.set("系统更新已跳过")
                return
            
            # 完成状态
            self.log_message("系统更新成功完成!")
            self.status_var.set("系统更新完成")
            
        except Exception as e:
            # 错误处理
            self.log_message(f"系统更新失败: {str(e)}", "error")
            self.status_var.set(f"更新失败: {str(e)}")
        finally:
            # 确保清除提示语
            self.master.after(0, lambda: self.update_hint_label.config(text=""))
            # 确保始终隐藏进度条
            self.hide_progress_indicator()
            
            # 短暂显示成功状态后恢复"就绪"
            self.master.after(3000, lambda: self.status_var.set("就绪"))
        
    def fix_apt_locks(self, ssh):
        """修复APT锁问题"""
        self.log_message("检查并修复APT锁问题...")
        
        # 检查是否有锁文件存在
        lock_files = [
            "/var/lib/apt/lists/lock",
            "/var/lib/dpkg/lock",
            "/var/cache/apt/archives/lock"
        ]
        
        for lock_file in lock_files:
            # 检查锁文件是否存在
            check_cmd = f"sudo [ -f {lock_file} ] && echo 'exists' || echo 'not exists'"
            result = self.run_ssh_command(ssh, check_cmd, ignore_errors=True)
            
            if 'exists' in result:
                self.log_message(f"发现锁文件: {lock_file}，尝试移除...")
                
                # 查找持有锁的进程
                self.run_ssh_command(ssh, f"sudo lsof {lock_file} || true", ignore_errors=True)
                
                # 强制移除锁文件
                self.run_ssh_command(ssh, f"sudo rm -f {lock_file}", ignore_errors=True)
                self.log_message(f"已移除锁文件: {lock_file}")
        
        # 检查是否有apt进程在运行
        self.log_message("检查是否有apt进程在运行...")
        ps_output = self.run_ssh_command(ssh, "ps aux | grep -i apt | grep -v grep || true", ignore_errors=True)
        if ps_output:
            self.log_message(f"发现运行的apt进程:\n{ps_output}", "warning")
            
            # 终止这些进程
            self.log_message("尝试终止apt进程...")
            self.run_ssh_command(ssh, "sudo killall apt apt-get || true", ignore_errors=True)
            self.run_ssh_command(ssh, "sudo pkill -f apt || true", ignore_errors=True)
            
            # 再次检查
            ps_output = self.run_ssh_command(ssh, "ps aux | grep -i apt | grep -v grep || true", ignore_errors=True)
            if not ps_output:
                self.log_message("成功终止所有apt进程")
            else:
                self.log_message("无法终止所有apt进程", "warning")
        
        # 重置dpkg状态
        self.log_message("重置dpkg状态...")
        self.run_ssh_command(ssh, "sudo dpkg --configure -a", ignore_errors=True)

    def show_progress_indicator(self):
        """显示进度指示器 - 简洁版"""
        if not self.progress_bar.winfo_viewable():
            self.progress_bar.configure(style="Green.Horizontal.TProgressbar")
            self.progress_bar.pack(side=tk.RIGHT, padx=10, fill=tk.Y, ipady=1)
            self.progress_bar.start()
            self.master.update()
            
    def hide_progress_indicator(self):
        """隐藏进度指示器 - 简洁版"""
        if self.progress_bar.winfo_viewable():
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.master.update()

    def install_dependencies(self, ssh):
        """安装必要依赖"""
        if self.stop_deployment_flag:
            raise Exception("部署已取消")
        
        self.log_message("正在安装必要依赖...")
        
        # 检测包管理器
        stdin, stdout, stderr = ssh.exec_command("command -v apt-get || command -v yum || echo unknown")
        pkg_manager = stdout.read().decode().strip()
        
        if "apt-get" in pkg_manager:
            self.log_message("使用APT安装依赖...")
            cmd = "sudo apt-get install -y curl wget unzip git socat nginx"
        elif "yum" in pkg_manager:
            self.log_message("使用YUM安装依赖...")           
            cmd = "sudo yum install -y curl wget unzip git socat nginx"
        else:
            raise Exception("不支持的包管理器，无法安装依赖")
        
        self.log_message(f"执行命令: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
        
        # 实时输出
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                output = stdout.channel.recv(1024).decode()
                if output:
                    self.log_message(output.strip(), "info")
            time.sleep(0.5)
        
        # 检查退出状态
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            error = stderr.read().decode().strip()
            if error:
                self.log_message(f"依赖安装出错: {error}", "error")
            raise Exception("依赖安装失败")
        
        self.log_message("依赖安装完成!")

    def configure_firewall(self, ssh, config):
        """配置防火墙 - 优先使用主流防火墙工具"""
        if self.stop_deployment_flag:
            return
            
        port = str(config["v2ray_port"])  # 确保端口是字符串类型以便比较
        self.log_message(f"配置防火墙规则，放行端口: {port}")
        
        try:
            # 1. 尝试使用firewalld（CentOS/RHEL）
            if self.firewalld_exists(ssh):
                self.log_message("检测到firewalld，使用firewalld配置防火墙")
                self.configure_firewalld(ssh, port)
                return
                
            # 2. 尝试使用ufw（Ubuntu/Debian）
            if self.ufw_exists(ssh):
                self.log_message("检测到ufw，使用ufw配置防火墙")
                self.configure_ufw(ssh, port)
                return
                
            # 3. 回退到iptables（通用）
            self.log_message("未检测到主流防火墙工具，使用iptables配置")
            self.configure_iptables(ssh, port)
            
        except Exception as e:
            self.log_message(f"防火墙配置出错: {str(e)}", "error")
            self.log_message("尝试使用最后手段: 禁用防火墙", "warning")
            self.disable_firewall(ssh)

    def firewalld_exists(self, ssh):
        """检查firewalld是否可用 - 添加命令存在性检查"""
        try:
            # 检查firewalld服务状态
            service_status = self.run_ssh_command(ssh, "systemctl is-active firewalld 2>/dev/null || echo 'inactive'", ignore_errors=True)
            # 检查firewall-cmd命令是否存在
            cmd_exists = self.run_ssh_command(ssh, "command -v firewall-cmd >/dev/null 2>&1 && echo 'exists' || echo 'not found'", ignore_errors=True)
            return "active" in service_status and "exists" in cmd_exists
        except:
            return False

    def ufw_exists(self, ssh):
        """检查ufw是否可用 - 添加命令存在性检查"""
        try:
            # 检查ufw服务状态
            service_status = self.run_ssh_command(ssh, "ufw status 2>/dev/null || echo 'inactive'", ignore_errors=True)
            # 检查ufw命令是否存在
            cmd_exists = self.run_ssh_command(ssh, "command -v ufw >/dev/null 2>&1 && echo 'exists' || echo 'not found'", ignore_errors=True)
            return ("active" in service_status or "Status: active" in service_status) and "exists" in cmd_exists
        except:
            return False

    def configure_firewalld(self, ssh, port):
        """使用firewalld配置防火墙"""
        try:
            # 添加HTTP/HTTPS服务（放行80/443）
            self.run_ssh_command(ssh, "sudo firewall-cmd --permanent --add-service=http")
            self.run_ssh_command(ssh, "sudo firewall-cmd --permanent --add-service=https")
            
            # 如果端口不是80或443，则额外放行
            if port not in ["80", "443"]:
                self.run_ssh_command(ssh, f"sudo firewall-cmd --permanent --add-port={port}/tcp")

            # 获取 Socks5 端口（如果启用）
            socks5_port = None
            if "enable_socks5" in config and config["enable_socks5"]:
                socks5_port = config["socks5_port"]
                
                # 在防火墙配置中添加 Socks5 端口
                if socks5_port:
                    self.log_message(f"放行 Socks5 端口: {socks5_port}")
                    
                    if self.firewalld_exists(ssh):
                        self.run_ssh_command(ssh, f"sudo firewall-cmd --permanent --add-port={socks5_port}/tcp")
                    elif self.ufw_exists(ssh):
                        self.run_ssh_command(ssh, f"sudo ufw allow {socks5_port}/tcp")
                    else:
                        self.run_ssh_command(ssh, f"sudo iptables -A INPUT -p tcp --dport {socks5_port} -j ACCEPT")
            
            # 重载防火墙
            self.run_ssh_command(ssh, "sudo firewall-cmd --reload")
            
            self.log_message("firewalld配置成功")
        except Exception as e:
            self.log_message(f"firewalld配置失败: {str(e)}", "warning")
            self.configure_iptables(ssh, port)
 
    def configure_ufw(self, ssh, port):
        """使用ufw配置防火墙"""
        try:
            # 确保ufw激活
            self.run_ssh_command(ssh, "sudo ufw --force enable")
            
            # 放行HTTP/HTTPS（80/443）
            self.run_ssh_command(ssh, "sudo ufw allow http")
            self.run_ssh_command(ssh, "sudo ufw allow https")
            
            # 如果端口不是80或443，则额外放行
            if port not in ["80", "443"]:
                self.run_ssh_command(ssh, f"sudo ufw allow {port}/tcp")

            # 获取 Socks5 端口（如果启用）
            socks5_port = None
            if "enable_socks5" in config and config["enable_socks5"]:
                socks5_port = config["socks5_port"]
                
                # 在防火墙配置中添加 Socks5 端口
                if socks5_port:
                    self.log_message(f"放行 Socks5 端口: {socks5_port}")
                    
                    if self.firewalld_exists(ssh):
                        self.run_ssh_command(ssh, f"sudo firewall-cmd --permanent --add-port={socks5_port}/tcp")
                    elif self.ufw_exists(ssh):
                        self.run_ssh_command(ssh, f"sudo ufw allow {socks5_port}/tcp")
                    else:
                        self.run_ssh_command(ssh, f"sudo iptables -A INPUT -p tcp --dport {socks5_port} -j ACCEPT")   

            # 重载规则
            self.run_ssh_command(ssh, "sudo ufw reload")
            
            self.log_message("ufw配置成功")
        except Exception as e:
            self.log_message(f"ufw配置失败: {str(e)}", "warning")
            self.configure_iptables(ssh, port)
 
    def configure_iptables(self, ssh, port):
        """使用iptables配置防火墙"""
        # 安装检查
        if not self.iptables_exists(ssh):
            self.log_message("iptables未安装，尝试安装...", "warning")
            self.install_iptables(ssh)

        try:
            # 清除可能存在的旧规则
            self.run_ssh_command(ssh, "sudo iptables -F", ignore_errors=True)
            
            # 设置默认策略
            self.run_ssh_command(ssh, "sudo iptables -P INPUT ACCEPT", ignore_errors=True)
            self.run_ssh_command(ssh, "sudo iptables -P FORWARD ACCEPT", ignore_errors=True)
            self.run_ssh_command(ssh, "sudo iptables -P OUTPUT ACCEPT", ignore_errors=True)
            
            # 放行80和443端口（无论用户端口是什么都放行）
            self.run_ssh_command(ssh, "sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT")
            self.run_ssh_command(ssh, "sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT")
            
            # 获取 Socks5 端口（如果启用）
            socks5_port = None
            if "enable_socks5" in config and config["enable_socks5"]:
                socks5_port = config["socks5_port"]
                
            # 在防火墙配置中添加 Socks5 端口
            if port not in ["80", "443"]:
                self.run_ssh_command(ssh, f"sudo iptables -A INPUT -p tcp --dport {port} -j ACCEPT")

                # 在防火墙配置中添加 Socks5 端口
                if socks5_port:
                    self.log_message(f"放行 Socks5 端口: {socks5_port}")
                    
                    if self.firewalld_exists(ssh):
                        self.run_ssh_command(ssh, f"sudo firewall-cmd --permanent --add-port={socks5_port}/tcp")
                    elif self.ufw_exists(ssh):
                        self.run_ssh_command(ssh, f"sudo ufw allow {socks5_port}/tcp")
                    else:
                        self.run_ssh_command(ssh, f"sudo iptables -A INPUT -p tcp --dport {socks5_port} -j ACCEPT")
            
            # 持久化规则 - 兼容不同系统
            # 检查系统类型
            os_type = self.run_ssh_command(ssh, "grep -E '^ID=' /etc/os-release | cut -d= -f2 | tr -d '\"'", ignore_errors=True).strip().lower()
            
            if os_type in ["debian", "ubuntu"]:
                # 添加环境变量避免交互提示
                install_cmd = (
                    "sudo DEBIAN_FRONTEND=noninteractive "
                    "apt-get install -y iptables-persistent"
                )
                self.run_ssh_command(ssh, install_cmd, ignore_errors=True)
                self.run_ssh_command(ssh, "sudo netfilter-persistent save", ignore_errors=True)
                self.log_message("使用iptables-persistent保存规则")
                
            elif os_type in ["centos", "rhel", "fedora"]:
                # CentOS/RHEL系统
                self.run_ssh_command(ssh, "sudo iptables-save > /etc/sysconfig/iptables", ignore_errors=True)
                self.run_ssh_command(ssh, "sudo service iptables save", ignore_errors=True)
                self.log_message("使用sysconfig保存规则")
                
            else:
                # 其他系统尝试通用方法
                self.run_ssh_command(ssh, "sudo iptables-save | sudo tee /etc/iptables/rules.v4", ignore_errors=True)
                self.log_message("使用通用方法保存规则")
            
            self.log_message("iptables配置成功")
        except Exception as e:
            self.log_message(f"iptables配置失败: {str(e)}", "error")
            raise Exception("防火墙配置失败")

    def iptables_exists(self, ssh):
        """检查iptables是否可用"""
        try:
            result = self.run_ssh_command(ssh, "command -v iptables", ignore_errors=True)
            return bool(result.strip())
        except:
            return False

    def install_iptables(self, ssh):
        """安装iptables"""
        try:
            # 检测包管理器
            pkg_manager = self.detect_package_manager(ssh)
            
            if pkg_manager == "apt":
                self.run_ssh_command(ssh, "sudo apt-get update -y", ignore_errors=True)
                self.run_ssh_command(ssh, "sudo apt-get install -y iptables", ignore_errors=True)
            elif pkg_manager == "yum":
                self.run_ssh_command(ssh, "sudo yum install -y iptables", ignore_errors=True)
            else:
                self.log_message("无法确定包管理器，跳过iptables安装", "warning")
        except Exception as e:
            self.log_message(f"安装iptables失败: {str(e)}", "warning")
    
    def detect_package_manager(self, ssh):
        """检测包管理器类型"""
        try:
            # 检查apt
            apt_check = self.run_ssh_command(ssh, "command -v apt-get", ignore_errors=True)
            if apt_check:
                return "apt"
            
            # 检查yum
            yum_check = self.run_ssh_command(ssh, "command -v yum", ignore_errors=True)
            if yum_check:
                return "yum"
            
            return "unknown"
        except:
            return "unknown"

    def disable_firewall(self, ssh):
        """禁用防火墙（最后手段）"""
        try:
            # 尝试禁用所有可能的防火墙服务
            services = ["firewalld", "ufw", "iptables"]
            for service in services:
                self.run_ssh_command(ssh, f"sudo systemctl stop {service} || true", ignore_errors=True)
                self.run_ssh_command(ssh, f"sudo systemctl disable {service} || true", ignore_errors=True)
            
            self.log_message("防火墙已禁用，请注意安全风险!", "warning")
        except Exception as e:
            self.log_message(f"禁用防火墙失败: {str(e)}", "error")
    
    def set_selinux(self, ssh):
        """设置SELinux - 增加兼容性检查"""
        if self.stop_deployment_flag:
            return
        
        self.log_message("配置SELinux...")
        try:
            # 先检查selinux是否安装
            selinux_installed = self.run_ssh_command(ssh, "command -v sestatus || echo 'not found'", ignore_errors=True)
            
            if "not found" in selinux_installed:
                self.log_message("SELinux未安装，跳过配置")
                return
                
            # 检查SELinux状态
            selinux_status = self.run_ssh_command(ssh, "sestatus | grep 'SELinux status' | awk '{print $3}'", ignore_errors=True)
            
            if "enabled" in selinux_status:
                mode = self.run_ssh_command(ssh, "sestatus | grep 'Current mode' | awk '{print $3}'", ignore_errors=True)
                if "enforcing" in mode:
                    self.log_message("SELinux处于强制模式，尝试设置为宽容模式")
                    self.run_ssh_command(ssh, "sudo setenforce 0", ignore_errors=True)
                    self.run_ssh_command(ssh, "sudo sed -i 's/SELINUX=enforcing/SELINUX=permissive/g' /etc/selinux/config", ignore_errors=True)
        except Exception as e:
            self.log_message(f"SELinux配置失败: {str(e)}，继续部署", "warning")
    
    def get_cert(self, ssh, config):
        """ 申请TLS证书 """
        if self.stop_deployment_flag:
            raise Exception("部署已取消")

        domain = config["full_domain"]
        self.log_message(f"准备为 {domain} 申请TLS证书...")

        # 创建证书目录
        commands = [
            "sudo mkdir -p /etc/v2ray",
            "sudo chmod -R 755 /etc/v2ray"
        ]
        for cmd in commands:
            self.run_ssh_command(ssh, cmd)

        # 检查证书是否已存在
        cert_file = f"/etc/v2ray/{domain}.pem"
        key_file = f"/etc/v2ray/{domain}.key"

        # 检查证书文件是否存在
        check_cert_cmd = f"sudo ls {cert_file} >/dev/null 2>&1"
        check_key_cmd = f"sudo ls {key_file} >/dev/null 2>&1"
        
        # 使用 try-except 检测命令执行结果
        try:
            self.run_ssh_command(ssh, check_cert_cmd, ignore_errors=False)
            self.run_ssh_command(ssh, check_key_cmd, ignore_errors=False)
            self.log_message(f"检测到已有证书: {cert_file} 和 {key_file}, 跳过申请流程")
            return cert_file, key_file
        except Exception:
            # 文件不存在会抛出异常，继续执行证书申请流程
            self.log_message("未检测到现有证书，开始申请新证书...")
            pass

        # 宝塔/原生Nginx 检测与停启
        is_baota = self.is_baota(ssh)
        if is_baota:
            self.log_message("检测到宝塔Nginx，使用宝塔命令控制Nginx进程")
            pre_hook = "nginx -s stop || { echo -n ''; }"
            post_hook = "nginx -c /www/server/nginx/conf/nginx.conf || { echo -n ''; }"
        else:
            pre_hook = "systemctl stop nginx"
            post_hook = "systemctl restart nginx"
        
        self.log_message("关闭Nginx以释放证书申请80/443端口")
        self.run_ssh_command(ssh, pre_hook, ignore_errors=True)

        # 安装acme.sh
        self.log_message("安装acme.sh证书工具...")
        self.run_ssh_command(ssh, "curl -sL https://get.acme.sh | sh -s email=webmaster@dimsn.com", timeout=120, ignore_errors=True)
        self.run_ssh_command(ssh, "~/.acme.sh/acme.sh --set-default-ca --server letsencrypt", ignore_errors=True)

        # 证书参数
        acme_opts = f" --pre-hook \"{pre_hook}\" --post-hook \"{post_hook}\""
        if config["enable_ipv6"]:
            acme_opts += " --listen-v6"
        acme_opts += " --insecure"
        self.log_message(f"acme.sh参数: {acme_opts}")

        # 正式申请
        cert_cmd = f"~/.acme.sh/acme.sh --issue -d {domain} --keylength ec-256 --standalone --debug 2 {acme_opts} --force"
        result = self.run_ssh_command(ssh, cert_cmd, timeout=600, ignore_errors=False)
        if ("Cert success" not in result) and ("Your cert is in" not in result):
            log_detail = self.run_ssh_command(ssh, f"cat ~/.acme.sh/acme.sh.log | tail -n 50", ignore_errors=True)
            raise Exception(f"证书申请失败，日志如下：\n{log_detail}")

        # 安装证书
        self.log_message("安装证书...")
        install_cmd = (
            f"sudo ~/.acme.sh/acme.sh --install-cert -d {domain} --ecc "
            f"--fullchain-file {cert_file} --key-file {key_file} "
            f"--reloadcmd \"{post_hook}\""
        )
        self.run_ssh_command(ssh, install_cmd, timeout=120)
        self.log_message(f"证书安装完成! 证书路径: {cert_file}, 密钥路径: {key_file}")

        # 启动Nginx
        self.run_ssh_command(ssh, post_hook, ignore_errors=True)
        self.log_message(f"Nginx已恢复启动")

        return cert_file, key_file

    def check_port_usage(self, ssh, ports):
        """检查端口占用情况但不释放"""
        for port in ports:
            cmd = f"ss -tuln | grep ':{port}\\b' || true"
            result = self.run_ssh_command(ssh, cmd, ignore_errors=True)
            if result:
                self.log_message(f"警告: 端口 {port} 被占用: {result}", "warning")
            else:
                self.log_message(f"端口 {port} 空闲")
    
    def install_v2ray(self, ssh, config):
        """安装V2Ray - 完全兼容脚本逻辑"""
        self.log_message("正在安装V2Ray...")

        self.run_ssh_command(ssh, "sudo systemctl stop v2ray || true", ignore_errors=True)

        # 确定V2Ray版本
        if "xtls" in config["protocol"]:
            new_ver = "v4.32.1"  # XTLS需要特定版本
        else:
            new_ver = "v5.37.0"   # 最新稳定版
    
        # 下载并安装
        arch = self.get_arch(ssh)
        download_url = f"https://github.com/v2fly/v2ray-core/releases/download/{new_ver}/v2ray-linux-{arch}.zip"
    
        commands = [
            "rm -rf /tmp/v2ray && mkdir -p /tmp/v2ray",
            f"curl -L -o /tmp/v2ray.zip {download_url}",
            "command -v unzip >/dev/null || { "
            "  [ -f /etc/redhat-release ] && yum install -y unzip >/dev/null 2>&1; "
            "  [ -f /etc/debian_version ] && apt update >/dev/null 2>&1 && apt install -y unzip >/dev/null 2>&1; "
            "}",
            "mkdir -p /etc/v2ray /var/log/v2ray",
            "unzip -o /tmp/v2ray.zip -d /tmp/v2ray",
            "mkdir -p /usr/bin/v2ray",
            "cp /tmp/v2ray/v2ray /usr/bin/v2ray/",
            "cp /tmp/v2ray/geo* /usr/bin/v2ray/",
            "chmod +x /usr/bin/v2ray/v2ray",
            "sudo chown -R nobody:nogroup /var/log/v2ray",
            "sudo chmod -R 755 /var/log/v2ray",
            "echo \"V2Ray 安装成功\""
        ]
    
        # XTLS需要额外文件
        if "xtls" in config["protocol"]:
            commands.append("cp /tmp/v2ray/v2ctl /usr/bin/v2ray/")
            commands.append("chmod +x /usr/bin/v2ray/v2ctl")
    
        # 修复：创建系统用户（兼容不同系统）
        commands.extend([
            # 检查用户是否已存在
            "id -u v2ray >/dev/null 2>&1 || { "
            # 尝试使用不同shell路径创建用户
            "  if [ -f /usr/sbin/nologin ]; then "
            "    sudo useradd --system --no-create-home --shell /usr/sbin/nologin v2ray; "
            "  elif [ -f /sbin/nologin ]; then "
            "    sudo useradd --system --no-create-home --shell /sbin/nologin v2ray; "
            "  else "
            "    sudo useradd --system --no-create-home --shell /bin/false v2ray; "
            "  fi "
            "}"
        ])

        for cmd in commands:
            # 建议：增加命令超时处理（需在run_ssh_command中实现）
            self.run_ssh_command(ssh, cmd)

        # 根据版本确定启动参数
        if new_ver == "v4.32.1":
            start_arg = "-config"
        else:
            start_arg = "run -c"
    
        # 创建服务文件（包含动态参数）
        service_file = f"""[Unit]
Description=V2ray Service
Documentation=https://www.v2fly.org/
After=network.target nss-lookup.target
[Service]
# If the version of systemd is 240 or above, then uncommenting Type=exec and commenting out Type=simple
#Type=exec
Type=simple
# This service runs as root. You may consider to run it as another user for security concerns.
# By uncommenting User=nobody and commenting out User=root, the service will run as user nobody.
# More discussion at https://github.com/v2ray/v2ray-core/issues/1011
User=root
#User=nobody
NoNewPrivileges=true
ExecStart=/usr/bin/v2ray/v2ray {start_arg} /etc/v2ray/config.json
Restart=on-failure
[Install]
WantedBy=multi-user.target"""
    
        # 上传服务文件
        sftp = ssh.open_sftp()
        with sftp.file("/etc/systemd/system/v2ray.service", "w") as f:
            f.write(service_file)
        self.run_ssh_command(ssh, "systemctl daemon-reload")
        self.run_ssh_command(ssh, "systemctl enable v2ray.service")
        self.log_message("V2Ray安装完成!")

    def get_arch(self, ssh):
        """获取系统架构 - 兼容脚本逻辑"""
        arch_map = {
            "i686": "32",
            "i386": "32",
            "x86_64": "64",
            "amd64": "64",
            "armv7": "arm32-v7a",
            "armv8": "arm64-v8a",
            "aarch64": "arm64-v8a"
        }
        
        arch_cmd = "uname -m"
        arch = self.run_ssh_command(ssh, arch_cmd).strip()
        return arch_map.get(arch, "64")  # 默认64位
    
    def configure_v2ray(self, ssh, config):
        """配置V2Ray"""
        if self.stop_deployment_flag:
            raise Exception("部署已取消")
        
        self.log_message("正在配置V2Ray...")
        
        # 生成V2Ray配置文件
        v2ray_config = self.generate_v2ray_config(config)
        
        # 上传配置文件到服务器专用目录
        self.log_message("上传V2Ray配置文件...")
        sftp = ssh.open_sftp()
        
        # 创建配置目录
        self.run_ssh_command(ssh, f"sudo mkdir -p /etc/v2ray")
        
        # 写入配置文件
        remote_path = f"/etc/v2ray/config.json"
        with sftp.file(remote_path, "w") as f:
            f.write(v2ray_config)
        
        # 设置权限
        self.run_ssh_command(ssh, f"sudo chmod 644 {remote_path}")
        
        self.log_message("V2Ray配置完成!")

    def generate_v2ray_config(self, config):
        """生成V2Ray配置文件 - 根据预设方案"""
        protocol = config["protocol"]
        domain = config["full_domain"]
        ws_path = config.get("ws_path", "/v2ray")
        uuid_val = config["uuid"]
        trojan_password = config.get("trojan_password", "")
        cert_file = config.get("tls_cert", "")
        key_file = config.get("tls_key", "")

        # 协议识别
        is_ws = any(proto in protocol for proto in ["ws", "ws_tls"])
        is_trojan = "trojan" in protocol
        
        # 确定端口和监听地址
        if is_ws:
            v2ray_port = self.internal_v2ray_port
            listen_address = "127.0.0.1"
        else:
            v2ray_port = config["v2ray_port"]
            listen_address = "0.0.0.0"
            
        # 基础配置
        base_config = {
            "log": {
                "access": "/var/log/v2ray/access.log",
                "error": "/var/log/v2ray/error.log",
                "loglevel": config.get("log_level", "warning")
            },
            "routing": {
                "domainStrategy": "AsIs",
                "rules": [
                    {
                        "type": "field",
                        "ip": ["geoip:private"],
                        "outboundTag": "blocked"
                    }
                ]
            },
            "inbounds": [],
            "outbounds": [
                {
                    "protocol": "freedom",
                    "tag": "direct",
                    "settings": {}
                },
                {
                    "protocol": "blackhole",
                    "tag": "blocked",
                    "settings": {}
                }
            ]
        }
        
        # 协议特定配置
        if protocol == "vmess_tcp_tls":
            base_config["inbounds"].append({
                "port": v2ray_port,
                "listen": listen_address,
                "protocol": "vmess",
                "settings": {
                    "clients": [{
                        "id": uuid_val,
                        "alterId": 0
                    }],
                    "disableInsecureEncryption": True
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "tls",
                    "tlsSettings": {
                        "certificates": [{
                            "certificateFile": cert_file,
                            "keyFile": key_file
                        }],
                        "serverName": domain,
                        "alpn": ["http/1.1", "h2"]
                    }
                }
            })
        
        elif protocol == "vmess_ws_tls":
            base_config["inbounds"].append({
                "port": v2ray_port,
                "listen": listen_address,
                "protocol": "vmess",
                "settings": {
                    "clients": [{
                        "id": uuid_val,
                        "level": 1,
                        "alterId": 0
                    }],
                    "disableInsecureEncryption": True
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {
                        "path": ws_path,
                        "headers": {
                            "Host": domain
                        }
                    }
                }
            })
        
        elif protocol == "vless_tcp_tls":
            base_config["inbounds"].append({
                "port": v2ray_port,
                "listen": listen_address,
                "protocol": "vless",
                "settings": {
                    "clients": [{
                        "id": uuid_val,
                        "level": 0
                    }],
                    "decryption": "none",
                    "fallbacks": [
                        {"alpn": "http/1.1", "dest": 80},
                        {"alpn": "h2", "dest": 81}
                    ]
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "tls",
                    "tlsSettings": {
                        "certificates": [{
                            "certificateFile": cert_file,
                            "keyFile": key_file
                        }],
                        "serverName": domain,
                        "alpn": ["http/1.1", "h2"]
                    }
                }
            })
        
        elif protocol == "vless_ws_tls":
            base_config["inbounds"].append({
                "port": v2ray_port,
                "listen": listen_address,
                "protocol": "vless",
                "settings": {
                    "clients": [{
                        "id": uuid_val,
                        "level": 0
                    }],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {
                        "path": ws_path,
                        "headers": {
                            "Host": domain
                        }
                    }
                }
            })
        
        elif protocol == "vless_tcp_xtls":
            base_config["inbounds"].append({
                "port": v2ray_port,
                "listen": listen_address,
                "protocol": "vless",
                "settings": {
                    "clients": [{
                        "id": uuid_val,
                        "flow": "xtls-rprx-direct",
                        "level": 0
                    }],
                    "decryption": "none",
                    "fallbacks": [
                        {"alpn": "http/1.1", "dest": 80},
                        {"alpn": "h2", "dest": 81}
                    ]
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "xtls",
                    "xtlsSettings": {
                        "certificates": [{
                            "certificateFile": cert_file,
                            "keyFile": key_file
                        }],
                        "serverName": domain,
                        "alpn": ["http/1.1", "h2"]
                    }
                }
            })
        
        elif protocol == "trojan_ws_tls":
            base_config["inbounds"].append({
                "port": v2ray_port,
                "listen": listen_address,
                "protocol": "trojan",
                "settings": {
                    "clients": [{
                        "password": trojan_password
                    }]
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {
                        "path": ws_path,
                        "headers": {
                            "Host": domain
                        }
                    }
                }
            })
        
        elif protocol == "trojango_ws_tls":
            base_config["inbounds"].append({
                "port": v2ray_port,
                "listen": listen_address,
                "protocol": "trojan",
                "settings": {
                    "clients": [{
                        "password": trojan_password
                    }],
                    "fallbacks": [
                        {"alpn": "http/1.1", "dest": 80},
                        {"alpn": "h2", "dest": 81}
                    ]
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "tls",
                    "tlsSettings": {
                        "certificates": [{
                            "certificateFile": cert_file,
                            "keyFile": key_file
                        }],
                        "serverName": domain,
                        "alpn": ["http/1.1", "h2"]
                    }
                }
            })

        # 添加 Socks5 入站配置
        if config.get("enable_socks5", False):
            socks5_config = {
                "port": config["socks5_port"],
                "listen": "0.0.0.0",  # 监听所有接口
                "protocol": "socks",
                "settings": {
                    "auth": config["socks5_auth"],
                    "accounts": [],
                    "udp": True,
                    "ip": "127.0.0.1"
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls"]
                }
            }
            
            # 如果启用了用户名/密码认证
            if config["socks5_auth"] == "password":
                socks5_config["settings"]["accounts"] = [
                    {
                        "user": config["socks5_username"],
                        "pass": config["socks5_password"]
                    }
                ]
            
            # 添加到入站列表
            base_config["inbounds"].append(socks5_config)

        # 合并自定义配置
        if config.get("custom_config"):
            try:
                custom = json.loads(config["custom_config"])
                base_config = self.deep_merge_configs(base_config, custom)
            except json.JSONDecodeError:
                self.log_message("自定义配置无效，使用默认配置", "warning")
        
        return json.dumps(base_config, indent=2)
    
    def deep_merge_configs(self, base, custom):
        """深度合并两个配置"""
        if isinstance(base, dict) and isinstance(custom, dict):
            for key in custom:
                if key in base:
                    if isinstance(base[key], dict) and isinstance(custom[key], dict):
                        base[key] = self.deep_merge_configs(base[key], custom[key])
                    elif isinstance(base[key], list) and isinstance(custom[key], list):
                        base[key].extend(custom[key])
                    else:
                        base[key] = custom[key]
                else:
                    base[key] = custom[key]
            return base
        return base
    
    def configure_nginx(self, ssh, config):
        """配置Nginx - 仅TLS协议需要"""
        if self.stop_deployment_flag:
            return

        # 仅TLS协议需要Nginx
        if "tls" not in config["protocol"] and "xtls" not in config["protocol"]:
            self.log_message("当前协议不需要Nginx，跳过配置")
            return
        
        self.log_message("正在配置Nginx...")
        
        try:
            # 创建必要目录
            self.run_ssh_command(ssh, "sudo mkdir -p /usr/share/nginx/html", ignore_errors=True)
            
            nginx_config = self.generate_nginx_config(config)
            
            # 生成Nginx配置文件名（与脚本一致）
            domain = config["full_domain"]
            config_name = f"{domain}.conf"
            
            # 宝塔面板特殊处理
            if self.is_baota(ssh):
                nginx_path = "/www/server/panel/vhost/nginx/"
            else:
                nginx_path = "/etc/nginx/conf.d/"
            
            remote_path = f"{nginx_path}{config_name}"

            # 清理可能存在的旧配置
            self.run_ssh_command(ssh, f"sudo rm -f /etc/nginx/conf.d/{config_name}", ignore_errors=True)
            
            # 上传Nginx配置
            sftp = ssh.open_sftp()
            with sftp.file(remote_path, "w") as f:
                f.write(nginx_config)
            
            # 设置权限
            self.run_ssh_command(ssh, f"sudo chmod 644 {remote_path}")
            
            # 如果不是宝塔面板，备份并创建主配置
            if not self.is_baota(ssh):
                self.log_message("备份并创建Nginx主配置...")
                self.run_ssh_command(ssh, "sudo [ -f /etc/nginx/nginx.conf.bak ] || sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak", ignore_errors=True)
                
                # 检查Nginx运行用户 - 使用新方法
                self.log_message("确定Nginx运行用户...")
                user = self.get_web_server_user(ssh)
                self.log_message(f"确定使用Nginx运行用户: {user}")

                nginx_main_conf = f"""user {user};
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

# Load dynamic modules. See /usr/share/doc/nginx/README.dynamic.
include /usr/share/nginx/modules/*.conf;

events {{
    worker_connections 1024;
}}

http {{
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;
    server_tokens off;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;
    gzip                on;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    # Load modular configuration files from the /etc/nginx/conf.d directory.
    # See http://nginx.org/en/docs/ngx_core_module.html#include
    # for more information.
    include /etc/nginx/conf.d/*.conf;
}}"""
                
                with sftp.file("/etc/nginx/nginx.conf", "w") as f:
                    f.write(nginx_main_conf)
            
            # 测试Nginx配置
            self.log_message("测试Nginx配置...")
            test_cmd = "sudo nginx -t 2>&1"  # 重定向stderr到stdout
            output = self.run_ssh_command(ssh, test_cmd, ignore_errors=True, use_pty=True)
            
            if "syntax is ok" not in output:
                self.log_message("Nginx配置测试失败!", "error")
                self.log_message(f"错误输出:\n{output}")
                self.diagnose_nginx(ssh, config)
                return False
                
            return True
        except Exception as e:
            # 详细错误处理
            self.log_message(f"Nginx配置失败: {str(e)}", "error")
            # 收集诊断信息
            self.diagnose_nginx(ssh, config)
            # 重新抛出异常以阻止后续操作
            raise Exception("Nginx配置失败，终止部署")

    def generate_nginx_config(self, config):
        """生成Nginx配置文件 - 使用脚本中的配置模板"""
        domain = config["full_domain"]
        port = self.server_port
        ws_path = config.get("ws_path", "/v2ray")
        protocol = config["protocol"]
        
        # 使用脚本中的证书路径
        cert_file = f"/etc/v2ray/{domain}.pem"
        key_file = f"/etc/v2ray/{domain}.key"

        # 获取用户选择的伪装网站
        proxy_type = config.get("proxy_type", "无")
        proxy_url = config.get("proxy_url", "")
        allow_spider = config.get("allow_spider", False)
        
        # 确定伪装网站URL
        action = ""
        if proxy_type == "静态网站(默认)":
            pass
        elif proxy_type == "小说站(随机)":
            # 随机选择一个小说站
            novel_sites = [
                "http://www.xbiquge.la",
                "http://www.biquge.info",
                "http://www.xxbiquge.com"
            ]
            proxy_url = random.choice(novel_sites)
            action = f"proxy_pass {proxy_url};\n        proxy_set_header Accept-Encoding '';\n        sub_filter \"{config['server_ip']}\" \"{domain}\";\n        sub_filter_once off;"
        elif proxy_type == "美女站":
            proxy_url = "http://www.kimiss.com"
            action = f"proxy_pass {proxy_url};\n        proxy_set_header Accept-Encoding '';\n        sub_filter \"{config['server_ip']}\" \"{domain}\";\n        sub_filter_once off;"
        elif proxy_type == "高清壁纸站":
            proxy_url = "https://www.wallpaperstock.net"
            action = f"proxy_pass {proxy_url};\n        proxy_set_header Accept-Encoding '';\n        sub_filter \"{config['server_ip']}\" \"{domain}\";\n        sub_filter_once off;"
        elif proxy_type == "自定义" and proxy_url:
            action = f"proxy_pass {proxy_url};\n        proxy_set_header Accept-Encoding '';\n        sub_filter \"{config['server_ip']}\" \"{domain}\";\n        sub_filter_once off;"
        
        # 机器人配置
        robot_config = ""
        if not allow_spider:
            robot_config = """
        location = /robots.txt {
            add_header Content-Type text/plain;
            return 200 'User-agent: *\\nDisallow: /';
        }"""

        # 根据协议类型生成不同的配置
        if "ws" in protocol:
            # WebSocket协议配置
            return f"""
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};
    return 301 https://\$server_name:{port}\$request_uri;
}}
server {{
    listen       {port} ssl http2;
    listen       [::]:{port} ssl http2;
    server_name {domain};
    charset utf-8;
    
    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers TLS13-AES-256-GCM-SHA384:TLS13-CHACHA20-POLY1305-SHA256:TLS13-AES-128-GCM-SHA256:TLS13-AES-128-CCM-8-SHA256:TLS13-AES-128-CCM-SHA256:EECDH+CHACHA20:EECDH+AES128:RSA+AES128:EECDH+AES256:RSA+AES256:EECDH+3DES:RSA+3DES:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache builtin:1000 shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_buffer_size 1400;
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_session_tickets off;
    ssl_certificate {cert_file};
    ssl_certificate_key {key_file};

    root /usr/share/nginx/html;
    location / {{
        {action}
    }}
{robot_config}
    
    # WebSocket路径
    location {ws_path} {{
        proxy_redirect off;
        proxy_pass http://127.0.0.1:{self.internal_v2ray_port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }}
}}
"""
        else:
            # 非WebSocket协议配置 (TCP+TLS/XTLS, Trojan)
            # 注意：这里不需要SSL配置，因为TLS由V2Ray直接处理
            return f"""
server {{
    listen 80;
    listen [::]:80;
    listen 81 http2;
    server_name {domain};
    root /usr/share/nginx/html;
    location / {{
        {action}
    }}
{robot_config}
}}
"""
    
    def is_baota(self, ssh):
        """检查是否安装了宝塔面板"""
        try:
            # 检查宝塔面板的安装标志
            result = self.run_ssh_command(ssh, "[ -f /www/server/panel/BT-Panel ] && echo 'true' || echo 'false'")
            return result.strip() == "true"
        except:
            return False

    def start_services(self, ssh, config):
        """启动服务"""
        if self.stop_deployment_flag:
            return
        
        self.log_message("正在启动服务...")
        
        nginx_configured = False
        v2ray_commands = []  # 专门存放V2Ray启动命令
        
        # 如果配置了Nginx，则启动Nginx
        if "tls" in config["protocol"] or "xtls" in config["protocol"]:
            nginx_configured = self.configure_nginx(ssh, config)
            if nginx_configured:
                commands = [
                    "sudo systemctl enable nginx",
                    "sudo systemctl restart nginx"
                ]
                self.log_message("Nginx启动成功")
        
        # 启动V2Ray
        v2ray_commands = [
            "sudo systemctl enable v2ray",
            "sudo systemctl restart v2ray"
        ]
        
        for cmd in commands:
            self.run_ssh_command(ssh, cmd)
        
        # 检查服务状态
        self.log_message("验证服务状态...")
        
        # 检查V2Ray状态
        v2ray_status = self.run_ssh_command(ssh, "sudo systemctl is-active v2ray", ignore_errors=True)
        if "active" in v2ray_status:
            self.log_message("V2Ray启动成功!")
        else:
            logs = self.run_ssh_command(ssh, "sudo journalctl -u v2ray -n 50 --no-pager")
            raise Exception(f"V2Ray启动失败:\n{logs}")
        
        self.log_message("服务启动成功!")

    def get_web_server_user(self, ssh):
        """确定Web服务器用户的名称"""
        # 首先检查Web服务器进程使用的用户
        web_user_cmd = "ps -eo user,comm | grep -E 'nginx|apache' | grep -v grep | awk '{print $1}' | sort | uniq | head -1"
        user = self.run_ssh_command(ssh, web_user_cmd, ignore_errors=True).strip()
        
        # 如果找到用户则返回
        if user and user != "root" and len(user) > 0:
            return user
        
        # 否则尝试查找系统上预定义的用户名
        users_to_check = ["nginx", "www-data", "apache", "httpd", "http", "www", "wwwrun"]
        for u in users_to_check:
            check_cmd = f"id {u} >/dev/null 2>&1 && echo exists"
            if "exists" in self.run_ssh_command(ssh, check_cmd, ignore_errors=True):
                return u
        
        # 检查Nginx配置文件中的用户设置
        nginx_user_cmd = "grep -E '^user' /etc/nginx/nginx.conf 2>/dev/null | awk '{print $2}' | tr -d ';'"
        nginx_user = self.run_ssh_command(ssh, nginx_user_cmd, ignore_errors=True).strip()
        if nginx_user and len(nginx_user) > 0:
            return nginx_user
        
        # 检查Apache配置中的用户设置
        apache_user_cmd = "grep -E '^User' /etc/apache2/apache2.conf 2>/dev/null | awk '{print $2}'"
        apache_user = self.run_ssh_command(ssh, apache_user_cmd, ignore_errors=True).strip()
        if apache_user and len(apache_user) > 0:
            return apache_user
        
        # 如果都找不到，安全回退到nobody
        return "nobody"

    def diagnose_nginx(self, ssh, config):
        """诊断Nginx问题"""
        self.log_message("执行Nginx深度诊断...")
        
        # 1. 检查端口占用
        ports = [80, 443, config.get('v2ray_port', 443)]
        for port in ports:
            self.log_message(f"检查端口 {port} 占用情况...")
            
            # 使用通用方法检测端口占用
            cmd = f"sudo lsof -i:{port} || sudo netstat -tuln | grep ':{port}\\>'"
            port_info = self.run_ssh_command(ssh, cmd, ignore_errors=True)
            
            if port_info:
                self.log_message(f"端口 {port} 被占用:\n{port_info}")
            else:
                self.log_message(f"端口 {port} 未被占用")
        
        # 2. 检查配置权限
        perm_cmd = "ls -l /etc/nginx/conf.d/ | grep " + config["full_domain"]
        perm_result = self.run_ssh_command(ssh, perm_cmd, ignore_errors=True)
        self.log_message(f"配置文件权限: {perm_result}")
        
        # 3. 检查Nginx状态
        status = self.run_ssh_command(ssh, "sudo systemctl status nginx --no-pager", ignore_errors=True)
        self.log_message(f"Nginx服务状态:\n{status}")
        
        # 4. 测试配置加载
        load_test = self.run_ssh_command(ssh, "sudo nginx -T 2>&1 | grep -A 20 'server {'", ignore_errors=True)
        self.log_message(f"配置加载测试:\n{load_test[:500]}...")  # 只显示前500字符

    def enable_bbr_acceleration(self, ssh):
        """开启BBR加速"""
        if self.stop_deployment_flag:
            return
        
        self.log_message("开启BBR加速...")
        try:
            # 检查是否已开启BBR
            bbr_status = self.run_ssh_command(ssh, "sysctl net.ipv4.tcp_congestion_control", ignore_errors=True)
            if "bbr" in bbr_status:
                self.log_message("BBR已启用")
                return
            
            # 开启BBR
            commands = [
                "echo 'net.core.default_qdisc=fq' | sudo tee -a /etc/sysctl.conf",
                "echo 'net.ipv4.tcp_congestion_control=bbr' | sudo tee -a /etc/sysctl.conf",
                "sudo sysctl -p"
            ]
            
            for cmd in commands:
                self.run_ssh_command(ssh, cmd, ignore_errors=True)
            
            # 验证BBR状态
            bbr_status = self.run_ssh_command(ssh, "sysctl net.ipv4.tcp_congestion_control", ignore_errors=True)
            if "bbr" in bbr_status:
                self.log_message("BBR加速已成功启用!")
            else:
                self.log_message("BBR加速启用失败", "warning")
        except Exception as e:
            self.log_message(f"启用BBR加速时出错: {str(e)}", "warning")

    def test_v2ray_connection(self, config):
        """测试V2Ray连接"""
        if self.stop_deployment_flag:
            return
        
        domain = config["full_domain"]
        error_msg = [] 
        
        # 根据协议类型选择测试端口
        if config["protocol"] in ["vmess_ws_tls", "vless_ws_tls", "trojan_ws_tls"]:
            port = 443
        else:
            port = config["v2ray_port"]

        self.log_message(f"正在测试 {domain}:{port} 的连接性...")
        
        try:
            # 先解析域名
            try:
                ip_address = socket.gethostbyname(domain)
                self.log_message(f"域名解析成功: {domain} -> {ip_address}")
            except socket.gaierror:
                self.log_message(f"域名解析失败: {domain}", "warning")
                # 等待5秒再试一次
                time.sleep(20)
                try:
                    ip_address = socket.gethostbyname(domain)
                    self.log_message(f"重试解析成功: {domain} -> {ip_address}")
                except socket.gaierror as e:
                    raise Exception(f"域名解析失败: {domain}") from e

            # 测试TCP连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((domain, port))
            sock.close()
            
            if result == 0:
                self.log_message("TCP连接测试成功!", "success")
            else:
                raise Exception(f"TCP连接失败 (错误代码: {result})")
            
            # 如果使用TLS，测试TLS握手
            if "tls" in config["protocol"] or "xtls" in config["protocol"]:
                # 创建更灵活的SSL上下文
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                context.check_hostname = False  # 不强制验证主机名
                context.verify_mode = ssl.CERT_NONE  # 不验证证书（仅用于测试）
                
                try:
                    with socket.create_connection((domain, port), timeout=10) as sock:
                        with context.wrap_socket(sock, server_hostname=domain) as ssock:
                            # 即使不验证证书，也可以获取证书信息
                            cert = ssock.getpeercert()
                            self.log_message(f"TLS握手成功! 证书主题: {cert.get('subject', '')}", "success")
                            
                            # 检查证书是否过期
                            if 'notAfter' in cert:
                                not_after = dict(x[0] for x in cert['notAfter'])
                                exp_date = f"{not_after.get('year')}-{not_after.get('month')}-{not_after.get('day')}"
                                self.log_message(f"证书有效期至: {exp_date}")
                            else:
                                self.log_message("证书信息中未找到有效期字段", "info")

                except ssl.SSLCertVerificationError as e:
                    # 证书验证失败，但仍然连接成功
                    self.log_message(f"TLS握手成功但证书验证失败: {str(e)}", "warning")
                except Exception as e:
                    raise Exception(f"TLS握手失败: {str(e)}")
        
        except Exception as e:
            # 提供详细诊断信息
            error_msg = [
                f"连接测试失败: {str(e)}",
                "可能原因:",
                "1. 服务器防火墙未开放端口",
                "2. Cloudflare代理设置不正确",
                "3. V2Ray服务未运行",
                "4. 域名解析问题",
                "5. 本地网络限制",
                "6. 证书问题（如果是自签名证书）"
            ]

            # 完整的错误信息列表
            error_info = "\n".join(error_msg)
            self.log_message(error_info, "error")
            raise Exception(error_info)
    
    def show_connection_info(self, config):
        """显示连接信息"""
        if self.stop_deployment_flag:
            return
        
        protocol = config["protocol"]
        domain = config["full_domain"]
        port = config["v2ray_port"]
        uuid = config["uuid"]
        ws_path = config.get("ws_path", "/v2ray")
        trojan_password = config.get("trojan_password", "")
        
        # 创建新窗口显示连接信息
        info_window = tk.Toplevel(self.master)
        info_window.title("V2Ray 连接信息")
        info_window.geometry("800x600")
        self.center_window(info_window)
        
        # 添加标签
        ttk.Label(info_window, text="V2Ray 部署成功!", font=('微软雅黑', 14, 'bold')).pack(pady=10)
        
        # 创建文本框显示配置
        info_frame = ttk.Frame(info_window)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        info_text = scrolledtext.ScrolledText(
            info_frame, 
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加配置信息
        info_text.insert(tk.END, "服务器信息:\n", "title")
        info_text.insert(tk.END, f"地址: {domain}\n")
        info_text.insert(tk.END, f"端口: {port}\n")
        info_text.insert(tk.END, f"协议方案: {protocol}\n")
        
        if "vmess" in protocol or "vless" in protocol:
            info_text.insert(tk.END, f"UUID: {uuid}\n")
        if "trojan" in protocol:
            info_text.insert(tk.END, f"密码: {trojan_password}\n")
        if "ws" in protocol:
            info_text.insert(tk.END, f"WebSocket路径: {ws_path}\n")
        
        info_text.insert(tk.END, f"Cloudflare代理: {'开启' if config['cf_proxy'] else '关闭'}\n")
        info_text.insert(tk.END, "\n")
        
        # 添加客户端配置
        info_text.insert(tk.END, "客户端配置:\n", "title")
        
        if "vmess" in protocol:
            # VMess配置
            v2rayn_config = {
                "v": "2",
                "ps": f"{domain}",
                "add": domain,
                "port": port,
                "id": uuid,
                "aid": "0",
                "scy": "auto",
                "net": "tcp" if "tcp" in protocol else "ws",
                "type": "none",
                "host": domain,
                "path": ws_path if "ws" in protocol else "",
                "tls": "tls" if "tls" in protocol else "none",
                "sni": domain,
                "alpn": ""
            }
            vmess_url = "vmess://" + base64.b64encode(json.dumps(v2rayn_config).encode()).decode()
            info_text.insert(tk.END, f"VMess 链接:\n{vmess_url}\n\n")
        
        if "vless" in protocol:
            # VLESS配置
            vless_url = f"vless://{uuid}@{domain}:{port}?encryption=none"
            if "tls" in protocol:
                vless_url += "&security=tls"
            if "xtls" in protocol:
                vless_url += "&security=xtls&flow=xtls-rprx-direct"
            if "ws" in protocol:
                vless_url += f"&type=ws&path={ws_path}"
            vless_url += f"#VLESS_{domain}"
            info_text.insert(tk.END, f"VLESS 链接:\n{vless_url}\n\n")
        
        if "trojan" in protocol:
            # Trojan配置
            trojan_url = f"trojan://{trojan_password}@{domain}:{port}"
            if "ws" in protocol:
                trojan_url += f"?type=ws&path={ws_path}"
            trojan_url += f"#Trojan_{domain}"
            info_text.insert(tk.END, f"Trojan 链接:\n{trojan_url}\n\n")

        # 添加 Socks5 配置信息
        if config.get("enable_socks5", False):
            info_text.insert(tk.END, "\nSocks5 配置:\n", "title")
            info_text.insert(tk.END, f"地址: {config['server_ip']}\n")
            info_text.insert(tk.END, f"端口: {config['socks5_port']}\n")
            if config["socks5_auth"] == "password":
                info_text.insert(tk.END, f"认证: 用户名/密码\n")
                info_text.insert(tk.END, f"用户名: {config['socks5_username']}\n")
                info_text.insert(tk.END, f"密码: {config['socks5_password']}\n")
            else:
                info_text.insert(tk.END, f"认证: 无\n")
            info_text.insert(tk.END, "\n")
            # 生成 Socks5 连接字符串
            if config["socks5_auth"] == "password":
                socks5_url = f"socks5://{config['socks5_username']}:{config['socks5_password']}@{config['server_ip']}:{config['socks5_port']}"
            else:
                socks5_url = f"socks5://{config['server_ip']}:{config['socks5_port']}"
            info_text.insert(tk.END, f"Socks5 链接:\n{socks5_url}\n\n")
        
        # 添加故障排除指南
        info_text.insert(tk.END, "故障排除指南:\n", "title")
        info_text.insert(tk.END, "1. 检查服务器防火墙: sudo ufw status\n")
        info_text.insert(tk.END, "2. 检查V2Ray状态: sudo systemctl status v2ray\n")
        info_text.insert(tk.END, "3. 检查端口监听: sudo netstat -tuln | grep ':{port}'\n")
        info_text.insert(tk.END, "4. 本地测试: curl -v http://localhost:{port}\n")
        info_text.insert(tk.END, "5. 检查Cloudflare DNS设置\n")
        info_text.insert(tk.END, "6. 暂时禁用服务器防火墙测试\n")
        
        info_text.config(state=tk.DISABLED)
        
        # 添加按钮
        button_frame = ttk.Frame(info_window)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="复制配置",
            command=lambda: self.copy_to_clipboard(info_text.get("1.0", tk.END)),
            style="Primary.TButton"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="关闭",
            command=info_window.destroy,
            style="Secondary.TButton"
        ).pack(side=tk.LEFT, padx=5)
    
    def on_task_double_click(self, event):
        """处理任务列表的双击事件"""
        # 获取选中的项
        selected_items = self.task_tree.selection()
        if not selected_items:
            return
        
        # 只处理第一个选中的项
        item = selected_items[0]
        values = self.task_tree.item(item, "values")
        
        # 检查任务状态
        if len(values) >= 8 and values[7] == "部署完成":
            # 获取保存的配置
            config = self.task_configs.get(item)
            if config:
                self.show_connection_info(config)
            else:
                self.log_message("未找到该任务的配置信息", "warning")
        else:
            self.log_message("该任务尚未部署完成，无法查看配置", "info")

    def run_ssh_command(self, ssh, command, timeout=60, ignore_errors=False, use_pty=False):
        """执行SSH命令并返回输出"""
        self.log_message(f"执行命令: {command}")
        
        try:
            # 使用正确的参数调用exec_command
            stdin, stdout, stderr = ssh.exec_command(command, timeout=timeout, get_pty=use_pty)
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            
            if output:
                self.log_message(output)
            
            if exit_status != 0:
                if error:
                    self.log_message(f"错误: {error}", "error")
                
                if not ignore_errors:
                    raise Exception(f"命令执行失败: {command} (退出状态: {exit_status})")
            
            return output
        except Exception as e:
            error_msg = f"执行命令时出错: {command}\n{str(e)}"
            if not ignore_errors:
                raise Exception(error_msg)
            return ""
    
    def run_ssh_command_with_retry(self, ssh, command, timeout=60, retries=3, delay=5):
        """带重试机制的SSH命令执行"""
        attempt = 1
        while attempt <= retries:
            try:
                return self.run_ssh_command(ssh, command, timeout)
            except Exception as e:
                if attempt < retries:
                    self.log_message(f"命令执行失败，将在 {delay} 秒后重试 ({attempt}/{retries})...", "warning")
                    time.sleep(delay)
                    attempt += 1
                else:
                    raise e
    
    def load_default_config(self):
        """加载默认V2Ray配置"""
        default_config = """{
  "log": {
    "access": "/var/log/v2ray/access.log",
    "error": "/var/log/v2ray/error.log",
    "loglevel": "warning"
  },
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {
        "type": "field",
        "ip": [
          "geoip:private"
        ],
        "outboundTag": "block"
      }
    ]
  },
  "outbounds": [
    {
      "protocol": "freedom",
      "tag": "direct"
    },
    {
      "protocol": "blackhole",
      "tag": "block"
    }
  ]
}"""
        
        self.custom_config_text.delete(1.0, tk.END)
        self.custom_config_text.insert(tk.END, default_config)
        self.log_message("已加载默认配置")
    
    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        try:
            self.master.clipboard_clear()
            self.master.clipboard_append(text)
            self.log_message("配置已复制到剪贴板")
        except Exception as e:
            self.log_message(f"复制配置失败: {str(e)}", "error")
    
    def on_close(self):
        """处理窗口关闭事件"""
        # 如果有任务正在运行，显示警告对话框
        if self.running_tasks > 0:
            # 创建居中对话框
            self.center_window(self.master)
            if not messagebox.askokcancel(
                "警告", 
                "当前有任务正在执行，确定要退出吗？",
                parent=self.master
            ):
                return  # 用户取消退出
        
        # 停止部署线程
        self.stop_deployment_flag = True
        
        # 关闭主窗口
        self.master.destroy()
        sys.exit(0)

def main():
    """程序主入口，添加更健壮的异常处理"""
    # 忽略 libpng 相关警告
    import os
    import warnings
    os.environ['PYTHONWARNINGS'] = 'ignore::Image.DecompressionBombWarning'
    warnings.filterwarnings("ignore", category=UserWarning, module="PIL")
    
    try:
        # 检查管理员权限
        if platform.system() == "Windows" and not is_admin():
            run_as_admin()
            return

        # 尝试导入必需的库
        try:
            import paramiko
            import requests
        except ImportError:
            # 如果导入失败，则进行安装
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            install_libraries()
            return
        
        # 提前创建应用数据目录
        app_data_dir = os.path.join(os.path.expanduser("~"), ".v2raydeployer")
        os.makedirs(app_data_dir, exist_ok=True)
        
        root = tk.Tk()
        # 设置UI缩放因子（解决高DPI显示问题）
        if platform.system() == "Windows":
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)

        # 设置程序标题
        root.title("V2Ray 一键部署工具")
        
        # 设置程序图标
        try:
            # 获取当前脚本所在目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            resources_dir = os.path.join(script_dir, "resources")
            icon_path = os.path.join(resources_dir, "v2ray_icon.ico")
            
            # 确保资源目录存在
            os.makedirs(resources_dir, exist_ok=True)
            
            # 检查图标文件是否存在
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
                print(f"已设置程序图标: {icon_path}")
            else:
                # 如果图标不存在，尝试创建默认图标
                print(f"图标文件不存在: {icon_path}")
                # 这里可以添加创建默认图标的代码，但为了简洁省略
        except Exception as e:
            print(f"设置图标失败: {str(e)}")
        
        # 显示启动画面
        splash = tk.Toplevel(root)
        splash.title("启动中")
        splash.geometry("300x150")
        # 设置启动画面图标
        try:
            if 'icon_path' in locals() and os.path.exists(icon_path):
                splash.iconbitmap(icon_path)
        except:
            pass
        
        splash_label = tk.Label(splash, text="正在初始化 V2Ray 部署工具...", font=("微软雅黑", 12))
        splash_label.pack(pady=20)
        progress = ttk.Progressbar(splash, mode="indeterminate")
        progress.pack(fill=tk.X, padx=20, pady=10)
        progress.start()
        root.update()
        
        app = V2RayDeployer(root)
        
        # 关闭启动画面
        splash.destroy()
        root.deiconify()  # 确保主窗口显示
        
        # 主窗口居中显示
        app.center_window(root)
        
        # 自动加载当前域名的配置
        app.auto_load_config()
        
        root.mainloop()
    except Exception as e:
        error_msg = f"程序启动时发生未捕获的异常: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        # 尝试显示错误对话框
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "致命错误", 
                f"程序启动失败: {str(e)}\n\n"
                "可能的原因:\n"
                "1. 缺少依赖库 (paramiko, requests)\n"
                "2. 网络连接问题\n"
                "3. 系统权限不足\n\n"
                "请检查日志获取详细信息。"
            )
        except:
            print("无法创建错误对话框:", error_msg)
        sys.exit(1)

if __name__ == "__main__":
    # 检查Windows管理员权限
    if platform.system() == "Windows" and not is_admin():
        run_as_admin()
    
    # 确保必需库已安装
    try:
        import paramiko
        import requests
    except ImportError:
        root = tk.Tk()
        root.withdraw()
        install_libraries()
        sys.exit(0)
    
    # 创建主窗口
    root = tk.Tk()
    if platform.system() == "Windows":
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    
    root.title("V2Ray 一键部署工具")
    
    # 设置程序图标
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "v2ray_icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except:
        pass
    
    # 显示启动画面
    splash = tk.Toplevel(root)
    splash.title("启动中")
    splash.geometry("300x150")
    try:
        if 'icon_path' in locals() and os.path.exists(icon_path):
            splash.iconbitmap(icon_path)
    except:
        pass
    
    splash_label = tk.Label(splash, text="正在初始化 V2Ray 部署工具...", font=("微软雅黑", 12))
    splash_label.pack(pady=20)
    progress = ttk.Progressbar(splash, mode="indeterminate")
    progress.pack(fill=tk.X, padx=20, pady=10)
    progress.start()
    root.update()
    
    # 创建主应用
    app = V2RayDeployer(root)
    
    # 关闭启动画面
    splash.destroy()
    root.deiconify()
    
    # 自动加载配置
    app.auto_load_config()
    
    # 启动主循环
    root.mainloop()
