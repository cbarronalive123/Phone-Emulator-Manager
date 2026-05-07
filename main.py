import sys
import subprocess
import os
import platform
import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QLabel, QSystemTrayIcon, QMenu,
    QDialog, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QMessageBox,
    QListWidgetItem, QTextBrowser
)
from PyQt6.QtGui import QAction, QFont, QIcon, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QRectF, QThread, pyqtSignal, QSharedMemory

def init_db():
    conn = sqlite3.connect("devices.db")
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS device_profiles
                      (id INTEGER PRIMARY KEY, os_type TEXT, name TEXT UNIQUE, internal_id TEXT)''')
                      
    cursor.execute('''CREATE TABLE IF NOT EXISTS os_images
                      (id INTEGER PRIMARY KEY, os_type TEXT, package TEXT UNIQUE, description TEXT)''')
                      
    # Cleanup any old garbage from previous versions
    cursor.execute("DELETE FROM os_images WHERE description LIKE '%CANARY%'")
    
    import devices_data
    for name, internal in devices_data.IOS_DEVICES:
        cursor.execute("INSERT OR IGNORE INTO device_profiles (os_type, name, internal_id) VALUES (?, ?, ?)", ("iOS", name, internal))
    
    ios_os = [
        ("iOS 19.0", "iOS 19.0 Simulator [2025]"),
        ("iOS 18.0", "iOS 18.0 Simulator [2024]"),
        ("iOS 17.4", "iOS 17.4 Simulator [2023]"), 
        ("iOS 16.4", "iOS 16.4 Simulator [2022]")
    ]
    for pkg, desc in ios_os:
        cursor.execute("INSERT OR IGNORE INTO os_images (os_type, package, description) VALUES (?, ?, ?)", ("iOS", pkg, desc))
        
    android_os = [
        ("system-images;android-37;google_apis_playstore;x86_64", "Android 17 (Cinnamon Bun) [2026] - with Google Play Store"),
        ("system-images;android-36;google_apis_playstore;x86_64", "Android 16 (Baklava) [2025] [Recommended] - with Google Play Store"),
        ("system-images;android-35;google_apis_playstore;x86_64", "Android 15 (2024) - with Google Play Store"),
        ("system-images;android-34;google_apis_playstore;x86_64", "Android 14 (2023) - with Google Play Store"),
        ("system-images;android-33;google_apis_playstore;x86_64", "Android 13 (2022) - with Google Play Store"),
        ("system-images;android-32;google_apis_playstore;x86_64", "Android 12L (2022) - with Google Play Store"),
        ("system-images;android-31;google_apis_playstore;x86_64", "Android 12 (2021) - with Google Play Store"),
        ("system-images;android-30;google_apis_playstore;x86_64", "Android 11 (2020) - with Google Play Store"),
        ("system-images;android-29;google_apis_playstore;x86_64", "Android 10 (2019) - with Google Play Store"),
        ("system-images;android-28;google_apis_playstore;x86_64", "Android 9 (2018) - with Google Play Store"),
    ]
    for pkg, desc in android_os:
        cursor.execute("INSERT OR IGNORE INTO os_images (os_type, package, description) VALUES (?, ?, ?)", ("Android", pkg, desc))
        
    for name, internal_id in devices_data.ANDROID_DEVICES:
        cursor.execute("INSERT OR IGNORE INTO device_profiles (os_type, name, internal_id) VALUES (?, ?, ?)", ("Android", name, internal_id))
        
    for name, internal_id in devices_data.HARMONYOS_DEVICES:
        cursor.execute("INSERT OR IGNORE INTO device_profiles (os_type, name, internal_id) VALUES (?, ?, ?)", ("HarmonyOS", name, internal_id))
        
    for name, internal_id in devices_data.FIREOS_DEVICES:
        cursor.execute("INSERT OR IGNORE INTO device_profiles (os_type, name, internal_id) VALUES (?, ?, ?)", ("Fire OS", name, internal_id))
        
    fire_os = [
        ("system-images;android-34;amazon_apis;x86_64", "Fire OS 14 (Android 14) [2024] - Kindle Fire"),
        ("system-images;android-30;amazon_apis;x86_64", "Fire OS 8 (Android 11) [2022] - Kindle Fire"),
        ("system-images;android-28;amazon_apis;x86_64", "Fire OS 7 (Android 9) [2019] - Kindle Fire")
    ]
    for pkg, desc in fire_os:
        cursor.execute("INSERT OR IGNORE INTO os_images (os_type, package, description) VALUES (?, ?, ?)", ("Fire OS", pkg, desc))
        
    harmony_os = [
        ("harmonyos-emulator-5.0", "HarmonyOS NEXT (5.0) [2024]"),
        ("harmonyos-emulator-4.0", "HarmonyOS 4.0 API 10 [2023]"),
        ("harmonyos-emulator-3.1", "HarmonyOS 3.1 API 9 [2023]")
    ]
    for pkg, desc in harmony_os:
        cursor.execute("INSERT OR IGNORE INTO os_images (os_type, package, description) VALUES (?, ?, ?)", ("HarmonyOS", pkg, desc))
        
    conn.commit()
    conn.close()

class SyncDbThread(QThread):
    finished = pyqtSignal()
    
    def __init__(self, avdmanager_path, sdkmanager_path):
        super().__init__()
        self.avdmanager_path = avdmanager_path
        self.sdkmanager_path = sdkmanager_path

    def run(self):
        conn = sqlite3.connect("devices.db")
        cursor = conn.cursor()
        
        try:
            CREATE_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0
            kwargs = {'creationflags': CREATE_NO_WINDOW} if platform.system() == "Windows" else {}
            
            # Query Android Devices
            if self.avdmanager_path:
                result = subprocess.run([self.avdmanager_path, "list", "device", "-c"], 
                                      capture_output=True, text=True, **kwargs)
                for dev in result.stdout.strip().split('\n'):
                    dev = dev.strip()
                    if dev:
                        cursor.execute("INSERT OR IGNORE INTO device_profiles (os_type, name, internal_id) VALUES (?, ?, ?)", ("Android", dev, dev))
            
            # Query Android OS Images
            if self.sdkmanager_path:
                result = subprocess.run([self.sdkmanager_path, "--list"], 
                                      capture_output=True, text=True, **kwargs)
                for line in result.stdout.split('\n'):
                    if "system-images;" in line:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            package = parts[0].strip()
                            
                            if "x86_64" not in package and "x86" not in package:
                                continue
                            if any(x in package for x in ["wear", "tv", "automotive", "chromeos"]):
                                continue
                                
                            api_mapping = {
                                "android-35": "Android 15 (2024) [Recommended]",
                                "android-34": "Android 14 (2023)",
                                "android-33": "Android 13 (2022)",
                                "android-32": "Android 12L (2022)",
                                "android-31": "Android 12 (2021)",
                                "android-30": "Android 11 (2020)",
                                "android-29": "Android 10 (2019)",
                                "android-28": "Android 9 (2018)"
                            }
                            
                            api_level = package.split(';')[1] if len(package.split(';')) > 1 else "Unknown"
                            
                            if api_level not in api_mapping:
                                continue
                                
                            human_api = api_mapping[api_level]
                            
                            if "playstore" in package:
                                suffix = "with Google Play Store"
                            elif "google_apis" in package:
                                suffix = "with Google APIs"
                            else:
                                suffix = "Open Source (No Google Apps)"
                                
                            nice_name = f"{human_api} - {suffix}"
                            cursor.execute("INSERT OR IGNORE INTO os_images (os_type, package, description) VALUES (?, ?, ?)", ("Android", package, nice_name))
        except Exception as e:
            print(f"Background Sync Error: {e}")
            
        conn.commit()
        conn.close()
        self.finished.emit()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings & Instructions")
        self.resize(550, 450)
        
        layout = QVBoxLayout(self)
        
        text_browser = QTextBrowser()
        text_browser.setOpenExternalLinks(True)
        text_browser.setStyleSheet("background-color: transparent; color: white; border: none; font-size: 14px;")
        
        html_content = """
        <style>
            a { color: #2ecc71; text-decoration: none; font-weight: bold; }
            h2 { color: #0098ff; margin-bottom: 5px; }
            ul { margin-top: 5px; }
            li { margin-bottom: 8px; }
        </style>
        <h2>Download Software Prerequisites</h2>
        <ul>
            <li><b>Android & Amazon Fire OS:</b><br>
            Requires <a href='https://developer.android.com/studio'>Android Studio</a>. Install it and open it once to automatically install the underlying SDK and command-line tools.</li>
            <li><b>Huawei HarmonyOS:</b><br>
            Requires <a href='https://developer.huawei.com/consumer/en/deveco-studio/'>DevEco Studio</a>, the official IDE provided by Huawei.</li>
            <li><b>Apple iOS:</b><br>
            Requires a Mac computer. Download <a href='https://apps.apple.com/us/app/xcode/id497799835'>Xcode</a> from the Mac App Store.</li>
        </ul>
        
        <hr style='border: 1px solid #1E3A8A; margin: 15px 0;'>
        
        <h2>Find Your Physical Device's OS Version</h2>
        <p>To match an emulator's System Image accurately to a real physical phone, you can find the OS version directly on the physical device:</p>
        <ul>
            <li><b>Android / Fire OS:</b> Open <i>Settings</i> > <i>About Phone</i> (or <i>About Device</i>) > Look for <b>Android Version</b>.</li>
            <li><b>HarmonyOS:</b> Open <i>Settings</i> > <i>About Phone</i> > Look for <b>HarmonyOS Version</b>.</li>
            <li><b>iOS:</b> Open <i>Settings</i> > <i>General</i> > <i>About</i> > Look for <b>iOS Version</b>.</li>
        </ul>
        """
        text_browser.setHtml(html_content)
        layout.addWidget(text_browser)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.buttons.accepted.connect(self.accept)
        layout.addWidget(self.buttons)
        
        self.setStyleSheet("""
            QDialog { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #09132D, stop:1 #020612); color: white; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1D4ED8, stop:1 #172554);
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: 1px solid #1E3A8A;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563EB, stop:1 #1E40AF); }
        """)

class CreateAvdDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Emulator")
        self.setMinimumWidth(400)
        self.device_mapping = {}
        self.image_mapping = {}
        self.all_devices_for_platform = []
        
        self.layout = QFormLayout(self)
        
        self.os_combo = QComboBox()
        for platform_name, icon_name in [("Android", "android"), ("iOS", "apple"), ("HarmonyOS", "huawei"), ("Fire OS", "amazon")]:
            icon_path = f"icons/{icon_name}.svg"
            if os.path.exists(icon_path):
                self.os_combo.addItem(QIcon(icon_path), platform_name)
            else:
                self.os_combo.addItem(platform_name)
        self.os_combo.currentTextChanged.connect(self.load_dropdowns)
        self.layout.addRow("Platform:", self.os_combo)
        
        self.name_input = QLineEdit()
        self.name_input.setText("New_Device")
        self.layout.addRow("Name:", self.name_input)
        
        self.make_combo = QComboBox()
        self.make_combo.currentTextChanged.connect(self.on_make_changed)
        self.layout.addRow("Make:", self.make_combo)
        
        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        self.layout.addRow("Model:", self.model_combo)
        
        self.image_combo = QComboBox()
        self.layout.addRow("System Image:", self.image_combo)
        
        self.load_dropdowns()
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addRow(self.buttons)
        
        self.setStyleSheet("""
            QDialog { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #09132D, stop:1 #020612); color: white; }
            QLabel { color: white; background: transparent; }
            QLineEdit, QComboBox { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #172554, stop:1 #0A102A);
                color: white; 
                border: 1px solid #1D4ED8;
                border-radius: 4px;
                padding: 5px;
            }
            QComboBox::drop-down { border: none; }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1D4ED8, stop:1 #172554);
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: 1px solid #1E3A8A;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563EB, stop:1 #1E40AF); }
        """)

    def _get_device_make(self, name):
        name_lower = name.lower()
        if name.startswith("Planet Computers"): return "Planet Computers"
        if name.startswith("Black Shark"): return "Black Shark"
        if name.startswith("Sony"): return "Sony"
        
        if name_lower.startswith("pixel") or name_lower.startswith("nexus"):
            return "Google"
        if "automotive" in name_lower:
            return "Automotive"
        if "wearos" in name_lower or "wear os" in name_lower:
            return "WearOS"
        if "tv" in name_lower or "television" in name_lower:
            return "TV"
        if "desktop" in name_lower:
            return "Desktop"
            
        import re
        if re.match(r'^\d+(\.\d+)?in', name_lower) or name_lower.startswith("resizable"):
            return "Generic"
        if name_lower.startswith("small") or name_lower.startswith("medium") or name_lower.startswith("large"):
            return "Generic"
            
        return name.split()[0]

    def load_dropdowns(self):
        platform_type = self.os_combo.currentText()
        self.make_combo.blockSignals(True)
        self.make_combo.clear()
        self.image_combo.clear()
        
        conn = sqlite3.connect("devices.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, internal_id FROM device_profiles WHERE os_type=? ORDER BY id", (platform_type,))
        self.all_devices_for_platform = cursor.fetchall()
        
        import devices_data
        makes = set()
        for name, internal_id in self.all_devices_for_platform:
            if platform_type == "iOS":
                makes.add("Apple")
            elif platform_type == "Fire OS":
                makes.add("Amazon")
            elif platform_type == "HarmonyOS":
                makes.add("Huawei")
            else:
                makes.add(self._get_device_make(name))
                    
        sorted_makes = []
        for brand in devices_data.NORTH_AMERICAN_MAKES:
            if brand in makes and platform_type != "iOS":
                sorted_makes.append(brand)
                
        other_makes = sorted([m for m in makes if m not in devices_data.NORTH_AMERICAN_MAKES and m != "Apple"])
        
        if platform_type == "iOS":
            makes_list = ["Apple"]
        elif platform_type == "Fire OS":
            makes_list = ["Amazon"]
        elif platform_type == "HarmonyOS":
            makes_list = ["Huawei"]
        else:
            makes_list = sorted_makes + other_makes
            
        if not makes_list:
            makes_list = ["Syncing..."]
            
        for make in makes_list:
            icon_path = f"icons/{make.lower()}.svg"
            if os.path.exists(icon_path):
                self.make_combo.addItem(QIcon(icon_path), make)
            else:
                self.make_combo.addItem(make)
                
        self.make_combo.blockSignals(False)
        
        # Load images
        cursor.execute("SELECT package, description FROM os_images WHERE os_type=?", (platform_type,))
        self.image_mapping.clear()
        
        temp_dict = {}
        for r in cursor.fetchall():
            pkg, desc = r[0], r[1]
            display = desc if platform_type == "Android" else pkg
            
            if display not in temp_dict:
                temp_dict[display] = pkg
            else:
                if "x86_64" in pkg:
                    temp_dict[display] = pkg
                    
        images = list(temp_dict.keys())
        images.sort(reverse=True)
        # Force Recommended to the absolute top
        recommended = [img for img in images if "[Recommended]" in img]
        others = [img for img in images if "[Recommended]" not in img]
        images = recommended + others
        self.image_mapping = temp_dict
            
        self.image_combo.clear()
        if not images:
            self.image_combo.addItem("No images found (Syncing...)")
        else:
            icon_path = "icons/android.svg" if platform_type == "Android" else "icons/apple.svg"
            if platform_type == "Fire OS": icon_path = "icons/amazon.svg"
            if platform_type == "HarmonyOS": icon_path = "icons/huawei.svg"
            icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
            for display in images:
                self.image_combo.addItem(icon, display)
        
        conn.close()
        
        self.on_make_changed()


    def on_make_changed(self):
        self.model_combo.clear()
        self.device_mapping = {}
        make = self.make_combo.currentText()
        platform_type = self.os_combo.currentText()
        
        if make == "Syncing...":
            self.model_combo.addItem("Syncing...")
            return
            
        models = []
        for name, internal_id in self.all_devices_for_platform:
            if platform_type == "iOS":
                if make == "Apple":
                    models.append(name)
                    self.device_mapping[name] = internal_id
            elif platform_type == "Fire OS":
                if make == "Amazon":
                    models.append(name)
                    self.device_mapping[name] = internal_id
            elif platform_type == "HarmonyOS":
                if make == "Huawei":
                    models.append(name)
                    self.device_mapping[name] = internal_id
            else:
                device_make = self._get_device_make(name)
                    
                if make == device_make:
                    models.append(name)
                    self.device_mapping[name] = internal_id
                    
        if not models:
            models = ["No models found"]
        else:
            import re
            def get_year(model_name):
                match = re.search(r'\((\d{4})\)', model_name)
                return int(match.group(1)) if match else 0
            
            # Sort chronologically descending
            models.sort(key=get_year, reverse=True)
            
        self.model_combo.addItems(models)

    def on_model_changed(self, text):
        if not text or text == "No models found" or text == "Syncing...":
            return
            
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', text)
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        self.name_input.setText(clean_name)

class EmulatorLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phone Emulator Manager")
        self.resize(385, 650)
        self.setMinimumSize(330, 520)
        
        init_db()
        
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #09132D, stop:1 #020612);
            }
            QLabel {
                color: #e0e0e0;
                font-size: 18px;
                font-weight: bold;
                padding-bottom: 10px;
                background: transparent;
            }
            QMenu {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #09132D, stop:1 #020612);
                color: #e0e0e0;
                border: 1px solid #1D4ED8;
            }
            QMenu::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1D4ED8, stop:1 #1E40AF);
            }
            QListWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0D1630, stop:1 #040814);
                border: 1px solid #1D4ED8;
                border-radius: 8px;
                padding: 8px;
                font-size: 15px;
                color: #e0e0e0;
                outline: none;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #1E3A8A;
                border-radius: 4px;
                background: transparent;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #14347A, stop:1 #0A1C47);
                border-left: 4px solid #3B82F6;
                color: white;
            }
            QListWidget::item:hover:!selected {
                background: rgba(37, 99, 235, 0.3);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1D4ED8, stop:1 #172554);
                color: white;
                border: 1px solid #1E3A8A;
                border-radius: 8px;
                padding: 14px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2563EB, stop:1 #1E40AF);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E40AF, stop:1 #1D4ED8);
            }
            QPushButton:disabled {
                background-color: #4a4a5a;
                color: #8b8b99;
            }
        """)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(10)
        
        self.label = QLabel("Select Mobile Phone to Start")
        self.layout.addWidget(self.label)
        
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.layout.addWidget(self.list_widget)
        
        self.start_button = QPushButton("Start Emulator")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.clicked.connect(self.start_emulator)
        self.start_button.setEnabled(False)
        self.layout.addWidget(self.start_button)
        
        self.manage_layout = QHBoxLayout()
        self.manage_layout.setSpacing(10)
        
        self.create_button = QPushButton("Create")
        self.create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_button.clicked.connect(self.create_avd)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_button.clicked.connect(self.delete_avd)
        self.delete_button.setEnabled(False)
        self.delete_button.setStyleSheet("""
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7f1d1d, stop:1 #450a0a); padding: 10px; font-size: 13px; border: 1px solid #991b1b; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #991b1b, stop:1 #7f1d1d); }
            QPushButton:disabled { background: #4a4a5a; border: 1px solid #333; }
        """)
        self.create_button.setStyleSheet("""
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #064E3B, stop:1 #022C22); padding: 10px; font-size: 13px; border: 1px solid #047857; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #047857, stop:1 #064E3B); }
        """)
        
        self.settings_button = QPushButton("⚙️ Settings")
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setStyleSheet("""
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #09132D, stop:1 #020612); padding: 10px; font-size: 13px; border: 1px solid #1D4ED8; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E3A8A, stop:1 #0F172A); }
        """)
        
        self.manage_layout.addWidget(self.create_button)
        self.manage_layout.addWidget(self.delete_button)
        self.manage_layout.addWidget(self.settings_button)
        self.layout.addLayout(self.manage_layout)
        
        self.emulator_path = self.get_emulator_path()
        self.setup_tray_icon()
        self.load_avds()
        
        # Start background sync
        self.sync_thread = SyncDbThread(self.get_avdmanager_path(), self.get_sdkmanager_path())
        self.sync_thread.start()

    def get_sdk_root(self):
        sdk_root = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
        system = platform.system()
        if not sdk_root:
            if system == "Windows":
                sdk_root = os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk")
            elif system == "Darwin":
                sdk_root = os.path.expanduser("~/Library/Android/sdk")
            else:
                sdk_root = os.path.expanduser("~/Android/Sdk")
        return sdk_root

    def get_emulator_path(self):
        sdk_root = self.get_sdk_root()
        emulator_exe = 'emulator.exe' if platform.system() == 'Windows' else 'emulator'
        if sdk_root:
            emulator = os.path.join(sdk_root, 'emulator', emulator_exe)
            if os.path.exists(emulator):
                return emulator
        return ""

    def get_avdmanager_path(self):
        sdk_root = self.get_sdk_root()
        avdmanager_exe = 'avdmanager.bat' if platform.system() == 'Windows' else 'avdmanager'
        cmdline_tools = os.path.join(sdk_root, 'cmdline-tools', 'latest', 'bin', avdmanager_exe)
        if os.path.exists(cmdline_tools):
            return cmdline_tools
        tools_bin = os.path.join(sdk_root, 'tools', 'bin', avdmanager_exe)
        if os.path.exists(tools_bin):
            return tools_bin
        return ""
        
    def get_sdkmanager_path(self):
        sdk_root = self.get_sdk_root()
        sdkmanager_exe = 'sdkmanager.bat' if platform.system() == 'Windows' else 'sdkmanager'
        cmdline_tools = os.path.join(sdk_root, 'cmdline-tools', 'latest', 'bin', sdkmanager_exe)
        if os.path.exists(cmdline_tools):
            return cmdline_tools
        return ""

    def create_phone_icon(self):
        pixmap = QPixmap(256, 256)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Exterior white border
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(Qt.PenStyle.NoPen)
        outer_rect = QRectF(28, 4, 200, 248)
        painter.drawRoundedRect(outer_rect, 28, 28)
        
        # Phone body (Black)
        painter.setBrush(QBrush(QColor("#111111")))
        inner_rect = QRectF(38, 14, 180, 228)
        painter.drawRoundedRect(inner_rect, 24, 24)
        
        # Screen (White)
        painter.setBrush(QBrush(QColor("#ffffff")))
        screen_rect = QRectF(44, 48, 168, 152)
        painter.drawRect(screen_rect)
        
        # Top speaker / camera (Larger so it doesn't anti-alias to grey)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawRoundedRect(QRectF(92, 16, 72, 16), 8, 8)
        
        # Bottom home button (Larger)
        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.drawEllipse(112, 210, 32, 32)
        
        # Draw the user's phone icon image inside the screen
        image_path = os.path.join("icons", "phone_icon_green.png")
        if os.path.exists(image_path):
            img = QPixmap(image_path)
            img = img.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x_pos = int(52 + (152 - img.width()) / 2)
            y_pos = int(48 + (152 - img.height()) / 2)
            painter.drawPixmap(x_pos, y_pos, img)
        
        painter.end()
        return QIcon(pixmap)

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        icon = self.create_phone_icon()
        self.tray_icon.setIcon(icon)
        self.setWindowIcon(icon)
        
        self.tray_menu = QMenu()
        
        self.show_action = QAction("Show Application", self)
        self.show_action.triggered.connect(self.show_app)
        self.tray_menu.addAction(self.show_action)
        
        self.tray_menu.addSeparator()
        
        self.quit_action = QAction("Quit", self)
        self.quit_action.triggered.connect(self.quit_app)
        self.tray_menu.addAction(self.quit_action)
        
        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick or reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_app()

    def show_app(self):
        self.showNormal()
        self.activateWindow()

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def on_selection_changed(self):
        has_selection = len(self.list_widget.selectedItems()) > 0
        self.start_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def load_avds(self):
        self.list_widget.clear()
        if not os.path.exists(self.emulator_path):
            self.list_widget.addItem(f"Emulator not found at:\n{self.emulator_path}")
            return
            
        try:
            kwargs = {}
            if platform.system() == "Windows":
                kwargs['creationflags'] = 0x08000000
                
            result = subprocess.run(
                [self.emulator_path, "-list-avds"], 
                capture_output=True, 
                text=True, 
                check=True,
                **kwargs
            )
            avds = result.stdout.strip().split('\n')
            has_valid_avds = False
            valid_index = 1
            for avd in avds:
                avd = avd.strip()
                if avd:
                    icon = QIcon("icons/android.svg") if os.path.exists("icons/android.svg") else QIcon()
                    item = QListWidgetItem(icon, f"{valid_index}. Android - {avd}")
                    item.setData(Qt.ItemDataRole.UserRole, avd)
                    self.list_widget.addItem(item)
                    valid_index += 1
                    has_valid_avds = True
            
            if not has_valid_avds:
                self.list_widget.addItem("No AVDs found.")
        except Exception as e:
            self.list_widget.addItem(f"Error loading AVDs: {e}")

    def create_avd(self):
        dialog = CreateAvdDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            platform_type = dialog.os_combo.currentText()
            name = dialog.name_input.text().strip()
            device_display = dialog.model_combo.currentText()
            image_display = dialog.image_combo.currentText()
            
            if not name or "Syncing" in image_display or "No images" in image_display:
                return
                
            if platform_type == "iOS":
                QMessageBox.information(self, "iOS Not Supported", "macOS and Xcode are strictly required to download or create iOS simulators. Windows is technically incapable of virtualizing iOS devices.")
                return
                
            avdmanager = self.get_avdmanager_path()
            if not avdmanager:
                QMessageBox.critical(self, "Error", "avdmanager not found!")
                return
                
            # Map the visual model name and OS image to internal profiles
            device_internal = dialog.device_mapping.get(device_display, device_display)
            image = dialog.image_mapping.get(image_display, image_display)
                
            sdkmanager = self.get_sdkmanager_path()
            if sdkmanager:
                self.tray_icon.showMessage("Downloading OS", f"Ensuring {image} is installed. This may take a while...", QSystemTrayIcon.MessageIcon.Information, 5000)
                try:
                    kwargs = {}
                    if platform.system() == "Windows":
                        kwargs['creationflags'] = 0x08000000
                    subprocess.run([sdkmanager, image], check=True, **kwargs)
                except Exception as e:
                    QMessageBox.warning(self, "Download Warning", f"Failed to verify/download image:\n{e}")
            
            try:
                kwargs = {}
                if platform.system() == "Windows":
                    kwargs['creationflags'] = 0x08000000
                
                cmd = f'echo no | "{avdmanager}" create avd -n "{name}" -k "{image}" -d "{device_internal}" -f'
                subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, **kwargs)
                self.load_avds()
                QMessageBox.information(self, "Success", f"Successfully created emulator {name}!")
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(self, "Error", f"Failed to create emulator:\n{e.stderr}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to create emulator:\n{str(e)}")

    def delete_avd(self):
        selected = self.list_widget.selectedItems()
        if not selected: return
        
        avd_name = selected[0].data(Qt.ItemDataRole.UserRole)
        if not avd_name:
            return
            
        reply = QMessageBox.question(self, 'Confirm Delete', 
                                     f'Are you sure you want to completely delete {avd_name}?',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            avdmanager = self.get_avdmanager_path()
            if not avdmanager:
                QMessageBox.critical(self, "Error", "avdmanager not found!")
                return
            
            try:
                kwargs = {}
                if platform.system() == "Windows":
                    kwargs['creationflags'] = 0x08000000
                    
                subprocess.run([avdmanager, "delete", "avd", "-n", avd_name], check=True, capture_output=True, text=True, **kwargs)
                self.load_avds()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete emulator:\n{str(e)}")

    def start_emulator(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        
        avd_name = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not avd_name:
            return
            
        try:
            kwargs = {}
            if platform.system() == "Windows":
                kwargs['creationflags'] = 0x08000000
                
            cmd = [self.emulator_path, "-avd", avd_name, "-memory", "6144", "-cores", "4", "-gpu", "host"]
            
            subprocess.Popen(cmd, **kwargs)
            self.hide()
        except Exception as e:
            print(f"Error starting emulator: {e}")

    def quit_app(self):
        self._is_quitting = True
        QApplication.instance().quit()

    def closeEvent(self, event):
        if getattr(self, '_is_quitting', False):
            event.accept()
        else:
            event.ignore()
            self.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    shared_mem = QSharedMemory("PhoneEmulatorAppUniqueId_12345")
    if not shared_mem.create(1):
        QMessageBox.warning(None, "Already Running", "The Phone Emulator Manager is already running. Check your system tray!")
        sys.exit(0)
        
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    app.setQuitOnLastWindowClosed(False)
    
    window = EmulatorLauncher()
    window.show()
    
    sys.exit(app.exec())
