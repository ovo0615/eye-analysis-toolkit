# -*- coding: utf-8 -*-
"""
QuickEye Analyzer GUI
參考開源程式碼來源：https://github.com/linmingchih/smart_design
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import os
import threading
try:
    from pyaedt import Circuit
except ImportError:
    from ansys.aedt.core import Circuit

def calculate_time(*args):
    try:
        gbps = float(speed_var.get())
        if gbps <= 0:
            raise ValueError
        ui = 1.0 / gbps * 1e-9 # UI in seconds
        # 計算合理的上升/下降時間 (預設 20% UI)
        trise = ui * 0.2
        
        ui_ps = ui * 1e12
        trise_ps = trise * 1e12
        
        ui_var.set(f"{ui_ps:.1f} ps")
        trise_var.set(f"{trise_ps:.1f} ps")
        
        return ui, trise
    except ValueError:
        ui_var.set("-")
        trise_var.set("-")
        return None, None

def browse_s4p():
    mode = mode_var.get() if 'mode_var' in globals() else "Differential"
    if mode == "Single-Ended":
        file_types = [("S2P files", "*.s2p"), ("All files", "*.*")]
        title_str = "選擇 S2P 檔案"
    else:
        file_types = [("S4P files", "*.s4p"), ("All files", "*.*")]
        title_str = "選擇 S4P 檔案"
        
    filepath = filedialog.askopenfilename(title=title_str, filetypes=file_types)
    if filepath:
        s4p_var.set(filepath)

def browse_outdir():
    dirpath = filedialog.askdirectory(title="選擇輸出資料夾")
    if dirpath:
        outdir_var.set(dirpath)

def run_analysis():
    s4p_path = s4p_var.get()
    outdir = outdir_var.get()
    version = version_var.get()
    
    if not os.path.exists(s4p_path):
        messagebox.showerror("錯誤", "找不到S參數檔案！")
        return
    if not os.path.exists(outdir):
        messagebox.showerror("錯誤", "找不到輸出資料夾！")
        return
        
    try:
        n_stages = int(stages_var.get())
        if n_stages < 1:
            raise ValueError
    except ValueError:
        messagebox.showerror("錯誤", "級數必須是正整數！")
        return
        
    ui, trise = calculate_time()
    if ui is None:
        messagebox.showerror("錯誤", "請輸入有效的傳輸速度！")
        return
        
    mode_str = mode_var.get()
    
    run_btn.config(state=tk.DISABLED)
    status_var.set("分析執行中，請稍候...")
    
    def task():
        circuit = None
        try:
            # 建立時間戳記避免覆蓋，並綁定為新的專案路徑
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            aedt_path = os.path.join(outdir, f'QuickEye_Analysis_{timestamp}.aedt')
            
            # 啟動 PyAEDT Circuit (強制新建專案，避免舊設計被覆蓋)
            circuit = Circuit(project=aedt_path, version=version, non_graphical=False)
            
            # 相容新舊版本的元件建立方式
            if hasattr(circuit.modeler, 'schematic') and hasattr(circuit.modeler.schematic, 'create_component'):
                cmp = circuit.modeler.schematic
            else:
                cmp = circuit.modeler.components
                
            # 使用原生 API 建立 Touchstone S 參數元件
            ts_list = []
            for i in range(n_stages):
                ts = cmp.create_touchstone_component(s4p_path)
                ts_list.append(ts)
                
            # 自動串接 S 參數元件 (使用 Page Port)
            if mode_str == "Differential":
                for i in range(n_stages - 1):
                    pname1 = f'net_p{i}'
                    pname2 = f'net_n{i}'
                    circuit.modeler.schematic.create_page_port(pname1, ts_list[i].pins[2].location)
                    circuit.modeler.schematic.create_page_port(pname2, ts_list[i].pins[3].location)
                    circuit.modeler.schematic.create_page_port(pname1, ts_list[i+1].pins[0].location)
                    circuit.modeler.schematic.create_page_port(pname2, ts_list[i+1].pins[1].location)
    
                circuit.modeler.schematic.create_page_port('Port1', ts_list[0].pins[0].location)
                circuit.modeler.schematic.create_page_port('Port2', ts_list[0].pins[1].location)
                circuit.modeler.schematic.create_page_port('Port3', ts_list[-1].pins[2].location)
                circuit.modeler.schematic.create_page_port('Port4', ts_list[-1].pins[3].location)
                    
                eye_source = cmp.create_component(component_library='Independent Sources', component_name='EYESOURCE_DIFF')
                eye_probe = cmp.create_component(component_library='Probes', component_name='EYEPROBE_DIFF')
                
                circuit.modeler.schematic.create_page_port('Port1', eye_source.pins[1].location)
                circuit.modeler.schematic.create_page_port('Port2', eye_source.pins[0].location)
                circuit.modeler.schematic.create_page_port('Port3', eye_probe.pins[1].location)
                circuit.modeler.schematic.create_page_port('Port4', eye_probe.pins[0].location)
            else:
                for i in range(n_stages - 1):
                    pname = f'net_p{i}'
                    circuit.modeler.schematic.create_page_port(pname, ts_list[i].pins[1].location)
                    circuit.modeler.schematic.create_page_port(pname, ts_list[i+1].pins[0].location)
                    
                circuit.modeler.schematic.create_page_port('Port1', ts_list[0].pins[0].location)
                circuit.modeler.schematic.create_page_port('Port2', ts_list[-1].pins[1].location)
                
                eye_source = cmp.create_component(component_library='Independent Sources', component_name='EYESOURCE')
                eye_probe = cmp.create_component(component_library='Probes', component_name='EYEPROBE')
                
                circuit.modeler.schematic.create_page_port('Port1', eye_source.pins[0].location)
                circuit.modeler.schematic.create_page_port('Port2', eye_probe.pins[0].location)
                
            if hasattr(eye_source, 'set_property'):
                eye_source.set_property('UIorBPSValue', f'{ui}s')
                eye_source.set_property('trise', f'{trise}s')
                eye_source.set_property('tfall', f'{trise}s')
            else:
                eye_source.parameters['UIorBPSValue'] = f'{ui}s'
                eye_source.parameters['trise'] = f'{trise}s'
                eye_source.parameters['tfall'] = f'{trise}s'
                
            setup = circuit.create_setup(setup_type="NexximQuickEye")

            # 執行模擬
            circuit.analyze()
            
            # 產生眼圖
            plot = circuit.post.create_statistical_eye_plot(setup.name, 'AEYEPROBE(required)', '')
            
            # 匯出 JPG
            plot_name = plot.name if hasattr(plot, 'name') else plot
            circuit.post.export_report_to_jpg(outdir, plot_name)
            
            # 將產生的 JPG 加上時間戳記重新命名
            jpg_orig = os.path.join(outdir, f"{plot_name}.jpg")
            jpg_new = os.path.join(outdir, f"{plot_name}_{timestamp}.jpg")
            if os.path.exists(jpg_orig):
                if os.path.exists(jpg_new):
                    os.remove(jpg_new)
                os.rename(jpg_orig, jpg_new)
            
            # 儲存 AEDT 專案 (已在初始化時綁定路徑)
            circuit.save_project()
            
            circuit.release_desktop(False, False)
            
            root.after(0, lambda: status_var.set("分析完成！"))
            root.after(0, lambda: messagebox.showinfo("成功", f"分析完成！結果已儲存至：\n{outdir}"))
        except Exception as e:
            if circuit:
                try:
                    circuit.release_desktop(False, False)
                except:
                    pass
            root.after(0, lambda e=e: messagebox.showerror("錯誤", f"執行失敗：\n{str(e)}"))
            root.after(0, lambda: status_var.set("分析失敗"))
        finally:
            root.after(0, lambda: run_btn.config(state=tk.NORMAL))

    threading.Thread(target=task, daemon=True).start()


# --- GUI 介面 ---
root = tk.Tk()
root.title("QuickEye 自動化眼圖分析工具")
root.configure(bg='white')
root.resizable(False, False)

style = ttk.Style()
style.theme_use('clam')
# 設定全局字體，依據使用者規則
style.configure('.', font=('微軟正黑體', 12), background='white')
style.configure('TLabel', font=('微軟正黑體', 12), background='white')
style.configure('TButton', font=('微軟正黑體', 12, 'bold'))
style.configure('TRadiobutton', font=('微軟正黑體', 12), background='white')
style.configure('TEntry', font=('Calibri', 12))
style.configure('TCombobox', font=('Calibri', 12))
style.configure('TFrame', background='white')

# 變數初始化
s4p_var = tk.StringVar()
outdir_var = tk.StringVar()
speed_var = tk.StringVar(value="10") # 預設 10 Gbps
stages_var = tk.StringVar(value="1") # 預設 1 級
ui_var = tk.StringVar()
trise_var = tk.StringVar()
status_var = tk.StringVar(value="等待執行...")
version_var = tk.StringVar(value="2026.1")
mode_var = tk.StringVar(value="Differential")

def update_canvas(*args):
    canvas.delete("all")
    mode = mode_var.get()
    if mode == "Differential":
        canvas.create_rectangle(120, 20, 220, 80, fill="#f0f0f0", outline="#333333", width=2)
        canvas.create_text(170, 50, text="S4P 模型\n(Touchstone)", font=("微軟正黑體", 11, "bold"), justify=tk.CENTER)
        canvas.create_line(40, 35, 120, 35, arrow=tk.LAST, width=2, fill="#0055a4")
        canvas.create_text(75, 20, text="Port 1 (In+)", fill="#0055a4", font=("Calibri", 12, "bold"))
        canvas.create_line(40, 65, 120, 65, arrow=tk.LAST, width=2, fill="#0055a4")
        canvas.create_text(75, 80, text="Port 2 (In-)", fill="#0055a4", font=("Calibri", 12, "bold"))
        canvas.create_line(220, 35, 300, 35, arrow=tk.LAST, width=2, fill="#2b7a0b")
        canvas.create_text(265, 20, text="Port 3 (Out+)", fill="#2b7a0b", font=("Calibri", 12, "bold"))
        canvas.create_line(220, 65, 300, 65, arrow=tk.LAST, width=2, fill="#2b7a0b")
        canvas.create_text(265, 80, text="Port 4 (Out-)", fill="#2b7a0b", font=("Calibri", 12, "bold"))
    else:
        canvas.create_rectangle(120, 30, 220, 70, fill="#f0f0f0", outline="#333333", width=2)
        canvas.create_text(170, 50, text="S2P 模型\n(Touchstone)", font=("微軟正黑體", 11, "bold"), justify=tk.CENTER)
        canvas.create_line(40, 50, 120, 50, arrow=tk.LAST, width=2, fill="#0055a4")
        canvas.create_text(75, 35, text="Port 1 (In)", fill="#0055a4", font=("Calibri", 12, "bold"))
        canvas.create_line(220, 50, 300, 50, arrow=tk.LAST, width=2, fill="#2b7a0b")
        canvas.create_text(265, 35, text="Port 2 (Out)", fill="#2b7a0b", font=("Calibri", 12, "bold"))

mode_var.trace_add("write", update_canvas)

speed_var.trace_add("write", calculate_time)

frame = ttk.Frame(root, padding=20)
frame.pack(fill=tk.BOTH, expand=True)

# AEDT版本選擇
ttk.Label(frame, text="AEDT 版本:").grid(row=0, column=0, sticky="e", pady=5, padx=5)
version_cb = ttk.Combobox(frame, textvariable=version_var, values=["2023.1", "2023.2", "2024.1", "2024.2", "2025.1", "2025.2", "2026.1"], width=10)
version_cb.grid(row=0, column=1, sticky="w", pady=5)

# S參數路徑 (.s2p / .s4p)
ttk.Label(frame, text="S參數檔案 (.sNp):").grid(row=1, column=0, sticky="e", pady=5, padx=5)
ttk.Entry(frame, textvariable=s4p_var, width=45).grid(row=1, column=1, pady=5)
ttk.Button(frame, text="瀏覽...", command=browse_s4p).grid(row=1, column=2, padx=5, pady=5)

# 訊號模式
ttk.Label(frame, text="訊號模式:").grid(row=2, column=0, sticky="e", pady=5, padx=5)
mode_frame = ttk.Frame(frame)
mode_frame.grid(row=2, column=1, sticky="w", pady=5)
ttk.Radiobutton(mode_frame, text="差動 (Differential)", variable=mode_var, value="Differential").pack(side=tk.LEFT, padx=5)
ttk.Radiobutton(mode_frame, text="單端 (Single-Ended)", variable=mode_var, value="Single-Ended").pack(side=tk.LEFT, padx=5)

# 參數設定
ttk.Label(frame, text="傳輸速度 (Gbps):").grid(row=3, column=0, sticky="e", pady=5, padx=5)
ttk.Entry(frame, textvariable=speed_var, width=15).grid(row=3, column=1, sticky="w", pady=5)

ttk.Label(frame, text="串接級數 (1~N):").grid(row=4, column=0, sticky="e", pady=5, padx=5)
ttk.Entry(frame, textvariable=stages_var, width=15).grid(row=4, column=1, sticky="w", pady=5)

# 動態計算顯示
ttk.Label(frame, text="計算出 UI 寬度:").grid(row=5, column=0, sticky="e", pady=5, padx=5)
ttk.Label(frame, textvariable=ui_var, foreground="blue").grid(row=5, column=1, sticky="w", pady=5)

ttk.Label(frame, text="上升/下降時間 (20% UI):").grid(row=6, column=0, sticky="e", pady=5, padx=5)
ttk.Label(frame, textvariable=trise_var, foreground="blue").grid(row=6, column=1, sticky="w", pady=5)

# 輸出目錄
ttk.Label(frame, text="輸出資料夾:").grid(row=7, column=0, sticky="e", pady=5, padx=5)
ttk.Entry(frame, textvariable=outdir_var, width=45).grid(row=7, column=1, pady=5)
ttk.Button(frame, text="瀏覽...", command=browse_outdir).grid(row=7, column=2, padx=5, pady=5)

# S4P Port Definition Diagram
canvas_frame = ttk.Frame(frame)
canvas_frame.grid(row=8, column=0, columnspan=3, pady=5)
ttk.Label(canvas_frame, text="⚠ 請確認您的 S 參數埠號 (Port) 定義符合以下工具預設排列：", foreground="#d9534f", font=("微軟正黑體", 11, "bold")).pack(pady=2)

canvas = tk.Canvas(canvas_frame, width=340, height=110, bg='white', highlightthickness=1, highlightbackground="#cccccc")
canvas.pack()

# 狀態與版權
ttk.Label(frame, textvariable=status_var, foreground="green").grid(row=9, column=0, columnspan=3, pady=5)

run_btn = ttk.Button(frame, text="執行分析", command=run_analysis)
run_btn.grid(row=10, column=0, columnspan=3, pady=5, ipadx=10, ipady=5)

copyright_text = "參考開源程式碼來源：https://github.com/linmingchih/smart_design"
ttk.Label(frame, text=copyright_text, foreground="gray", justify="center", font=("微軟正黑體", 10)).grid(row=11, column=0, columnspan=3, pady=5)

calculate_time()
update_canvas()
root.mainloop()
