#!/usr/bin/env python3
"""
PixivUtil GUI - A graphical interface for PixivUtil2
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import json
import configparser
from pathlib import Path
from queue import Queue, Empty

class PixivUtilGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PixivUtil2 GUI")
        self.root.geometry("900x700")
        
        # Configuration
        self.config_path = Path("config.ini")
        self.pixivutil_path = Path("PixivUtil2.py")
        self.process = None
        self.output_queue = Queue()
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        self.create_widgets()
        self.load_config()
        
    def create_widgets(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Download Tab
        download_frame = ttk.Frame(notebook)
        notebook.add(download_frame, text='Download')
        self.create_download_tab(download_frame)
        
        # Settings Tab
        settings_frame = ttk.Frame(notebook)
        notebook.add(settings_frame, text='Settings')
        self.create_settings_tab(settings_frame)
        
        # Database Tab
        db_frame = ttk.Frame(notebook)
        notebook.add(db_frame, text='Database')
        self.create_database_tab(db_frame)
        
        # Output Tab
        output_frame = ttk.Frame(notebook)
        notebook.add(output_frame, text='Output')
        self.create_output_tab(output_frame)
        
    def create_download_tab(self, parent):
        # Download mode selection
        mode_frame = ttk.LabelFrame(parent, text="Download Mode", padding=10)
        mode_frame.pack(fill='x', padx=10, pady=5)
        
        self.download_mode = tk.StringVar(value="1")
        modes = [
            ("1", "Download by Member ID"),
            ("2", "Download by Image ID"),
            ("3", "Download by Tags"),
            ("4", "Download from List"),
            ("5", "Download User Bookmarks"),
            ("6", "Download Image Bookmarks"),
            ("7", "Download from Tags List"),
            ("8", "Download New Illustrations"),
            ("9", "Download by Title/Caption"),
            ("f1", "FANBOX: Supported Artists"),
            ("f2", "FANBOX: By Creator ID"),
            ("f4", "FANBOX: Followed Artists"),
        ]
        
        row = 0
        col = 0
        for value, text in modes:
            ttk.Radiobutton(mode_frame, text=text, variable=self.download_mode, 
                          value=value).grid(row=row, column=col, sticky='w', padx=5, pady=2)
            col += 1
            if col > 1:
                col = 0
                row += 1
        
        # Input frame
        input_frame = ttk.LabelFrame(parent, text="Input", padding=10)
        input_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(input_frame, text="Enter ID(s) / Tags / File Path:").pack(anchor='w')
        self.input_entry = ttk.Entry(input_frame, width=70)
        self.input_entry.pack(fill='x', pady=5)
        
        ttk.Button(input_frame, text="Browse File", 
                  command=self.browse_file).pack(side='left', padx=5)
        
        # Options frame
        options_frame = ttk.LabelFrame(parent, text="Options", padding=10)
        options_frame.pack(fill='x', padx=10, pady=5)
        
        self.include_sketch = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Include Pixiv Sketch", 
                       variable=self.include_sketch).grid(row=0, column=0, sticky='w', padx=5)
        
        self.use_wildcard = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Use Wildcard for Tags", 
                       variable=self.use_wildcard).grid(row=0, column=1, sticky='w', padx=5)
        
        ttk.Label(options_frame, text="Start Page:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.start_page = ttk.Entry(options_frame, width=10)
        self.start_page.grid(row=1, column=1, sticky='w', padx=5)
        self.start_page.insert(0, "1")
        
        ttk.Label(options_frame, text="End Page:").grid(row=1, column=2, sticky='w', padx=5, pady=5)
        self.end_page = ttk.Entry(options_frame, width=10)
        self.end_page.grid(row=1, column=3, sticky='w', padx=5)
        self.end_page.insert(0, "0")
        
        # Control buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="Start Download", 
                                    command=self.start_download, style='Accent.TButton')
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop Download", 
                                   command=self.stop_download, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        # Progress
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding=10)
        progress_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready", foreground='green')
        self.status_label.pack(anchor='w')
        
    def create_settings_tab(self, parent):
        # Create canvas with scrollbar
        canvas = tk.Canvas(parent)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Authentication
        auth_frame = ttk.LabelFrame(scrollable_frame, text="Authentication", padding=10)
        auth_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(auth_frame, text="Username/Email:").grid(row=0, column=0, sticky='w', pady=5)
        self.username_entry = ttk.Entry(auth_frame, width=40)
        self.username_entry.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        
        ttk.Label(auth_frame, text="Password:").grid(row=1, column=0, sticky='w', pady=5)
        self.password_entry = ttk.Entry(auth_frame, width=40, show='*')
        self.password_entry.grid(row=1, column=1, sticky='ew', pady=5, padx=5)
        
        ttk.Label(auth_frame, text="Cookie (PHPSESSID):").grid(row=2, column=0, sticky='w', pady=5)
        self.cookie_entry = ttk.Entry(auth_frame, width=40)
        self.cookie_entry.grid(row=2, column=1, sticky='ew', pady=5, padx=5)
        
        # Download Settings
        dl_frame = ttk.LabelFrame(scrollable_frame, text="Download Settings", padding=10)
        dl_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(dl_frame, text="Root Directory:").grid(row=0, column=0, sticky='w', pady=5)
        self.root_dir = ttk.Entry(dl_frame, width=40)
        self.root_dir.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        ttk.Button(dl_frame, text="Browse", command=self.browse_root_dir).grid(row=0, column=2, padx=5)
        
        ttk.Label(dl_frame, text="Number of Pages (0=all):").grid(row=1, column=0, sticky='w', pady=5)
        self.num_pages = ttk.Entry(dl_frame, width=10)
        self.num_pages.grid(row=1, column=1, sticky='w', pady=5, padx=5)
        
        self.r18_mode = tk.BooleanVar()
        ttk.Checkbutton(dl_frame, text="R18 Mode Only", 
                       variable=self.r18_mode).grid(row=2, column=0, columnspan=2, sticky='w', pady=5)
        
        self.download_avatar = tk.BooleanVar()
        ttk.Checkbutton(dl_frame, text="Download Avatar", 
                       variable=self.download_avatar).grid(row=3, column=0, columnspan=2, sticky='w', pady=5)
        
        self.verify_image = tk.BooleanVar()
        ttk.Checkbutton(dl_frame, text="Verify Images", 
                       variable=self.verify_image).grid(row=4, column=0, columnspan=2, sticky='w', pady=5)
        
        self.overwrite = tk.BooleanVar()
        ttk.Checkbutton(dl_frame, text="Overwrite Existing Files", 
                       variable=self.overwrite).grid(row=5, column=0, columnspan=2, sticky='w', pady=5)
        
        # Filename Format
        filename_frame = ttk.LabelFrame(scrollable_frame, text="Filename Format", padding=10)
        filename_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(filename_frame, text="Format:").grid(row=0, column=0, sticky='w', pady=5)
        self.filename_format = ttk.Entry(filename_frame, width=50)
        self.filename_format.grid(row=0, column=1, sticky='ew', pady=5, padx=5)
        
        ttk.Label(filename_frame, text="Example: %artist% - %title%", 
                 foreground='gray').grid(row=1, column=1, sticky='w', padx=5)
        
        # Network Settings
        network_frame = ttk.LabelFrame(scrollable_frame, text="Network", padding=10)
        network_frame.pack(fill='x', padx=10, pady=5)
        
        self.use_proxy = tk.BooleanVar()
        ttk.Checkbutton(network_frame, text="Use Proxy", 
                       variable=self.use_proxy).grid(row=0, column=0, sticky='w', pady=5)
        
        ttk.Label(network_frame, text="Proxy Address:").grid(row=1, column=0, sticky='w', pady=5)
        self.proxy_addr = ttk.Entry(network_frame, width=40)
        self.proxy_addr.grid(row=1, column=1, sticky='ew', pady=5, padx=5)
        
        ttk.Label(network_frame, text="Timeout (seconds):").grid(row=2, column=0, sticky='w', pady=5)
        self.timeout = ttk.Entry(network_frame, width=10)
        self.timeout.grid(row=2, column=1, sticky='w', pady=5, padx=5)
        
        # Save button
        ttk.Button(scrollable_frame, text="Save Settings", 
                  command=self.save_config).pack(pady=10)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_database_tab(self, parent):
        db_frame = ttk.LabelFrame(parent, text="Database Management", padding=10)
        db_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        operations = [
            ("Show all members", "d", "1"),
            ("Show all downloaded images", "d", "2"),
            ("Export list (member_id only)", "d", "3"),
            ("Export list (detailed)", "d", "4"),
            ("Show member by last downloaded", "d", "6"),
            ("Show image by image_id", "d", "7"),
            ("Show member by member_id", "d", "8"),
            ("Delete member by member_id", "d", "12"),
            ("Delete image by image_id", "d", "13"),
            ("Clean up database", "d", "19"),
        ]
        
        for i, (text, cmd, subcmd) in enumerate(operations):
            btn = ttk.Button(db_frame, text=text, 
                           command=lambda c=cmd, s=subcmd: self.run_db_operation(c, s))
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky='ew')
        
    def create_output_tab(self, parent):
        output_frame = ttk.Frame(parent)
        output_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        ttk.Label(output_frame, text="Console Output:", 
                 font=('Arial', 10, 'bold')).pack(anchor='w', pady=5)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, 
                                                     height=25, bg='#1e1e1e', 
                                                     fg='#d4d4d4', insertbackground='white')
        self.output_text.pack(fill='both', expand=True)
        
        button_frame = ttk.Frame(output_frame)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(button_frame, text="Clear Output", 
                  command=self.clear_output).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Save Log", 
                  command=self.save_log).pack(side='left', padx=5)
        
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filename)
    
    def browse_root_dir(self):
        dirname = filedialog.askdirectory(title="Select Root Directory")
        if dirname:
            self.root_dir.delete(0, tk.END)
            self.root_dir.insert(0, dirname)
    
    def load_config(self):
        if not self.config_path.exists():
            return
        
        # Disable interpolation to allow % characters in values
        config = configparser.ConfigParser(interpolation=None)
        config.read(self.config_path, encoding='utf-8')
        
        try:
            # Authentication
            if 'Authentication' in config:
                self.username_entry.insert(0, config['Authentication'].get('username', ''))
                self.password_entry.insert(0, config['Authentication'].get('password', ''))
                self.cookie_entry.insert(0, config['Authentication'].get('cookie', ''))
            
            # Settings
            if 'Settings' in config:
                self.root_dir.insert(0, config['Settings'].get('rootdirectory', './'))
                self.download_avatar.set(config['Settings'].getboolean('downloadavatar', False))
                self.verify_image.set(config['Settings'].getboolean('verifyimage', False))
            
            # Pixiv
            if 'Pixiv' in config:
                self.num_pages.insert(0, config['Pixiv'].get('numberofpage', '0'))
                self.r18_mode.set(config['Pixiv'].getboolean('r18mode', False))
            
            # Download Control
            if 'DownloadControl' in config:
                self.overwrite.set(config['DownloadControl'].getboolean('overwrite', False))
            
            # Filename
            if 'Filename' in config:
                self.filename_format.insert(0, config['Filename'].get('filenameformat', 
                                                                      '%artist% - %title%'))
            
            # Network
            if 'Network' in config:
                self.use_proxy.set(config['Network'].getboolean('useproxy', False))
                self.proxy_addr.insert(0, config['Network'].get('proxyaddress', ''))
                self.timeout.insert(0, config['Network'].get('timeout', '60'))
                
        except Exception as e:
            self.log_output(f"Error loading config: {str(e)}")
    
    def save_config(self):
        config = configparser.ConfigParser()
        # Disable interpolation to allow % characters in values
        config = configparser.ConfigParser(interpolation=None)
        
        # Read existing config
        if self.config_path.exists():
            config.read(self.config_path)
        
        # Update sections
        if 'Authentication' not in config:
            config['Authentication'] = {}
        config['Authentication']['username'] = self.username_entry.get()
        config['Authentication']['password'] = self.password_entry.get()
        config['Authentication']['cookie'] = self.cookie_entry.get()
        
        if 'Settings' not in config:
            config['Settings'] = {}
        config['Settings']['rootdirectory'] = self.root_dir.get()
        config['Settings']['downloadavatar'] = str(self.download_avatar.get())
        config['Settings']['verifyimage'] = str(self.verify_image.get())
        
        if 'Pixiv' not in config:
            config['Pixiv'] = {}
        config['Pixiv']['numberofpage'] = self.num_pages.get()
        config['Pixiv']['r18mode'] = str(self.r18_mode.get())
        
        if 'DownloadControl' not in config:
            config['DownloadControl'] = {}
        config['DownloadControl']['overwrite'] = str(self.overwrite.get())
        
        if 'Filename' not in config:
            config['Filename'] = {}
        config['Filename']['filenameformat'] = self.filename_format.get()
        
        if 'Network' not in config:
            config['Network'] = {}
        config['Network']['useproxy'] = str(self.use_proxy.get())
        config['Network']['proxyaddress'] = self.proxy_addr.get()
        config['Network']['timeout'] = self.timeout.get()
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            config.write(f)
        
        messagebox.showinfo("Success", "Settings saved successfully!")
        self.log_output("Settings saved to config.ini")
    
    def start_download(self):
        if not self.pixivutil_path.exists():
            messagebox.showerror("Error", 
                               f"PixivUtil2.py not found at {self.pixivutil_path}\n"
                               "Please place this GUI in the same folder as PixivUtil2.py")
            return
        
        mode = self.download_mode.get()
        input_val = self.input_entry.get().strip()
        
        if not input_val and mode not in ['5', '8', 'f1', 'f4']:
            messagebox.showwarning("Warning", "Please enter required input")
            return
        
        # Build command
        import sys
        cmd = [sys.executable, str(self.pixivutil_path), '-s', mode]
        
        if input_val:
            if mode == '4' or mode == '7':  # List file modes
                cmd.extend(['-f', input_val])
            else:
                # Split multiple IDs by space
                ids = input_val.split()
                cmd.extend(ids)
        
        # Add options
        if self.include_sketch.get() and mode == '1':
            cmd.append('--include_sketch')
        
        if self.use_wildcard.get() and mode in ['3', '7']:
            cmd.append('--use_wildcard_tag')
        
        start = self.start_page.get()
        end = self.end_page.get()
        if start and start != '1':
            cmd.extend(['--sp', start])
        if end and end != '0':
            cmd.extend(['--ep', end])
        
        cmd.append('-x')  # Exit when done
        
        self.log_output(f"Executing: {' '.join(cmd)}\n")
        
        # Start download in thread
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.progress_bar.start()
        self.status_label.config(text="Downloading...", foreground='blue')
        
        thread = threading.Thread(target=self.run_download, args=(cmd,), daemon=True)
        thread.start()
    
    def run_download(self, cmd):
        try:
            # Set UTF-8 encoding for the subprocess
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                env=env,
                encoding='utf-8',
                errors='replace'  # Replace characters that can't be encoded
            )
            
            for line in self.process.stdout:
                self.root.after(0, self.log_output, line)
            
            self.process.wait()
            
            if self.process.returncode == 0:
                self.root.after(0, self.download_complete, "Download completed successfully!")
            else:
                self.root.after(0, self.download_complete, 
                              f"Download finished with code: {self.process.returncode}")
                
        except Exception as e:
            self.root.after(0, self.download_error, str(e))
    
    def stop_download(self):
        if self.process:
            self.process.terminate()
            self.log_output("\n--- Download stopped by user ---\n")
            self.download_complete("Download stopped")
    
    def download_complete(self, message):
        self.progress_bar.stop()
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_label.config(text=message, foreground='green')
        self.process = None
    
    def download_error(self, error):
        self.progress_bar.stop()
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_label.config(text=f"Error: {error}", foreground='red')
        self.log_output(f"\nError: {error}\n")
        self.process = None
    
    def run_db_operation(self, cmd, subcmd):
        if not self.pixivutil_path.exists():
            messagebox.showerror("Error", "PixivUtil2.py not found")
            return
        
        import sys
        command = [sys.executable, str(self.pixivutil_path), '-s', cmd]
        
        self.log_output(f"\nExecuting database operation: {cmd} {subcmd}\n")
        
        thread = threading.Thread(
            target=self.run_command_interactive,
            args=(command, subcmd),
            daemon=True
        )
        thread.start()
    
    def run_command_interactive(self, cmd, initial_input=None):
        try:
            # Set UTF-8 encoding for the subprocess
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                env=env,
                encoding='utf-8',
                errors='replace'
            )
            
            if initial_input:
                self.process.stdin.write(initial_input + '\n')
                self.process.stdin.flush()
            
            for line in self.process.stdout:
                self.root.after(0, self.log_output, line)
            
            self.process.wait()
            self.root.after(0, self.log_output, "\n--- Operation completed ---\n")
            
        except Exception as e:
            self.root.after(0, self.log_output, f"\nError: {str(e)}\n")
    
    def log_output(self, text):
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
    
    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
    
    def save_log(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.output_text.get(1.0, tk.END))
            messagebox.showinfo("Success", f"Log saved to {filename}")

def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    
    # Map package names to their import names
    package_map = {
        'pillow': 'PIL',
        'beautifulsoup4': 'bs4',
        'pysocks': 'socks',
        'curl-cffi': 'curl_cffi',
        'python-dateutil': 'dateutil',
        'demjson3': 'demjson3'
    }
    
    # Read requirements from requirements.txt if it exists
    req_file = Path("requirements.txt")
    if req_file.exists():
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name
                    package = line.split('==')[0].split('>=')[0].split('<=')[0].split('[')[0].strip().lower()
                    
                    # Get the actual import name
                    import_name = package_map.get(package, package.replace('-', '_'))
                    
                    try:
                        __import__(import_name)
                    except ImportError:
                        missing.append(line)
    
    return missing

def install_dependencies(missing):
    """Install missing dependencies"""
    import sys
    
    result = messagebox.askyesno(
        "Missing Dependencies",
        f"The following packages are required but not installed:\n\n" +
        "\n".join(missing) +
        "\n\nWould you like to install them now?\n" +
        "(This will run: pip install -r requirements.txt)"
    )
    
    if result:
        try:
            # Create a simple window to show installation progress
            install_window = tk.Toplevel()
            install_window.title("Installing Dependencies")
            install_window.geometry("500x300")
            
            ttk.Label(install_window, text="Installing dependencies...", 
                     font=('Arial', 12, 'bold')).pack(pady=10)
            
            output = scrolledtext.ScrolledText(install_window, height=15)
            output.pack(fill='both', expand=True, padx=10, pady=10)
            
            def run_install():
                # Add --no-warn-script-location to suppress PATH warnings
                # This is safe and just hides informational warnings
                process = subprocess.Popen(
                    [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt', 
                     '--no-warn-script-location', '--disable-pip-version-check'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                
                for line in process.stdout:
                    output.insert(tk.END, line)
                    output.see(tk.END)
                    output.update()
                
                process.wait()
                
                if process.returncode == 0:
                    messagebox.showinfo("Success", 
                                      "Dependencies installed successfully!\n" +
                                      "Please restart the application.")
                else:
                    messagebox.showerror("Error", 
                                       "Failed to install dependencies.\n" +
                                       "Please run manually: pip install -r requirements.txt")
                
                install_window.destroy()
            
            thread = threading.Thread(target=run_install, daemon=True)
            thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Installation failed: {str(e)}")

def main():
    # Check dependencies first
    missing = check_dependencies()
    
    if missing:
        # Create temporary root for messagebox
        temp_root = tk.Tk()
        temp_root.withdraw()
        install_dependencies(missing)
        temp_root.destroy()
        return
    
    root = tk.Tk()
    app = PixivUtilGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
