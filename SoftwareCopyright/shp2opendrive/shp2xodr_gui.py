import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
import json
from pathlib import Path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from shp2xodr import ChainOfResponsibilityConverter
class ShpToOpenDriveGUI:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.create_widgets()
        self.converter = None
    def setup_window(self):
        self.root.title("Shapefile转OpenDrive格式转换器")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        self.colors = {
            'bg': '#f5f5f7',           # 浅灰背景
            'card_bg': '#ffffff',       # 白色卡片背景
            'border': '#d2d2d7',       # 边框颜色
            'text': '#1d1d1f',         # 深色文字
            'secondary_text': '#86868b', # 次要文字
            'accent': '#007aff',        # 蓝色强调色
            'success': '#34c759',       # 成功绿色
            'error': '#ff3b30'          # 错误红色
        }
        self.root.configure(bg=self.colors['bg'])
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        title_label = ttk.Label(main_frame, text="Shapefile转OpenDrive格式转换器", 
                               font=('SF Pro Display', 24, 'bold'))
        title_label.grid(row=0, column=0, pady=(0, 30), sticky=tk.W)
        self.create_file_selection_frame(main_frame, 1)
        self.create_config_frame(main_frame, 2)
        self.create_control_frame(main_frame, 3)
        self.create_log_frame(main_frame, 4)
        main_frame.rowconfigure(4, weight=1)
    def create_file_selection_frame(self, parent, row):
        file_frame = ttk.LabelFrame(parent, text="文件选择", padding="15")
        file_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        file_frame.columnconfigure(1, weight=1)
        ttk.Label(file_frame, text="输入Shapefile:").grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.input_var = tk.StringVar()
        input_entry = ttk.Entry(file_frame, textvariable=self.input_var, width=50)
        input_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 10), pady=(0, 10))
        ttk.Button(file_frame, text="浏览", command=self.browse_input_file).grid(row=0, column=2, pady=(0, 10))
        ttk.Label(file_frame, text="输出文件:").grid(row=1, column=0, sticky=tk.W)
        self.output_var = tk.StringVar()
        output_entry = ttk.Entry(file_frame, textvariable=self.output_var, width=50)
        output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 10))
        ttk.Button(file_frame, text="浏览", command=self.browse_output_file).grid(row=1, column=2)
    def create_config_frame(self, parent, row):
        config_frame = ttk.LabelFrame(parent, text="转换参数", padding="15")
        config_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        config_frame.columnconfigure(1, weight=1)
        ttk.Label(config_frame, text="几何拟合容差 (米):").grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.tolerance_var = tk.DoubleVar(value=1.0)
        tolerance_spin = ttk.Spinbox(config_frame, from_=0.1, to=10.0, increment=0.1, 
                                   textvariable=self.tolerance_var, width=10)
        tolerance_spin.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 10))
        ttk.Label(config_frame, text="最小道路长度 (米):").grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        self.min_length_var = tk.DoubleVar(value=1.0)
        min_length_spin = ttk.Spinbox(config_frame, from_=0.1, to=100.0, increment=0.1, 
                                    textvariable=self.min_length_var, width=10)
        min_length_spin.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 10))
        self.use_arcs_var = tk.BooleanVar()
        arcs_check = ttk.Checkbutton(config_frame, text="使用圆弧拟合", variable=self.use_arcs_var)
        arcs_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        ttk.Label(config_frame, text="配置文件 (可选):").grid(row=3, column=0, sticky=tk.W)
        self.config_var = tk.StringVar()
        config_entry = ttk.Entry(config_frame, textvariable=self.config_var, width=40)
        config_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(10, 10))
        ttk.Button(config_frame, text="浏览", command=self.browse_config_file).grid(row=3, column=2)
    def create_control_frame(self, parent, row):
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        control_frame.columnconfigure(0, weight=1)
        self.convert_button = ttk.Button(control_frame, text="开始转换", 
                                       command=self.start_conversion, style='Accent.TButton')
        self.convert_button.grid(row=0, column=0, pady=10)
        self.progress_var = tk.StringVar(value="准备就绪")
        progress_label = ttk.Label(control_frame, textvariable=self.progress_var)
        progress_label.grid(row=1, column=0, pady=(0, 10))
        self.progress_bar = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress_bar.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    def create_log_frame(self, parent, row):
        log_frame = ttk.LabelFrame(parent, text="转换日志", padding="15")
        log_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80, 
                                                 wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        ttk.Button(log_frame, text="清除日志", command=self.clear_log).grid(row=1, column=0, pady=(10, 0))
    def browse_input_file(self):
        filename = filedialog.askopenfilename(
            title="选择输入Shapefile",
            filetypes=[("Shapefile", "*.shp"), ("所有文件", "*.*")]
        )
        if filename:
            self.input_var.set(filename)
            if not self.output_var.get():
                output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(filename))), "output")
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, 
                                         os.path.splitext(os.path.basename(filename))[0] + ".xodr")
                self.output_var.set(output_file)
    def browse_output_file(self):
        filename = filedialog.asksaveasfilename(
            title="选择输出文件",
            defaultextension=".xodr",
            filetypes=[("OpenDrive文件", "*.xodr"), ("所有文件", "*.*")]
        )
        if filename:
            self.output_var.set(filename)
    def browse_config_file(self):
        filename = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if filename:
            self.config_var.set(filename)
    def log_message(self, message, level="INFO"):
        self.log_text.config(state=tk.NORMAL)
        timestamp = tk.datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    def validate_inputs(self):
        if not self.input_var.get():
            messagebox.showerror("错误", "请选择输入Shapefile文件")
            return False
        if not os.path.exists(self.input_var.get()):
            messagebox.showerror("错误", "输入文件不存在")
            return False
        if not self.output_var.get():
            messagebox.showerror("错误", "请指定输出文件路径")
            return False
        output_dir = os.path.dirname(self.output_var.get())
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                messagebox.showerror("错误", f"无法创建输出目录: {e}")
                return False
        return True
    def start_conversion(self):
        if not self.validate_inputs():
            return
        self.convert_button.config(state=tk.DISABLED)
        self.progress_bar.start()
        self.progress_var.set("转换中...")
        conversion_thread = threading.Thread(target=self.run_conversion)
        conversion_thread.daemon = True
        conversion_thread.start()
    def run_conversion(self):
        try:
            self.log_message("开始转换过程")
            config = {
                'geometry_tolerance': self.tolerance_var.get(),
                'min_road_length': self.min_length_var.get(),
                'use_arc_fitting': self.use_arcs_var.get()
            }
            if self.config_var.get() and os.path.exists(self.config_var.get()):
                try:
                    with open(self.config_var.get(), 'r', encoding='utf-8') as f:
                        file_config = json.load(f)
                        config.update(file_config)
                    self.log_message(f"已加载配置文件: {self.config_var.get()}")
                except Exception as e:
                    self.log_message(f"配置文件加载失败: {e}", "WARNING")
            self.converter = ChainOfResponsibilityConverter(config)
            success = self.converter.convert(
                self.input_var.get(),
                self.output_var.get()
            )
            self.root.after(0, self.conversion_completed, success)
        except Exception as e:
            self.root.after(0, self.conversion_error, str(e))
    def conversion_completed(self, success):
        self.progress_bar.stop()
        self.convert_button.config(state=tk.NORMAL)
        if success:
            self.progress_var.set("转换成功完成")
            self.log_message("转换成功完成！", "SUCCESS")
            if self.converter and hasattr(self.converter, 'conversion_stats'):
                stats = self.converter.conversion_stats
                self.log_message(f"输入道路数: {stats.get('input_roads', 0)}")
                self.log_message(f"输出道路数: {stats.get('output_roads', 0)}")
                self.log_message(f"总长度: {stats.get('total_length', 0):.2f} 米")
                self.log_message(f"转换时间: {stats.get('conversion_time', 0):.2f} 秒")
            messagebox.showinfo("成功", "转换成功完成！")
        else:
            self.progress_var.set("转换失败")
            self.log_message("转换失败！", "ERROR")
            messagebox.showerror("失败", "转换失败，请检查日志获取详细信息")
    def conversion_error(self, error_message):
        self.progress_bar.stop()
        self.convert_button.config(state=tk.NORMAL)
        self.progress_var.set("转换出错")
        self.log_message(f"转换出错: {error_message}", "ERROR")
        messagebox.showerror("错误", f"转换过程出错: {error_message}")
def main():
    import datetime
    tk.datetime = datetime
    root = tk.Tk()
    app = ShpToOpenDriveGUI(root)
    root.mainloop()
if __name__ == '__main__':
    main()