#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# version: 2.1.0

# TODO: 추가 예정 기능 목록
# 1. 데이터베이스 기능
#    - PostgreSQL 연결 및 관리 기능
#    - 이메일 메타데이터 저장 및 인덱싱
#    - 전문 검색(Full-text search) 구현
#    - 대용량 데이터 처리 최적화
#
# 2. 이메일 검색 기능
#    - IMAP/POP3 프로토콜 지원
#    - 이메일 본문 및 첨부파일 처리
#    - 메타데이터 기반 검색 (보낸사람, 날짜, 제목 등)
#    - 본문 내용 검색 및 필터링
#
# 3. 구글 캘린더 연동
#    - OAuth2 인증 처리
#    - 일정 조회/추가/수정/삭제
#    - 알림 설정 지원
#    - 반복 일정 관리
#
# 4. 카카오톡 메시지 전송
#    - 카카오톡 REST API 연동
#    - 텍스트/이미지 메시지 전송
#    - 템플릿 메시지 지원
#    - 대화방 관리 기능

import os
import shutil
import subprocess
import zlib
import hashlib
from typing import List, Union, Tuple, Optional, Callable, Any, Dict
import xml.etree.ElementTree as ET
import tempfile
import pkg_resources
import io
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import sys
import time
from datetime import datetime
import uuid
import zipfile
from PIL import Image
import random
import urllib.parse
import re

class Config:
    """설정 관리를 위한 클래스"""
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._config = self._load_config()

    def reload(self):
        """설정을 다시 로드합니다."""
        self._config = self._load_config()
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """설정값을 가져옵니다."""
        return self._config.get(key, default)

    def get_smtp_settings(self) -> dict:
        """SMTP 설정을 딕셔너리로 반환합니다."""
        return {
            'host': self.get('SMTP_HOST', 'smtp.gmail.com'),
            'port': int(self.get('SMTP_PORT', '587')),
            'username': self.get('SMTP_USERNAME', ''),
            'password': self.get('SMTP_PASSWORD', ''),
            'secure': self.get('SMTP_SECURE', 'YES').upper() not in ['NO', 'N']
        }

    @staticmethod
    def _load_config() -> dict:
        """
        ~/.config/codai/tools.conf 파일에서 설정을 읽어옵니다.
        파일이 없는 경우 기본 설정으로 생성합니다.
        
        Returns:
            dict: 설정값들을 담은 딕셔너리
        """
        config = {}
        config_dir = os.path.expanduser("~/.config/codai")
        config_path = os.path.join(config_dir, "tools.conf")
        
        # 기본 SMTP 설정
        default_config = {
            'SMTP_HOST': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'SMTP_USERNAME': '',
            'SMTP_PASSWORD': '',
            'SMTP_SECURE': 'YES'
        }
        
        # 설정 디렉토리가 없으면 생성
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        # 설정 파일이 없으면 기본 설정으로 생성
        if not os.path.exists(config_path):
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write("""# Codai Tools 설정 파일
# 이 파일은 자동으로 생성되었습니다.
# 각 설정값을 필요에 맞게 수정해주세요.

# =============================================================================
# SMTP 이메일 설정
# =============================================================================
# Gmail을 사용하는 경우:
# - SMTP_HOST는 'smtp.gmail.com' 사용
# - SMTP_PORT는 587 (TLS) 또는 465 (SSL) 사용
# - SMTP_USERNAME에 Gmail 주소 입력
# - SMTP_PASSWORD에 앱 비밀번호 입력 (Gmail 계정 설정에서 생성 필요)
# - SMTP_SECURE는 TLS 사용시 YES, 미사용시 NO

# Naver 메일을 사용하는 경우:
# SMTP_HOST=smtp.naver.com
# SMTP_PORT=587

# 다음 메일을 사용하는 경우:
# SMTP_HOST=smtp.daum.net
# SMTP_PORT=465

# 현재 설정값:
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_SECURE=YES
""")
            print(f"[INFO] 기본 설정 파일이 생성되었습니다: {config_path}")
            print("[INFO] SMTP 설정을 완료하려면 파일을 직접 수정해주세요.")
        
        # 설정 파일 읽기
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):  # 주석 무시
                        try:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            config[key] = value
                        except ValueError:
                            continue  # 잘못된 형식의 라인은 무시
        except Exception as e:
            print(f"[ERROR] 설정 파일 읽기 실패: {str(e)}")
            return default_config
        
        # 필수 SMTP 설정이 없는 경우 기본값으로 설정
        for key, value in default_config.items():
            if key not in config:
                config[key] = value
        
        return config

# 전역 설정 객체 생성
config = Config()

# 기존 전역 변수 제거
# SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD 변수는 더 이상 사용하지 않음

def install_if_missing(package: str, import_name: str = None) -> None:
    """Install a package if it's not already installed
    
    Args:
        package (str): Package name to install with pip
        import_name (str, optional): Module name to import. Defaults to package name.
    """
    import subprocess
    import sys
    import pkg_resources
    
    try:
        # 패키지가 이미 설치되어 있는지 확인
        pkg_resources.require(package)
        
        # pyhwp의 경우 특별 처리
        if package == "pyhwp":
            try:
                __import__("hwp5")
                return
            except ImportError:
                raise pkg_resources.DistributionNotFound(package)
        
        # 다른 패키지들의 경우 기존 방식대로 처리
        if import_name:
            __import__(import_name)
        else:
            __import__(package.replace('-', '_'))
        return  # 이미 설치되어 있고 import 가능하면 종료
    except (pkg_resources.DistributionNotFound, ImportError):
        try:
            # 가상환경의 pip 사용
            pip_path = os.path.join(os.path.dirname(sys.executable), 'pip')
            
            # 패키지 설치
            subprocess.run([
                pip_path, "install", "--quiet", package
            ], check=True)
            
            print(f"[INFO] Successfully installed {package}")
            
            # 설치 후 import 확인
            if package == "pyhwp":
                try:
                    __import__("hwp5")
                except ImportError as e:
                    print(f"[WARNING] Package installed but import failed: {str(e)}")
                    raise
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Failed to install {package}: {str(e)}")
            raise

# Required packages
# 패키지 이름과 import 이름이 다른경우 처리
REQUIRED_PACKAGES = [
    ("requests", "requests"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("matplotlib", "matplotlib"),
    ("openpyxl", "openpyxl"),
    ("fpdf", "fpdf"),
    ("pyhwp", "hwp5"),  # pyhwp의 실제 import 이름은 hwp5입니다
    ("olefile", "olefile"),  
    ("python-pptx", "pptx"),
    ("PyPDF2", "PyPDF2"),
    ("Pillow", "PIL"),
    ("svglib", "svglib"),
    ("reportlab", "reportlab"),
    ("selenium", "selenium"),
    ("webdriver_manager", "webdriver_manager"),
    ("beautifulsoup4", "bs4"),
    ("lxml", "lxml"),
    ("python-docx", "docx"),
    ("trafilatura", "trafilatura"),
    ("cairosvg", "cairosvg")
]

# 패키지 설치 상태 확인 및 설치
# print("\n[INFO] Checking required packages...")
for package, import_name in REQUIRED_PACKAGES:
    try:
        # pkg_resources를 사용하여 설치 여부 확인
        pkg_resources.require(package)
        if import_name:
            __import__(import_name)
        else:
            __import__(package.replace('-', '_'))
    except (pkg_resources.DistributionNotFound, ImportError):
        print(f"[INFO] Installing missing package: {package}")
        install_if_missing(package, import_name)
        
# print("[INFO] All required packages are ready.")

# Then import all required modules
import smtplib
import webbrowser
import io
import zipfile
import olefile
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from fpdf import FPDF
from PIL import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.utils import formatdate
import cairosvg  # SVG 처리를 위한 라이브러리
# File extensions supported by pandas
PANDAS_EXTENSIONS = {
    '.xlsx': pd.read_excel,  # Excel files
    '.xls': pd.read_excel,
    '.csv': pd.read_csv,     # CSV files
    '.json': pd.read_json,   # JSON files
    '.html': pd.read_html,   # HTML files
    '.xml': pd.read_xml,     # XML files
    '.parquet': pd.read_parquet,  # Parquet files
    '.feather': pd.read_feather,  # Feather files
    '.pickle': pd.read_pickle,    # Pickle files
    '.sql': pd.read_sql,     # SQL files
    '.hdf': pd.read_hdf,     # HDF5 files
    '.sas': pd.read_sas,     # SAS files
    '.stata': pd.read_stata,  # Stata files
    '.spss': pd.read_spss    # SPSS files
}

# Pandas writers for different file types
PANDAS_WRITERS = {
    '.xlsx': lambda df, path: df.to_excel(path, index=False),
    '.xls': lambda df, path: df.to_excel(path, index=False),
    '.csv': lambda df, path: df.to_csv(path, index=False),
    '.json': lambda df, path: df.to_json(path),
    '.html': lambda df, path: df.to_html(path),
    '.xml': lambda df, path: df.to_xml(path),
    '.parquet': lambda df, path: df.to_parquet(path),
    '.feather': lambda df, path: df.to_feather(path),
    '.pickle': lambda df, path: df.to_pickle(path),
    '.sql': lambda df, path: df.to_sql(path),
    '.hdf': lambda df, path: df.to_hdf(path, 'data'),
}

# HWP file handlers
HWP_EXTENSIONS = {
    '.hwp': 'hwp',     # 한글 문서
    '.hwpx': 'hwpx'    # 한글 2018 이상 문서
}

# ChromeDriver 경로를 저장할 전역 변수
_chrome_driver_path = None

# ============================================================================
# 문서 처리 클래스 (Document Processing Classes)
# ============================================================================

def convert_image_to_rgb(img):
    """Convert image to RGB mode safely.
    
    Args:
        img: PIL Image object
    
    Returns:
        PIL Image object in RGB mode
    """
    if img.mode in ('RGBA', 'LA'):
        # RGBA나 LA 모드인 경우 알파 채널을 고려하여 변환
        background = Image.new('RGB', img.size, (255, 255, 255))
        if 'A' in img.mode:  # 알파 채널이 있는 경우
            background.paste(img, mask=img.split()[-1])
        else:
            background.paste(img)
        return background
    elif img.mode == 'P':  # 팔레트 모드
        return img.convert('RGB')
    elif img.mode != 'RGB':  # 그 외 모드
        return img.convert('RGB')
    return img

class HWPDocument:
    def __init__(self):
        self.elements = []  # (type, content, page_break) 튜플 리스트
        self.has_title = False  # 제목 존재 여부 추적
        # ~/.airun/templates 디렉토리에서 템플릿 파일 찾기
        self.template_path = os.path.expanduser('~/.airun/templates/blank.hwpx')
        if not os.path.exists(self.template_path):
            # 템플릿 디렉토리가 없으면 생성
            template_dir = os.path.dirname(self.template_path)
            os.makedirs(template_dir, exist_ok=True)
            raise FileNotFoundError(f"템플릿 파일을 찾을 수 없습니다: {self.template_path}")
        self._temp_files = []  # Track temporary files for cleanup
        
    def _preprocess_text(self, text):
        """
        특수문자와 글머리 기호를 처리하는 내부 메서드
        """
        if not text:
            return text
            
        # 특수한 공백 문자를 일반 공백으로 변환
        text = text.replace('\u3000', ' ')  # 전각 공백
        text = text.replace('\u200b', '')   # 제로 너비 공백
        text = text.replace('\ufeff', '')   # BOM

        # 특수문자 제거 (한글, 영문, 숫자, 일부 문장부호만 유지)
        # text = re.sub(r'[^\w\s\.,\(\)\[\]:/가-힣]', '', text)  # URL의 :/ 문자 유지
                
        # 연속된 공백을 하나로
        text = ' '.join(text.split())
            
        # XML 특수문자 이스케이프
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        
        # HWP 문서에서 사용되는 특수문자 처리
        text = text.replace('&amp;lt;', '[')
        text = text.replace('&amp;gt;', ']')
        text = text.replace('&amp;amp;', '&')
        text = text.replace('&amp;quot;', '"')
        
        # 연속된 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        
        # 글머리 기호 처리
        bullet_markers = ['•', '○', '●', '□', '■', '△', '▲', '▽', '▼', '◁', '◀', '▷', '▶',
                         '♠', '♡', '♣', '♤', '♥', '♧', '⊙', '◎', '▣', '◈', '▨', '▧', '▦', '▩',
                         '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨', '⑩',
                         '㉠', '㉡', '㉢', '㉣', '㉤', '㉥', '㉦', '㉧', '㉨', '㉩',
                         'Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ', 'Ⅵ', 'Ⅶ', 'Ⅷ', 'Ⅸ', 'Ⅹ']
                         
        # 기존 글머리 기호 앞에 공백 추가
        for marker in bullet_markers:
            if text.startswith(marker):
                text = ' ' + text
                break
                
        # 일반적인 글머리 기호 처리 - 글머리기호는 새줄에 추가
        if text.startswith('- ') or text.startswith('* ') or text.startswith('+ '):
            text = ' ' + text
            
        # 숫자 글머리 기호 처리 (예: "1. ", "1.1. " 등)
        if re.match(r'^\d+\.(\d+\.)?\s', text):
            text = ' ' + text
            
        # 알파벳 글머리 기호 처리 (예: "A. ", "a. " 등)
        if re.match(r'^[A-Za-z]\.(\d+\.)?\s', text):
            text = ' ' + text
            
        # 줄 끝의 불필요한 공백 제거
        text = text.rstrip()
        
        # 줄 바꿈 문자 정규화
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text

    def _split_long_text(self, text, max_length=60):
        sentences = []
        for paragraph in text.split('\n\n'):
            # 문장 단위로 분리 (마침표, 물음표, 느낌표 기준)
            for sentence in paragraph.replace('. ', '.\n').replace('? ', '?\n').replace('! ', '!\n').split('\n'):
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                # 문장이 max_length보다 길면 추가로 분리
                while len(sentence) > max_length:
                    # 공백을 기준으로 단어 분리
                    split_idx = sentence[:max_length].rfind(' ')
                    if split_idx == -1:  # 공백을 찾지 못한 경우
                        split_idx = max_length
                    sentences.append(sentence[:split_idx].strip())
                    sentence = sentence[split_idx:].strip()
                
                if sentence:  # 남은 문장 추가
                    sentences.append(sentence)
            
            # 문단 구분을 위해 빈 문장 추가
            sentences.append('')
        
        return sentences    

    def _join_broken_lines(self, lines):
        """잘린 문장을 하나로 합칩니다."""
        result = []
        current = []
        
        for line in lines:
            stripped = self._preprocess_text(line)
            if not stripped:
                if current:
                    result.append(' '.join(current))
                    current = []
                result.append('')
            elif line[0].isspace() and current:  # 들여쓰기된 줄이 이어지는 경우
                current.append(stripped)
            else:
                if current:
                    # 마지막 단어가 잘린 것 같은 경우 현재 줄과 합치기
                    last_word = current[-1].split()[-1]
                    if not any(current[-1].endswith(end) for end in ['다.', '까?', '요.', '임.', '됨.', '함.', '다']) and \
                    (len(last_word) >= 2 and not last_word[-1].isalnum() or \
                        current[-1][-1] in [',', '.'] or \
                        len(current[-1]) > 60):  # 긴 문장은 이어질 가능성이 높음
                        current.append(stripped)
                    else:
                        result.append(' '.join(current))
                        current = [stripped]
                else:
                    if stripped.endswith(('다.', '까?', '요.', '임.', '됨.', '함.', '다')) and len(stripped) < 60:
                        result.append(stripped)
                    else:
                        current = [stripped]
        
        if current:
            result.append(' '.join(current))
        
        # 불필요한 공백 제거
        result = [line.strip() for line in result]
        
        # 빈 줄이 연속되지 않도록
        final_result = []
        prev_empty = True
        
        for line in result:
            if line or not prev_empty:
                final_result.append(line)
            prev_empty = not line
        
        return final_result

    def _normalize_content(self, content):
        """파일 내용을 정규화합니다."""
        # 모든 줄의 끝에 있는 공백 제거
        lines = [line.rstrip() for line in content.split('\n')]
        
        # 빈 줄 처리
        result = []
        prev_empty = True  # 시작 부분의 빈 줄 제거를 위해
        
        # 잘린 문장 합치기
        lines = self._join_broken_lines(lines)
        
        for line in lines:
            # 현재 줄이 비어있는지 확인
            is_empty = not line.strip()
            
            # 빈 줄이 연속되지 않도록 처리
            if is_empty:
                if not prev_empty:
                    result.append('')
                prev_empty = True
            else:
                # 실제 내용이 있는 줄 처리
                stripped = line.strip()
                # 들여쓰기가 있는 경우 4칸으로 통일
                if line[0].isspace():
                    result.append('    ' + stripped)
                else:
                    result.append(stripped)
                prev_empty = False
        
        # 마지막 빈 줄 제거
        while result and not result[-1]:
            result.pop()
        
        return '\n'.join(result)

    def add_heading(self, text, **kwargs):
        """
        제목 스타일의 문단을 추가합니다. 모든 제목은 동일한 스타일(14pt, 굵게)로 적용됩니다.
        """
        self.elements.append(('heading', text, False))
        self.has_title = True  # 제목이 추가되었음을 표시
        
    def add_paragraph(self, text):
        """
        문단을 추가합니다. 여러 줄의 텍스트인 경우 자동으로 add_text_content를 호출합니다.
        긴 텍스트는 자동으로 분리되어 여러 문단으로 추가됩니다.
        
        Args:
            text (str): 추가할 텍스트 (단일 또는 여러 줄)
        """
        if not text:  # 빈 텍스트 처리
            return
            
        text = str(text).strip()
        
        # 여러 줄의 텍스트인지 확인
        if '\n' in text:
            # 여러 줄이면 add_text_content 호출
            text = self._normalize_content(text)
            self.add_text_content(text)
        else:
            # 단일 줄이면 기존 로직 수행
            if text in ['<그림>', '<표>']:  # 특수 마커 처리
                return
                
            # 제목이 없는 경우 처리
            if not self.has_title:
                self.add_heading(text)
                self.has_title = True
                return
            
            # 특수문자와 글머리 기호 처리
            processed_text = self._preprocess_text(text)
            
            # 긴 텍스트 처리
            if len(processed_text) > 60:  # 60자 이상인 경우
                for sentence in self._split_long_text(processed_text):
                    if sentence.strip():
                        self.elements.append(('paragraph', sentence.strip(), False))
            else:
                self.elements.append(('paragraph', processed_text, False))

    def add_text_content(self, text):
        """
        여러 줄의 텍스트 내용을 자동으로 처리하여 추가합니다.
        각 문단은 빈 줄로 구분되며, 긴 문단은 자동으로 분리됩니다.
        
        Args:
            text (str): 추가할 텍스트 내용 (여러 줄 가능)
        """
        if not text:
            return
            
        # 전체 텍스트 전처리
        text = self._preprocess_text(text)
        text = self._normalize_content(text)        
        
        # 빈 줄을 기준으로 문단 분리
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:  # 빈 문단 건너뛰기
                continue
                
            # 특수 마커 처리
            if paragraph in ['<그림>', '<표>']:
                continue
                
            # 제목이 없는 경우 처리
            if not self.has_title:
                self.add_heading(paragraph)
                self.has_title = True
                continue
            
            # 제목으로 시작하는 경우 처리
            if paragraph.startswith('제'):
                self.add_heading(paragraph)
                continue
            
            # 긴 문단 처리
            if len(paragraph) > 60:
                for sentence in self._split_long_text(paragraph):
                    if sentence.strip():
                        self.elements.append(('paragraph', sentence.strip(), False))
            else:
                self.elements.append(('paragraph', paragraph, False))
            
            # 문단 사이에 빈 줄 추가
            self.elements.append(('paragraph', '', False))

    def add_page_break(self):
        """
        빈 문단과 함께 페이지 넘김을 추가합니다.
        """
        self.elements.append(('paragraph', '', True))

    def add_image(self, image):
        """Add an image to the document.
        
        Args:
            image: Can be:
                - str: Path to image file or URL
                - bytes: Binary image data
                - PIL.Image: PIL Image object
        """
        import tempfile
        from PIL import Image
        import io
        import os
        import urllib.parse
        import sys
        
        try:
            temp_img = None
            
            # Check if input is PIL Image
            if hasattr(image, 'mode') and hasattr(image, 'save'):
                # Handle PIL Image
                img_obj = convert_image_to_rgb(image)
                
                # Save to temporary file
                temp_fd, temp_img = tempfile.mkstemp(suffix='.jpg')
                os.close(temp_fd)
                img_obj.save(temp_img, 'JPEG', quality=95)
                self._temp_files.append(temp_img)
                
            # Check if input is bytes
            elif isinstance(image, bytes):
                try:
                    # Handle binary data
                    img_obj = Image.open(io.BytesIO(image))
                    img_obj = convert_image_to_rgb(img_obj)
                    
                    # Save to temporary file
                    temp_fd, temp_img = tempfile.mkstemp(suffix='.jpg')
                    os.close(temp_fd)
                    img_obj.save(temp_img, 'JPEG', quality=95)
                    self._temp_files.append(temp_img)
                except:
                    # SVG 처리 시도
                    try:
                        temp_fd, temp_img = tempfile.mkstemp(suffix='.jpg')
                        os.close(temp_fd)
                        cairosvg.svg2png(bytestring=image, write_to=temp_img)
                        self._temp_files.append(temp_img)
                    except Exception as svg_error:
                        print(f"[WARNING] SVG 처리 실패: {str(svg_error)}")
                        return
                
            # Check if input is URL
            elif isinstance(image, str) and urllib.parse.urlparse(image).scheme in ('http', 'https'):
                # SVG URL인 경우 처리
                if image.lower().endswith('.svg'):
                    try:
                        # SVG를 PNG로 변환
                        temp_fd, temp_img = tempfile.mkstemp(suffix='.jpg')
                        os.close(temp_fd)
                        cairosvg.svg2png(url=image, write_to=temp_img)
                        self._temp_files.append(temp_img)
                    except Exception as svg_error:
                        print(f"[WARNING] SVG URL 처리 실패: {str(svg_error)}")
                        return
                else:
                    # 일반 이미지 URL 처리
                    img_data = read_url(image)
                    if not img_data:
                        raise Exception("Failed to download image from URL: %s" % image)
                    
                    # Convert to PIL Image
                    img_obj = Image.open(io.BytesIO(img_data))
                    img_obj = convert_image_to_rgb(img_obj)
                    
                    # Save to temporary file
                    temp_fd, temp_img = tempfile.mkstemp(suffix='.jpg')
                    os.close(temp_fd)
                    img_obj.save(temp_img, 'JPEG', quality=95)
                    self._temp_files.append(temp_img)
                
            # Handle local file path
            elif isinstance(image, str):
                # SVG 파일인 경우 처리
                if image.lower().endswith('.svg'):
                    try:
                        temp_fd, temp_img = tempfile.mkstemp(suffix='.jpg')
                        os.close(temp_fd)
                        cairosvg.svg2png(url=image, write_to=temp_img)
                        self._temp_files.append(temp_img)
                    except Exception as svg_error:
                        print(f"[WARNING] SVG 파일 처리 실패: {str(svg_error)}")
                        return
                else:
                    # Get various base directories
                    current_file_dir = os.path.dirname(os.path.abspath(__file__))
                    workspace_root = os.path.dirname(current_file_dir)
                    cwd = os.getcwd()
                    
                    # If running from script, get script directory
                    if sys.argv[0] and sys.argv[0] != '-c':
                        script_path = os.path.abspath(sys.argv[0])
                        script_dir = os.path.dirname(script_path)
                    else:
                        script_dir = cwd
                    
                    # Try different path resolutions in order of priority
                    base_paths = {
                        cwd: "현재 작업 디렉토리",
                        script_dir: "스크립트 디렉토리",
                        workspace_root: "워크스페이스 루트",
                        current_file_dir: "utils.py 디렉토리"
                    }
                    
                    possible_paths = []
                    tried_paths = set()  # 중복 체크를 위한 set
                    
                    # 1. 먼저 주어진 경로 그대로 시도
                    if os.path.isabs(image):
                        if image not in tried_paths:
                            possible_paths.append((image, "절대 경로"))
                            tried_paths.add(image)
                    else:
                        # 2. 각 기준 디렉토리에서 상대 경로로 시도
                        for base_dir, desc in base_paths.items():
                            full_path = os.path.normpath(os.path.join(base_dir, image))
                            if full_path not in tried_paths:
                                possible_paths.append((full_path, desc))
                                tried_paths.add(full_path)
                    
                    # Try each path
                    temp_img = None
                    paths_tried = []
                    
                    for path, desc in possible_paths:
                        paths_tried.append(f"{path} ({desc})")
                        if os.path.exists(path):
                            # 이미지를 열고 RGB로 변환
                            img_obj = Image.open(path)
                            img_obj = convert_image_to_rgb(img_obj)
                            
                            # 임시 파일로 저장
                            temp_fd, temp_img = tempfile.mkstemp(suffix='.jpg')
                            os.close(temp_fd)
                            img_obj.save(temp_img, 'JPEG', quality=95)
                            self._temp_files.append(temp_img)
                            break
                    
                    if temp_img is None:
                        raise FileNotFoundError("이미지 파일을 찾을 수 없습니다: %s\n시도한 경로들:\n%s" % 
                                             (image, "\n".join(f"- {p}" for p in paths_tried)))
            
            else:
                raise ValueError("Unsupported image type. Must be file path, URL, bytes, or PIL Image")
            
            # Add image to document
            if temp_img and os.path.exists(temp_img):
                self.elements.append(('image', temp_img, False))
            
        except Exception as e:
            if temp_img and temp_img not in self._temp_files:
                try:
                    os.remove(temp_img)
                except:
                    pass
            print(f"[WARNING] Image processing failed: {str(e)}")
    
    def add_table(self, data, header=None, page_break=False):
        """
        표를 추가합니다.
        :param data: 2차원 리스트 형태의 표 데이터 ([[cell1, cell2], [cell3, cell4]] 형식)
        :param header: 헤더 행 데이터 (옵션)
        :param page_break: True이면 이 표 다음에 페이지 넘김을 추가합니다.
        """
        if not data:
            raise ValueError("표 데이터가 비어있습니다.")
        
        # 헤더가 있는 경우 데이터 앞에 추가
        if header:
            table_data = [header] + data
        else:
            table_data = data

        # 모든 행의 길이가 동일한지 확인
        row_lengths = set(len(row) for row in table_data)
        if len(row_lengths) != 1:
            raise ValueError("모든 행의 길이가 동일해야 합니다.")
        
        self.elements.append(('table', table_data, page_break))

    def save(self, output_path):
        """Save the document and cleanup temporary files."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # 템플릿 파일 압축 해제
                with zipfile.ZipFile(self.template_path, 'r') as template_zip:
                    template_zip.extractall(temp_dir)

                # header.xml 파일 수정 (기존 코드 유지)
                header_path = os.path.join(temp_dir, 'Contents', 'header.xml')
                with open(header_path, 'r', encoding='utf-8') as f:
                    header_content = f.read()

                # charProperties 섹션 찾기 및 수정 (기존 코드 유지)
                char_props_start = header_content.find('<hh:charProperties')
                char_props_end = header_content.find('</hh:charProperties>')
                
                if char_props_start == -1 or char_props_end == -1:
                    raise ValueError("header.xml 파일의 구조가 올바르지 않습니다.")

                # 새로운 글자 모양 정의 (기존 코드 유지)
                char_props = '''<hh:charProperties itemCnt="9">
                    <hh:charPr id="0" height="1000" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
                        <hh:fontRef hangul="2" latin="2" hanja="2" japanese="2" other="2" symbol="2" user="2"/>
                        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                    </hh:charPr>
                    <hh:charPr id="1" height="1000" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
                        <hh:fontRef hangul="1" latin="1" hanja="1" japanese="1" other="1" symbol="1" user="1"/>
                        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                    </hh:charPr>
                    <hh:charPr id="2" height="900" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
                        <hh:fontRef hangul="1" latin="1" hanja="1" japanese="1" other="1" symbol="1" user="1"/>
                        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                    </hh:charPr>
                    <hh:charPr id="3" height="900" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
                        <hh:fontRef hangul="2" latin="2" hanja="2" japanese="2" other="2" symbol="2" user="2"/>
                        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                    </hh:charPr>
                    <hh:charPr id="4" height="900" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
                        <hh:fontRef hangul="1" latin="1" hanja="1" japanese="1" other="1" symbol="1" user="1"/>
                        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:spacing hangul="-5" latin="-5" hanja="-5" japanese="-5" other="-5" symbol="-5" user="-5"/>
                        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                    </hh:charPr>
                    <hh:charPr id="5" height="1600" textColor="#2E74B5" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
                        <hh:fontRef hangul="1" latin="1" hanja="1" japanese="1" other="1" symbol="1" user="1"/>
                        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                    </hh:charPr>
                    <hh:charPr id="6" height="1100" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
                        <hh:fontRef hangul="1" latin="1" hanja="1" japanese="1" other="1" symbol="1" user="1"/>
                        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                    </hh:charPr>
                    <hh:charPr id="7" height="1000" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
                        <hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                    </hh:charPr>
                    <hh:charPr id="8" height="1400" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" symMark="NONE" borderFillIDRef="2">
                        <hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>
                        <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>
                        <hh:bold/>
                    </hh:charPr>
                </hh:charProperties>'''

                # charProperties 섹션 전체 교체
                header_content = (
                    header_content[:char_props_start] + 
                    char_props +
                    header_content[char_props_end + len('</hh:charProperties>'):]
                )

                # borderFills 섹션 찾기
                border_fills_start = header_content.find('<hh:borderFills')
                border_fills_end = header_content.find('</hh:borderFills>')
                
                if border_fills_start == -1 or border_fills_end == -1:
                    raise ValueError("header.xml 파일의 구조가 올바르지 않습니다.")

                # 새로운 테두리 스타일 정의
                border_fills = '''<hh:borderFills itemCnt="3">
                    <hh:borderFill id="1" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">
                        <hh:slash type="NONE" Crooked="0" isCounter="0"/>
                        <hh:backSlash type="NONE" Crooked="0" isCounter="0"/>
                        <hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>
                        <hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>
                        <hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>
                        <hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>
                        <hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>
                    </hh:borderFill>
                    <hh:borderFill id="2" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">
                        <hh:slash type="NONE" Crooked="0" isCounter="0"/>
                        <hh:backSlash type="NONE" Crooked="0" isCounter="0"/>
                        <hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>
                        <hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>
                        <hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>
                        <hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>
                        <hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>
                        <hc:fillBrush>
                            <hc:winBrush faceColor="none" hatchColor="#999999" alpha="0"/>
                        </hc:fillBrush>
                    </hh:borderFill>
                    <hh:borderFill id="3" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">
                        <hh:slash type="NONE" Crooked="0" isCounter="0"/>
                        <hh:backSlash type="NONE" Crooked="0" isCounter="0"/>
                        <hh:leftBorder type="SOLID" width="0.12 mm" color="#000000"/>
                        <hh:rightBorder type="SOLID" width="0.12 mm" color="#000000"/>
                        <hh:topBorder type="SOLID" width="0.12 mm" color="#000000"/>
                        <hh:bottomBorder type="SOLID" width="0.12 mm" color="#000000"/>
                        <hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>
                    </hh:borderFill>
                </hh:borderFills>'''

                # borderFills 섹션 전체 교체
                header_content = (
                    header_content[:border_fills_start] + 
                    border_fills +
                    header_content[border_fills_end + len('</hh:borderFills>'):]
                )

                # 수정된 header.xml 저장
                with open(header_path, 'w', encoding='utf-8') as f:
                    f.write(header_content)

                # 이미지 처리를 위한 준비
                bindata_dir = os.path.join(temp_dir, 'BinData')
                contents_dir = os.path.join(temp_dir, 'Contents')
                preview_dir = os.path.join(temp_dir, 'Preview')
                
                # 필요한 모든 디렉토리 생성
                for directory in [bindata_dir, contents_dir, preview_dir]:
                    os.makedirs(directory, exist_ok=True)
                
                manifest_items = []
                image_count = 0

                # content.hpf 파일 수정 준비
                content_hpf_path = os.path.join(temp_dir, 'Contents', 'content.hpf')
                with open(content_hpf_path, 'r', encoding='utf-8') as f:
                    content_hpf = f.read()

                # 기존 이미지 항목 제거
                manifest_start = content_hpf.find('<opf:manifest>')
                manifest_end = content_hpf.find('</opf:manifest>')
                if manifest_start == -1 or manifest_end == -1:
                    raise ValueError("content.hpf 파일 구조가 올바르지 않습니다.")

                # 기본 manifest 항목
                manifest_items.append('''<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>
<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>
<opf:item id="settings" href="settings.xml" media-type="application/xml"/>''')

                # Section0.xml 파일 수정
                section_path = os.path.join(temp_dir, 'Contents', 'section0.xml')
                with open(section_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 본문 시작 위치 찾기
                body_start = content.find('<hs:sec')
                body_end = content.find('</hs:sec>')
                if body_start == -1 or body_end == -1:
                    raise ValueError("문서 구조가 올바르지 않습니다.")
                
                # 기존 문서의 기본 설정 추출
                first_p_start = content.find('<hp:p', body_start)
                first_p_end = content.find('</hp:p>', first_p_start) + len('</hp:p>')
                if first_p_start == -1 or first_p_end == -1:
                    raise ValueError("문서 구조가 올바르지 않습니다.")

                # XML 네임스페이스와 기본 설정 보존
                header = content[body_start:first_p_end]
                
                # 새로운 본문 내용 생성
                new_body = header
                
                # 요소 순서대로 처리
                for element_type, content_data, page_break, *extra in self.elements:  # *extra로 추가 매개변수 처리
                    if element_type == 'paragraph':
                        char_pr_id = extra[0] if extra else "0"  # extra가 있으면 첫 번째 값 사용, 없으면 기본값 "0"
                        paragraph_xml = f'''
                        <hp:p pageBreak="{1 if page_break else 0}" paraPrIDRef="0" styleIDRef="0">
                            <hp:pPr>
                                <hp:margin left="0" right="0" prev="0" next="850"/>
                            </hp:pPr>
                            <hp:run charPrIDRef="{char_pr_id}">
                                <hp:t>{content_data}</hp:t>
                            </hp:run>
                            <hp:linesegarray>
                                <hp:lineseg textpos="0" vertpos="0" vertsize="1000" textheight="1000" 
                                           baseline="850" spacing="1000" horzpos="0" horzsize="42520" 
                                           flags="393216"/>
                            </hp:linesegarray>
                        </hp:p>'''
                        new_body += paragraph_xml
                    
                    elif element_type == 'heading':
                        # 제목 문단 추가
                        heading_xml = f'''
                        <hp:p pageBreak="{1 if page_break else 0}" paraPrIDRef="0" styleIDRef="0">
                            <hp:pPr>
                                <hp:margin left="0" right="0" prev="850" next="850"/>
                            </hp:pPr>
                            <hp:run charPrIDRef="8">
                                <hp:t>{content_data}</hp:t>
                            </hp:run>
                            <hp:linesegarray>
                                <hp:lineseg textpos="0" vertpos="1600" vertsize="1400" textheight="1400" 
                                           baseline="1190" spacing="840" horzpos="0" horzsize="42520" 
                                           flags="393216"/>
                            </hp:linesegarray>
                        </hp:p>'''
                        new_body += heading_xml
                    
                    elif element_type == 'image':
                        # 이미지 처리
                        image_count += 1
                        image_path = content_data
                        
                        # 이미지 파일 복사 및 변환
                        img = Image.open(image_path)
                        # RGBA나 P 모드인 경우 RGB로 변환
                        if img.mode in ('RGBA', 'P', 'LA'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode in ('RGBA', 'LA'):
                                background.paste(img, mask=img.split()[-1])
                            else:
                                background.paste(img)
                            img = background
                        elif img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # 원본 이미지 확장자 유지
                        _, ext = os.path.splitext(image_path)
                        img_filename = f'image{image_count}{ext.lower()}'
                        img.save(os.path.join(bindata_dir, img_filename))

                        # 이미지 크기 계산 (A4 용지 기준 적절한 크기로 조정)
                        img_width, img_height = img.size
                        width = 41550  # A4 용지 너비에 맞춤
                        height = int(width * (img_height / img_width))

                        # content.hpf에 이미지 항목 추가
                        media_type = f"image/{ext[1:].lower()}"
                        manifest_items.append(
                            f'<opf:item id="image{image_count}" href="BinData/{img_filename}" '
                            f'media-type="{media_type}" isEmbeded="1"/>'
                        )

                        # 이미지 문단 추가
                        image_xml = f'''
                        <hp:p pageBreak="{1 if page_break else 0}" paraPrIDRef="0" styleIDRef="0">
                            <hp:pPr>
                                <hp:margin left="0" right="0" prev="850" next="850"/>
                            </hp:pPr>
                            <hp:run charPrIDRef="7">
                                <hp:pic id="{1000000 + image_count}" zOrder="{image_count}" 
                                       numberingType="PICTURE" textWrap="SQUARE" textFlow="BOTH_SIDES" 
                                       lock="0" dropcapstyle="None" href="" groupLevel="0" 
                                       instid="{682337706 + image_count}" reverse="0">
                                    <hp:offset x="0" y="0"/>
                                    <hp:orgSz width="{width}" height="{height}"/>
                                    <hp:curSz width="0" height="0"/>
                                    <hp:flip horizontal="0" vertical="0"/>
                                    <hp:rotationInfo angle="0" centerX="{width//2}" centerY="{height//2}" 
                                                    rotateimage="1"/>
                                    <hp:renderingInfo>
                                        <hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>
                                        <hc:scaMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>
                                        <hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>
                                    </hp:renderingInfo>
                                    <hp:imgRect>
                                        <hc:pt0 x="0" y="0"/>
                                        <hc:pt1 x="{width}" y="0"/>
                                        <hc:pt2 x="{width}" y="{height}"/>
                                        <hc:pt3 x="0" y="{height}"/>
                                    </hp:imgRect>
                                    <hp:imgClip left="0" right="96000" top="0" bottom="77400"/>
                                    <hp:inMargin left="0" right="0" top="0" bottom="0"/>
                                    <hc:img binaryItemIDRef="image{image_count}" bright="0" contrast="0" 
                                           effect="REAL_PIC" alpha="0"/>
                                    <hp:effects/>
                                    <hp:sz width="{width}" widthRelTo="ABSOLUTE" height="{height}" 
                                          heightRelTo="ABSOLUTE" protect="0"/>
                                    <hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="1" 
                                           allowOverlap="1" holdAnchorAndSO="0" vertRelTo="PARA" 
                                           horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" 
                                           vertOffset="0" horzOffset="0"/>
                                    <hp:outMargin left="0" right="0" top="0" bottom="0"/>
                                    <hp:shapeComment>그림입니다.</hp:shapeComment>
                                </hp:pic>
                            </hp:run>
                            <hp:linesegarray>
                                <hp:lineseg textpos="0" vertpos="0" vertsize="1000" textheight="1000" 
                                           baseline="850" spacing="600" horzpos="0" horzsize="42520" 
                                           flags="393216"/>
                            </hp:linesegarray>
                        </hp:p>'''
                        new_body += image_xml

                    elif element_type == 'table':
                        # 표 데이터
                        table_data = content_data
                        row_count = len(table_data)
                        col_count = len(table_data[0])
                        
                        # 표 XML 시작
                        table_xml = f'''
                        <hp:p pageBreak="{1 if page_break else 0}" paraPrIDRef="0" styleIDRef="0">
                            <hp:run charPrIDRef="7">
                                <hp:tbl id="{1000000 + len(new_body)}" zOrder="0" numberingType="TABLE" 
                                       textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" 
                                       dropcapstyle="None" pageBreak="CELL" repeatHeader="1" 
                                       rowCnt="{row_count}" colCnt="{col_count}" cellSpacing="0" 
                                       borderFillIDRef="3" noAdjust="0">
                                    <hp:sz width="42520" widthRelTo="ABSOLUTE" height="5000" 
                                          heightRelTo="ABSOLUTE" protect="0"/>
                                    <hp:pos treatAsChar="0" affectLSpacing="0" flowWithText="1" 
                                           allowOverlap="1" holdAnchorAndSO="0" vertRelTo="PARA" 
                                           horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" 
                                           vertOffset="0" horzOffset="0"/>
                                    <hp:outMargin left="283" right="283" top="283" bottom="283"/>
                                    <hp:inMargin left="510" right="510" top="141" bottom="141"/>'''

                        # 각 행 추가
                        for row_idx, row in enumerate(table_data):
                            table_xml += '<hp:tr>'
                            for col_idx, cell in enumerate(row):
                                table_xml += f'''
                                    <hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" 
                                          dirty="0" borderFillIDRef="3">
                                        <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" 
                                                   vertAlign="CENTER" linkListIDRef="0" 
                                                   linkListNextIDRef="0" textWidth="0" textHeight="0" 
                                                   hasTextRef="0" hasNumRef="0">
                                            <hp:p paraPrIDRef="0" styleIDRef="0" pageBreak="0" 
                                                 columnBreak="0" merged="0">
                                                <hp:run charPrIDRef="0">
                                                    <hp:t>{str(cell)}</hp:t>
                                                </hp:run>
                                            </hp:p>
                                        </hp:subList>
                                        <hp:cellAddr colAddr="{col_idx}" rowAddr="{row_idx}"/>
                                        <hp:cellSpan colSpan="1" rowSpan="1"/>
                                        <hp:cellSz width="{42520 // col_count}" height="1000"/>
                                        <hp:cellMargin left="510" right="510" top="141" bottom="141"/>
                                    </hp:tc>'''
                            table_xml += '</hp:tr>'

                        # 표 XML 종료
                        table_xml += '''
                                </hp:tbl>
                            </hp:run>
                        </hp:p>'''
                        
                        new_body += table_xml

                new_body += '</hs:sec>'

                # 전체 내용 교체
                content = content[:body_start] + new_body

                # 수정된 내용 저장
                with open(section_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # content.hpf 파일 업데이트
                new_manifest = '<opf:manifest>\n' + '\n'.join(manifest_items) + '\n</opf:manifest>'
                content_hpf = (
                    content_hpf[:manifest_start] + 
                    new_manifest + 
                    content_hpf[manifest_end + len('</opf:manifest>'):]
                )
                with open(content_hpf_path, 'w', encoding='utf-8') as f:
                    f.write(content_hpf)

                # Preview/PrvText.txt 수정
                preview_text = '\n'.join(
                    content_data for type_, content_data, _ in self.elements 
                    if type_ == 'paragraph' and content_data
                )
                preview_path = os.path.join(temp_dir, 'Preview', 'PrvText.txt')
                with open(preview_path, 'w', encoding='utf-8') as f:
                    f.write(preview_text)

                # 새로운 HWPX 파일 생성
                with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as output_zip:
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_name = os.path.relpath(file_path, temp_dir)
                            output_zip.write(file_path, arc_name)

            return True
        except Exception as e:
            print(f"Error saving document: {str(e)}")
            return False

class PDFDocument:
    def __init__(self):
        try:
            self.font_path = safe_path_join(os.path.expanduser("~"), ".airun", "NotoSansKR-Regular.ttf")
            if not os.path.exists(self.font_path):
                raise FileNotFoundError(f"Font file not found: {self.font_path}")
            
            # 폰트 등록
            pdfmetrics.registerFont(TTFont('NotoSansKR', self.font_path))
            
            # 임시 PDF 생성
            self.buffer = io.BytesIO()
            self.pdf = canvas.Canvas(self.buffer, pagesize=A4)
            self.pdf.setFont('NotoSansKR', 10)
            
            # 페이지 크기 설정
            self.width, self.height = A4
            self.margin = 50  # 여백
            self.y = self.height - self.margin  # 현재 y 위치
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize PDF document: {str(e)}")
            raise
            
    def add_page(self):
        """Add a new page to the PDF document."""
        self.pdf.showPage()
        self.pdf.setFont('NotoSansKR', 10)
        self.y = self.height - self.margin
        
    def add_content(self, text: str):
        """Add text content to the current page."""
        if text is None or not isinstance(text, str):
            return
            
        try:
            # 텍스트 전처리
            text = text.strip().replace('\r\n', '\n').replace('\r', '\n')
            lines = text.split('\n')
            
            for line in lines:
                if line.strip():
                    # 페이지 넘김 확인
                    if self.y < self.margin:
                        self.add_page()
                    
                    self.pdf.drawString(self.margin, self.y, line.strip())
                    self.y -= 15  # 줄간격
                else:
                    self.y -= 15  # 빈 줄
                    
        except Exception as e:
            print(f"[WARNING] Failed to add content: {str(e)}")
            
    def add_text(self, text: str):
        """Add text content to the current page."""
        self.add_content(text)
        
    def add_title(self, title: str):
        """Add a title to the current page."""
        if title is None or not isinstance(title, str):
            return
            
        try:
            title = title.strip()
            self.pdf.setFont('NotoSansKR', 16)
            
            # 중앙 정렬을 위한 텍스트 너비 계산
            text_width = self.pdf.stringWidth(title, 'NotoSansKR', 16)
            x = (self.width - text_width) / 2
            
            self.pdf.drawString(x, self.y, title)
            self.y -= 30  # 제목 후 여백
            
            self.pdf.setFont('NotoSansKR', 10)
        except Exception as e:
            print(f"[WARNING] Failed to add title: {str(e)}")
            
    def add_subtitle(self, subtitle: str):
        """Add a subtitle to the current page."""
        if subtitle is None or not isinstance(subtitle, str):
            return
            
        try:
            subtitle = subtitle.strip()
            self.pdf.setFont('NotoSansKR', 14)
            self.pdf.drawString(self.margin, self.y, subtitle)
            self.y -= 25  # 부제목 후 여백
            
            self.pdf.setFont('NotoSansKR', 10)
        except Exception as e:
            print(f"[WARNING] Failed to add subtitle: {str(e)}")
            
    def add_image(self, image_path: str, x: float = None, y: float = None, w: float = 0, h: float = 0):
        """Add an image to the PDF document.
        
        Args:
            image_path: Path to image file or URL
            x: X coordinate (if None, will be centered)
            y: Y coordinate (if None, will use current y position)
            w: Width in points (if 0, will use scaled image width)
            h: Height in points (if 0, will use scaled image height)
        """
        try:
            img_temp = None
            temp_path = None
            
            # URL인 경우 다운로드
            if isinstance(image_path, str) and urllib.parse.urlparse(image_path).scheme in ('http', 'https'):
                # SVG URL인 경우 처리
                if image_path.lower().endswith('.svg'):
                    try:
                        temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
                        os.close(temp_fd)
                        cairosvg.url_to_png(url=image_path, write_to=temp_path)
                        image_path = temp_path
                    except Exception as svg_error:
                        print(f"[WARNING] SVG URL 처리 실패: {str(svg_error)}")
                        return
                else:
                    response = requests.get(image_path)
                    if response.status_code != 200:
                        raise Exception(f"Failed to download image: {response.status_code}")
                    img_data = response.content
                    img_temp = Image.open(io.BytesIO(img_data))
                    img_temp = convert_image_to_rgb(img_temp)
            # 로컬 파일인 경우
            else:
                # SVG 파일인 경우 처리
                if image_path.lower().endswith('.svg'):
                    try:
                        temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
                        os.close(temp_fd)
                        cairosvg.svg2png(url=image_path, write_to=temp_path)
                        image_path = temp_path
                        img_temp = Image.open(temp_path)
                    except Exception as svg_error:
                        print(f"[WARNING] SVG 파일 처리 실패: {str(svg_error)}")
                        return
                else:
                    img_temp = Image.open(image_path)
                    img_temp = convert_image_to_rgb(img_temp)
            
            # 이미지가 없는 경우 처리
            if not img_temp and not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            # 이미지 크기 계산
            if not img_temp:
                img_temp = Image.open(image_path)
                img_temp = convert_image_to_rgb(img_temp)
            
            # 픽셀 크기를 포인트로 변환 (PDF 포인트는 1/72 인치)
            POINTS_PER_INCH = 72.0
            
            # 이미지의 실제 크기를 계산 (픽셀)
            img_w_px, img_h_px = img_temp.size
            
            # 기본 크기 계산 (픽셀을 포인트로 변환)
            img_w = img_w_px * POINTS_PER_INCH / 96  # 96 DPI를 기준으로 변환
            img_h = img_h_px * POINTS_PER_INCH / 96
            
            # 크기가 지정되지 않은 경우 원본 크기 사용 (최대 페이지 너비의 90%로 제한)
            if w == 0 and h == 0:
                max_w = (self.width - 2 * self.margin) * 0.9
                if img_w > max_w:
                    scale = max_w / img_w
                    w = img_w * scale
                    h = img_h * scale
                else:
                    w = img_w
                    h = img_h
            # 너비만 지정된 경우 비율 유지
            elif h == 0 and w > 0:
                h = w * (img_h / img_w)
            # 높이만 지정된 경우 비율 유지
            elif w == 0 and h > 0:
                w = h * (img_w / img_h)
            
            # x 좌표가 지정되지 않은 경우 중앙 정렬
            if x is None:
                x = (self.width - w) / 2
            else:
                x = max(self.margin, min(x, self.width - self.margin - w))
            
            # y 좌표가 지정되지 않은 경우 현재 위치 사용
            if y is None:
                # 이미지 위에 여백 추가
                self.y -= 20
                y = self.y - h
            
            # 이미지가 페이지를 벗어나는지 확인
            if y < self.margin:
                self.add_page()
                # 새 페이지의 상단에 여백을 두고 시작
                y = self.height - self.margin - h - 20
            
            # 이미지 추가
            if temp_path:
                self.pdf.drawImage(temp_path, x, y, w, h)
                os.unlink(temp_path)  # 임시 파일 삭제
            else:
                # 임시 파일로 저장
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    img_temp.save(temp_file.name, 'JPEG', quality=95)
                    
                    # PDF에 이미지 추가
                    self.pdf.drawImage(temp_file.name, x, y, w, h)
                    
                # 임시 파일 삭제
                os.unlink(temp_file.name)
            
            # 현재 y 위치 업데이트 (이미지 아래에 여백 추가)
            self.y = y - 30
            
        except Exception as e:
            print(f"[WARNING] Failed to add image: {str(e)}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass

    def save(self, filename: str):
        """Save the PDF document to a file."""
        try:
            # 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
            
            # PDF 저장
            self.pdf.save()
            
            # 파일로 저장
            with open(filename, 'wb') as f:
                f.write(self.buffer.getvalue())
                
        except Exception as e:
            print(f"[ERROR] Failed to save PDF: {str(e)}")
            raise

# ============================================================================
# 파일 시스템 기본 유틸리티 (File System Core Utilities)
# ============================================================================

def normalize_path(path: str) -> str:
    """
    Normalize file path by handling spaces, special characters, and user paths.
    파일 경로의 공백, 특수문자, 사용자 경로를 처리합니다.
    """
    # print("\n[DEBUG] normalize_path 시작")
    # print(f"[DEBUG] 입력된 경로: '{path}'")
    
    # Expand user path (~/...)
    expanded_path = os.path.expanduser(path)
    # print(f"[DEBUG] 확장된 경로: '{expanded_path}'")
    
    # Handle spaces and special characters
    parts = expanded_path.split('/')
    # print(f"[DEBUG] 경로 분할: {parts}")
    
    normalized_parts = []
    for part in parts:
        if part:  # Skip empty parts
            # print(f"[DEBUG] 처리 전 부분: '{part}'")
            # Escape spaces and special characters
            escaped_part = part.replace(" ", "\\ ").replace("(", "\\(").replace(")", "\\)")
            # print(f"[DEBUG] 처리 후 부분: '{escaped_part}'")
            normalized_parts.append(escaped_part)
    
    final_path = "/" + "/".join(normalized_parts)
    # print(f"[DEBUG] 최종 경로: '{final_path}'")
    
    return final_path

def safe_path_join(*paths: str) -> str:
    """
    Safely join path components, escaping special characters.
    안전하게 경로를 결합하고 특수문자를 이스케이프 처리합니다.
        
        Args:
        *paths: Path components to join
                결합할 경로들
        
    Returns:
        str: Normalized and escaped joined path
             정규화되고 이스케이프된 결합 경로
    """
    # print("\n[DEBUG] safe_path_join 시작")
    # print(f"[DEBUG] 입력된 경로들: {paths}")
    
    # 경로 컴포넌트 처리
    processed_paths = []
    for path in paths:
        path_str = str(path)
        # print(f"[DEBUG] 처리 전 경로: '{path_str}'")
        
        # 홈 디렉토리 처리
        if path_str.startswith('~'):
            path_str = os.path.expanduser(path_str)
            # print(f"[DEBUG] 홈 디렉토리 확장: '{path_str}'")
            
        processed_paths.append(path_str)
    
    # print(f"[DEBUG] 처리된 경로들: {processed_paths}")
    
    # 경로 결합
    final_path = os.path.join(*processed_paths)
    # print(f"[DEBUG] 최종 경로: '{final_path}'")
    
    return final_path

def list_directory(path: str) -> List[str]:
    """
    Return a list of files and folders in the directory.
    디렉토리의 파일/폴더 목록을 반환합니다.
    
    Args:
        path (str): Path to the directory to scan
               탐색할 디렉토리 경로
        
    Returns:
        List[str]: List of file and folder names
                  파일과 폴더 이름 목록
        
    Raises:
        FileNotFoundError: If the directory does not exist
                          디렉토리가 존재하지 않는 경우
        PermissionError: If there is no access permission
                        디렉토리 접근 권한이 없는 경우
    """
    return os.listdir(path)

def read_file(path: str) -> Union[str, pd.DataFrame, bytes]:
    """
    Read and return the contents of a file based on its extension.
    파일 확장자에 따라 내용을 읽어 반환합니다.
    """
    # print(f"\n[INFO] Reading file: {path}")
    file_ext = os.path.splitext(path)[1].lower()
    
    try:
        # Convert to raw path
        raw_path = os.path.expanduser(path)
        # print(f"[DEBUG] Raw path: '{raw_path}'")
        
        if not os.path.exists(raw_path):
            # print(f"[ERROR] File not found: {raw_path}")
            raise FileNotFoundError(f"File not found: {raw_path}")

        # Office 문서, PDF, HWP 처리
        if file_ext in ['.doc', '.docx']:
            return extract_from_doc(raw_path)
        elif file_ext in ['.ppt', '.pptx']:
            return extract_from_ppt(raw_path)
        elif file_ext == '.pdf':
            return extract_from_pdf(raw_path)
        elif file_ext in ['.hwp', '.hwpx']:
            return convert_hwp_to_text(raw_path)

        # Pandas-supported files
        PANDAS_EXTENSIONS = {
            '.xlsx': pd.read_excel,  # Excel files
            '.xls': pd.read_excel,
            '.csv': pd.read_csv,     # CSV files
            '.json': pd.read_json,   # JSON files
            '.html': pd.read_html,   # HTML files
            '.xml': pd.read_xml,     # XML files
            '.parquet': pd.read_parquet,  # Parquet files
            '.feather': pd.read_feather,  # Feather files
            '.pickle': pd.read_pickle,    # Pickle files
            '.sql': pd.read_sql,     # SQL files
            '.hdf': pd.read_hdf,     # HDF5 files
            '.sas': pd.read_sas,     # SAS files
            '.stata': pd.read_stata,  # Stata files
            '.spss': pd.read_spss    # SPSS files
        }
        
        if file_ext in PANDAS_EXTENSIONS:
            # print(f"[INFO] Detected pandas-supported file ({file_ext})")
            return pd.read_excel(raw_path)
                    
        # Text files
        TEXT_EXTENSIONS = ['.txt', '.log', '.yaml', '.yml', '.md', '.cfg', '.conf']
        if file_ext in TEXT_EXTENSIONS:
            # print("[INFO] Detected text file")
            with open(raw_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        # Binary files
        BINARY_EXTENSIONS = [
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
            # Audio
            '.mp3', '.wav', '.ogg', '.flac',
            # Video
            '.mp4', '.avi', '.mkv', '.mov',
            # Archives
            '.zip', '.rar', '.7z', '.tar', '.gz'
        ]
        
        if file_ext in BINARY_EXTENSIONS:
            # print(f"[INFO] Detected binary file ({file_ext})")
            with open(raw_path, 'rb') as f:
                return f.read()
                
        # Unknown files
        # print("[WARNING] Unknown file type, attempting to read as text")
        try:
            with open(raw_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # print("[INFO] File is binary, reading as bytes")
            with open(raw_path, 'rb') as f:
                return f.read()
                
    except Exception as e:
        print(f"[ERROR] Failed to read file: {str(e)}")
        raise

def write_file(path: str, content: Union[str, pd.DataFrame, bytes], mode: str = 'w', encoding: str = 'utf-8') -> None:
    """
    Write content to a file based on its type and extension.
    내용을 파일 형식에 맞게 저장합니다.
    
    Args:
        path (str): Path to write the file to
        content (Union[str, pd.DataFrame, bytes]): Content to write
        mode (str, optional): File open mode ('w', 'a', 'wb', 'ab'). Defaults to 'w'
        encoding (str, optional): Text encoding. Defaults to 'utf-8'
    """
    file_ext = os.path.splitext(path)[1].lower()
    
    try:
        raw_path = os.path.expanduser(path)
        
        directory = os.path.dirname(raw_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        # HWPX 파일 처리
        if file_ext == '.hwpx':
            doc = HWPDocument()
            # 파일명을 제목으로 사용
            title = os.path.splitext(os.path.basename(raw_path))[0]
            # doc.add_heading("title")
            doc.add_heading("")
            
            if isinstance(content, str):
                doc.add_text_content(content)
            elif isinstance(content, pd.DataFrame):
                doc.add_table(data=content.values.tolist(), header=content.columns.tolist())
            else:
                raise ValueError("HWPX 파일 생성을 위해서는 문자열이나 DataFrame 형식의 데이터가 필요합니다.")
            doc.save(raw_path)
            return

        # PDF 파일 처리
        if file_ext == '.pdf':
            doc = PDFDocument()
            if isinstance(content, str):
                doc.add_content(content)
            elif isinstance(content, pd.DataFrame):
                # DataFrame을 텍스트 테이블 형식으로 변환
                table_str = content.to_string()
                doc.add_content(table_str)
            else:
                raise ValueError("PDF 파일 생성을 위해서는 문자열이나 DataFrame 형식의 데이터가 필요합니다.")
            doc.save(raw_path)
            return
            
        # DataFrame to text for .txt files
        if isinstance(content, pd.DataFrame) and file_ext == '.txt':
            content = content.to_string()
        
        # PDF 추출 텍스트 처리
        if isinstance(content, str) and file_ext == '.txt':
            # 인코딩 감지
            try:
                import chardet
                if not content.isprintable():  # 비인쇄 문자가 포함된 경우
                    encoding_detect = chardet.detect(content.encode())
                    detected_encoding = encoding_detect['encoding']
                    if detected_encoding and detected_encoding.lower() != 'utf-8':
                        content = content.encode(detected_encoding).decode('utf-8', errors='ignore')
            except ImportError:
                pass  # chardet가 없는 경우 기본 처리 사용
            
            # 비인쇄 문자 제거
            content = ''.join(char for char in content if char.isprintable() or char in ['\n', '\t', ' '])
        
        # Text content
        if isinstance(content, str):
            # 'wb' 또는 'ab' 모드인 경우 encoding 매개변수 제외
            if 'b' in mode:
                with open(raw_path, mode) as f:
                    f.write(content.encode(encoding))
            else:
                with open(raw_path, mode, encoding=encoding) as f:
                    f.write(content)
            return
            
        # Binary content
        if isinstance(content, bytes):
            # 바이너리 모드가 아닌 경우 'b' 추가
            binary_mode = mode if 'b' in mode else mode + 'b'
            with open(raw_path, binary_mode) as f:
                f.write(content)
            return
            
        raise ValueError(f"Unsupported content type: {type(content)}")
        
    except Exception as e:
        print(f"[ERROR] Failed to write file: {str(e)}")
        raise

def rename_file_or_directory(old_path: str, new_name: str) -> None:
    """
    Rename a file or directory.
    파일 또는 디렉토리의 이름을 변경합니다.
    
    Args:
        old_path (str): Current path of the file/directory
                       변경할 파일/디렉토리의 현재 경로
        new_name (str): New name for the file/directory
                       새로운 이름
        
    Raises:
        FileNotFoundError: If the file/directory does not exist
                          파일/디렉토리가 존재하지 않는 경우
        PermissionError: If there is no permission to rename
                        변경 권한이 없는 경우
    """
    new_path = os.path.join(os.path.dirname(old_path), new_name)
    os.rename(old_path, new_path)

def remove_file(path: str) -> None:
    """
    Delete a file.
    파일을 삭제합니다.
    
    Args:
        path (str): Path to the file to delete
               삭제할 파일의 경로
        
    Raises:
        FileNotFoundError: If the file does not exist
                          파일이 존재하지 않는 경우
        PermissionError: If there is no permission to delete
                        삭제 권한이 없는 경우
    """
    os.remove(path)

def remove_directory_recursively(path: str) -> None:
    """
    Delete a directory and all its contents recursively.
    디렉토리를 재귀적으로 삭제합니다.
    
    Args:
        path (str): Path to the directory to delete
               삭제할 디렉토리의 경로
        
    Raises:
        FileNotFoundError: If the directory does not exist
                          디렉토리가 존재하지 않는 경우
        PermissionError: If there is no permission to delete
                        삭제 권한이 없는 경우
    """
    shutil.rmtree(path)

# ============================================================================
# 시스템 유틸리티 (System Utilities)
# ============================================================================

def run_command(command: str) -> Tuple[str, str, int]:
    """
    Execute a shell command and return its output.
    셸 명령어를 실행하고 결과를 반환합니다.
    
    Args:
        command (str): Command to execute
                      실행할 명령어
        
    Returns:
        Tuple[str, str, int]: (stdout, stderr, return_code)
                             (표준출력, 표준에러, 반환코드)
        
    Raises:
        subprocess.SubprocessError: If the command execution fails
                                  명령어 실행 실패 시
    """
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate()
    return stdout, stderr, process.returncode

def which_command(command: str) -> Optional[str]:
    """
    Check if a command exists in system PATH.
    시스템 PATH에 명령어가 존재하는지 확인합니다.
    
    Args:
        command (str): Command to check
                      확인할 명령어
        
    Returns:
        Optional[str]: Full path to the command if found, None otherwise
                      명령어가 존재하면 전체 경로, 없으면 None
    """
    try:
        result = subprocess.run(
            ['which', command],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except subprocess.SubprocessError:
        return None

def apt_install(package_name: str) -> Tuple[bool, str]:
    """
    Install a package using apt-get.
    apt-get을 사용하여 패키지를 설치합니다.
    
    Args:
        package_name (str): Name of the package to install
                          설치할 패키지 이름
        
    Returns:
        Tuple[bool, str]: (success, message)
                         (성공 여부, 메시지)
        
    Note:
        Requires sudo privileges
        sudo 권한이 필요합니다
    """
    try:
        # Check if running as root
        if os.geteuid() != 0:
            return False, "This function requires root privileges"
            
        cmd = f"apt-get install -y {package_name}"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return True, f"Successfully installed {package_name}"
        else:
            return False, f"Failed to install {package_name}: {result.stderr}"
            
    except subprocess.SubprocessError as e:
        return False, f"Installation error: {str(e)}"

def is_package_installed(package_name: str) -> bool:
    """
    Check if a package is installed via apt.
    apt로 패키지가 설치되어 있는지 확인합니다.
    
    Args:
        package_name (str): Name of the package to check
                          확인할 패키지 이름
        
    Returns:
        bool: True if installed, False otherwise
              설치되어 있으면 True, 아니면 False
    """
    try:
        result = subprocess.run(
            ['dpkg', '-l', package_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except subprocess.SubprocessError:
        return False

# ============================================================================
# 문서 변환 유틸리티 (Document Conversion Utilities)
# ============================================================================

def convert_hwp_to_text(hwp_path: str) -> str:
    """
    HWP/HWPX 파일을 텍스트로 변환합니다.
    """
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        import platform
        import subprocess
        import tempfile
        import os
        
        # 파일 확장자 확인
        ext = os.path.splitext(hwp_path)[1].lower()
        
        if ext == '.hwpx':
            try:
                with zipfile.ZipFile(hwp_path) as zf:
                    # section0.xml 파싱
                    with zf.open('Contents/section0.xml') as f:
                        content = f.read().decode('utf-8')
                        
                        # XML 파싱
                        root = ET.fromstring(content)
                        
                        # 네임스페이스 정의
                        ns = {
                            'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
                            'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
                            'ha': 'http://www.hancom.co.kr/hwpml/2011/app',
                            'hs': 'http://www.hancom.co.kr/hwpml/2011/section'
                        }
                        
                        text_parts = []
                        
                        # 1. 문단(p) 처리
                        for para in root.findall('.//hp:p', ns):
                            para_text = []
                            
                            # 1.1 일반 텍스트(t)
                            for run in para.findall('.//hp:run', ns):
                                for t in run.findall('.//hp:t', ns):
                                    if t.text:
                                        para_text.append(t.text)
                            
                            # 1.2 표 처리
                            for tbl in para.findall('.//hp:tbl', ns):
                                for tc in tbl.findall('.//hp:tc', ns):
                                    cell_text = []
                                    for t in tc.findall('.//hp:t', ns):
                                        if t.text:
                                            cell_text.append(t.text.strip())
                                    if cell_text:
                                        para_text.append(' '.join(cell_text))
                            
                            if para_text:
                                text_parts.append(' '.join(para_text))
                        
                        text = '\n'.join(text_parts)
                        return text if text.strip() else "No text content found in the HWPX file."
                    
            except Exception as e:
                raise Exception(f"Failed to process HWPX file: {str(e)}")
                
        elif ext == '.hwp':
            # Windows 환경에서는 임시 파일을 사용하여 처리
            if platform.system() == 'Windows':
                # 임시 디렉토리 생성
                with tempfile.TemporaryDirectory() as temp_dir:
                    # hwp5txt 명령어로 텍스트 파일 생성
                    temp_txt = os.path.join(temp_dir, 'output.txt')
                    cmd = ['hwp5txt', '--output', temp_txt, hwp_path]
                    
                    try:
                        # UTF-8 인코딩으로 출력 설정
                        env = os.environ.copy()
                        env['PYTHONIOENCODING'] = 'utf-8'
                        
                        # 명령어 실행
                        result = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding='utf-8')
                        if result.returncode != 0:
                            raise Exception(result.stderr)
                        
                        # 생성된 텍스트 파일 읽기
                        if os.path.exists(temp_txt):
                            with open(temp_txt, 'r', encoding='utf-8') as f:
                                return f.read()
                        else:
                            return result.stdout
                    except subprocess.SubprocessError as e:
                        raise Exception(f"Failed to convert HWP file: {str(e)}")
            else:
                # Linux/Mac 환경에서는 기존 방식 유지
                result = subprocess.run(
                    ['hwp5txt', hwp_path],
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
                if result.returncode == 0:
                    return result.stdout
                else:
                    raise Exception(result.stderr)
        else:
            raise ValueError("Unsupported file format. Only .hwp and .hwpx files are supported.")
            
    except subprocess.SubprocessError as e:
        raise Exception(f"Failed to convert HWP file: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to convert file: {str(e)}")

def extract_from_doc(doc_path: str) -> str:
    """
    DOC/DOCX 파일에서 텍스트를 추출합니다.
    
    Args:
        doc_path (str): DOC/DOCX 파일 경로
        
    Returns:
        str: 추출된 텍스트
        
    Raises:
        ImportError: 필요한 패키지가 설치되지 않은 경우
        Exception: 파일 처리 중 오류가 발생한 경우
    """
    try:
        # 파일 존재 여부 확인
        if not os.path.exists(doc_path):
            raise FileNotFoundError(f"File not found: {doc_path}")
            
        # 파일 확장자 확인
        ext = os.path.splitext(doc_path)[1].lower()
        if ext not in ['.doc', '.docx']:
            raise ValueError("File must have .doc or .docx extension")
            
        print(f"\nExtracting text from: {doc_path}")
        
        if ext == '.docx':
            # DOCX 파일 처리
            from docx import Document
            doc = Document(doc_path)
            
            # 텍스트 추출
            paragraphs = []
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    paragraphs.append(text)
                    
            # 표 처리
            for table in doc.tables:
                for row in table.rows:
                    row_texts = []
                    for cell in row.cells:
                        text = cell.text.strip()
                        if text:
                            row_texts.append(text)
                    if row_texts:
                        paragraphs.append(" | ".join(row_texts))
            
            return "\n".join(paragraphs)
        else:
            # DOC 파일 처리 (antiword 사용)
            import subprocess
            
            # antiword 설치 여부 확인
            result = subprocess.run(['which', 'antiword'], capture_output=True, text=True)
            if result.returncode != 0:
                raise ImportError("antiword is not installed. Please install it using 'sudo apt-get install antiword'")
            
            # antiword로 텍스트 추출
            result = subprocess.run(['antiword', doc_path], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to extract text using antiword: {result.stderr}")
            
            return result.stdout
        
    except ImportError as e:
        if 'antiword' in str(e):
            raise ImportError(str(e))
        raise ImportError("Required packages not found. Please install 'python-docx' for DOCX files and 'antiword' for DOC files")
    except Exception as e:
        raise Exception(f"Failed to extract text from document: {str(e)}")

def extract_from_ppt(ppt_path: str) -> str:
    """
    PPT/PPTX 파일에서 텍스트를 추출합니다.
    
    Args:
        ppt_path (str): PPT/PPTX 파일 경로
        
    Returns:
        str: 추출된 텍스트
        
    Raises:
        ImportError: 필요한 패키지가 설치되지 않은 경우
        Exception: 파일 처리 중 오류가 발생한 경우
    """
    try:
        # 파일 존재 여부 확인
        if not os.path.exists(ppt_path):
            raise FileNotFoundError(f"File not found: {ppt_path}")
            
        # 파일 확장자 확인
        ext = os.path.splitext(ppt_path)[1].lower()
        if ext not in ['.ppt', '.pptx']:
            raise ValueError("File must have .ppt or .pptx extension")
            
        print(f"\nExtracting text from: {ppt_path}")
        
        if ext == '.pptx':
            # PPTX 파일 처리
            from pptx import Presentation
            prs = Presentation(ppt_path)
            
            # 슬라이드별 텍스트 추출
            all_text = []
            for i, slide in enumerate(prs.slides, 1):
                slide_text = []
                print(f"Processing slide {i}/{len(prs.slides)}...")
                
                # 도형에서 텍스트 추출
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text = shape.text.strip()
                        if text:
                            slide_text.append(text)
                            
                    # 표 처리
                    if shape.has_table:
                        table_text = []
                        for row in shape.table.rows:
                            row_text = []
                            for cell in row.cells:
                                text = cell.text.strip()
                                if text:
                                    row_text.append(text)
                            if row_text:
                                table_text.append(" | ".join(row_text))
                        if table_text:
                            slide_text.extend(table_text)
                
                if slide_text:
                    all_text.append(f"[Slide {i}]\n" + "\n".join(slide_text))
            
            return "\n\n".join(all_text)
        else:
            # PPT 파일 처리 (catppt 사용)
            import subprocess
            
            # catppt 설치 여부 확인
            result = subprocess.run(['which', 'catppt'], capture_output=True, text=True)
            if result.returncode != 0:
                raise ImportError("catppt is not installed. Please install it using 'sudo apt-get install catdoc'")
            
            # catppt로 텍스트 추출
            result = subprocess.run(['catppt', ppt_path], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to extract text using catppt: {result.stderr}")
            
            return result.stdout
        
    except ImportError as e:
        if 'catppt' in str(e):
            raise ImportError(str(e))
        raise ImportError("Required packages not found. Please install 'python-pptx' for PPTX files and 'catdoc' for PPT files")
    except Exception as e:
        raise Exception(f"Failed to extract text from presentation: {str(e)}")

def extract_from_pdf(pdf_path: str) -> str:
    """
    PDF 파일에서 텍스트를 추출합니다.
    
    Args:
        pdf_path (str): PDF 파일 경로
        
    Returns:
        str: 추출된 텍스트
        
    Raises:
        ImportError: PyPDF2 패키지가 설치되지 않은 경우
        Exception: 파일 처리 중 오류가 발생한 경우
    """
    try:
        from PyPDF2 import PdfReader
        
        # 파일 존재 여부 확인
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"File not found: {pdf_path}")
            
        # 파일 확장자 확인
        ext = os.path.splitext(pdf_path)[1].lower()
        if ext != '.pdf':
            raise ValueError("File must have .pdf extension")
            
        print(f"\nExtracting text from PDF: {pdf_path}")
        
        # PDF 파일 열기
        reader = PdfReader(pdf_path)
        
        # 페이지별 텍스트 추출
        all_text = []
        total_pages = len(reader.pages)
        
        for i, page in enumerate(reader.pages, 1):
            print(f"Processing page {i}/{total_pages}...")
            text = page.extract_text()
            if text.strip():
                all_text.append(f"[Page {i}]\n{text.strip()}")
        
        if not all_text:
            print("Warning: No text content found in PDF")
            return ""
            
        return "\n\n".join(all_text)
        
    except ImportError:
        raise ImportError("Required package 'PyPDF2' not found")
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")

def extract_tables_from_hwp(hwp_path: str, excel_path: str) -> bool:
    """
    HWP/HWPX 파일에서 표를 추출하여 Excel 파일로 저장합니다.
    """
    try:
        import pandas as pd
        import subprocess
        import os
        from bs4 import BeautifulSoup
        import tempfile        
        
        # 파일 존재 여부 확인
        if not os.path.exists(hwp_path):
            raise FileNotFoundError(f"File not found: {hwp_path}")
            
        # 파일 확장자 확인
        ext = os.path.splitext(hwp_path)[1].lower()
        if ext not in ['.hwp', '.hwpx']:
            raise ValueError("File must have .hwp or .hwpx extension")
        
        print(f"\nExtracting tables from: {hwp_path}")
        tables = []
        
        if ext == '.hwpx':
            # HWPX 파일 처리
            import zipfile
            import xml.etree.ElementTree as ET
            
            with zipfile.ZipFile(hwp_path) as zf:
                # section0.xml 파싱
                with zf.open('Contents/section0.xml') as f:
                    content = f.read().decode('utf-8')
                    root = ET.fromstring(content)
                    
                    # 네임스페이스 정의
                    ns = {
                        'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
                        'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
                        'ha': 'http://www.hancom.co.kr/hwpml/2011/app',
                        'hs': 'http://www.hancom.co.kr/hwpml/2011/section'
                    }
                    
                    # 표 추출
                    table_count = 0
                    for tbl in root.findall('.//hp:tbl', ns):
                        table_count += 1
                        print(f"\nProcessing table {table_count}...")
                        
                        table_data = []
                        max_cols = 0
                        
                        # 모든 행을 순회하며 최대 열 수 찾기
                        for tr in tbl.findall('.//hp:tr', ns):
                            cols = len(tr.findall('.//hp:tc', ns))
                            max_cols = max(max_cols, cols)
                        
                        # 행 처리
                        row_count = 0
                        for tr in tbl.findall('.//hp:tr', ns):
                            row_count += 1
                            row_data = [''] * max_cols  # 빈 셀로 초기화
                            
                            # 셀 처리
                            for i, tc in enumerate(tr.findall('.//hp:tc', ns)):
                                cell_text = []
                                
                                # 병합 셀 정보
                                rowspan = int(tc.get('rowspan', '1'))
                                colspan = int(tc.get('colspan', '1'))
                                
                                # 셀 내용 추출
                                for t in tc.findall('.//hp:t', ns):
                                    if t.text:
                                        cell_text.append(t.text.strip())
                                
                                # 셀 내용 저장
                                cell_content = ' '.join(cell_text) if cell_text else ''
                                
                                # 병합 셀 처리
                                for col in range(i, min(i + colspan, max_cols)):
                                    row_data[col] = cell_content
                            
                            table_data.append(row_data)
                        
                        if table_data:
                            # 빈 행/열 제거
                            df = pd.DataFrame(table_data)
                            # 모든 값이 빈 문자열인 행/열 제거
                            df = df.loc[:, (df != '').any()]
                            df = df.loc[(df != '').any(axis=1)]
                            
                            if not df.empty:
                                tables.append(df)
                                print(f"Found table with {len(df)} rows and {len(df.columns)} columns")
                            else:
                                print("Table is empty after cleaning")
                        else:
                            print("No data found in table")
                            
        else:
            # HWP 파일 처리
            
            # 파일 존재 여부 확인
            if not os.path.exists(hwp_path):
                raise FileNotFoundError(f"File not found: {hwp_path}")
                
            # 파일 확장자 확인
            ext = os.path.splitext(hwp_path)[1].lower()
            if ext not in ['.hwp', '.hwpx']:
                raise ValueError("File must have .hwp or .hwpx extension")
            
            print(f"\nExtracting tables from: {hwp_path}")
            tables = []
            
            # 임시 디렉토리 생성
            temp_dir = tempfile.mkdtemp(prefix='hwp_')
            temp_html_path = os.path.join(temp_dir, 'output.html')
            
            try:
                # HWP 파일을 HTML로 변환
                result = subprocess.run(['hwp5html', '--output', temp_dir, hwp_path],
                                    capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Failed to convert HWP to HTML: {result.stderr}")
                
                # index.xhtml 파일 찾기
                index_path = os.path.join(temp_dir, 'index.xhtml')
                if not os.path.exists(index_path):
                    raise Exception("HTML conversion failed: index.xhtml not found")
                
                # HTML 파일 읽기
                with open(index_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # BeautifulSoup으로 HTML 파싱
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 표 추출
                table_elements = soup.find_all('table')
                print(f"Found {len(table_elements)} tables")
                
                for i, table in enumerate(table_elements, 1):
                    print(f"\nProcessing table {i}...")
                    
                    # 표 데이터 추출
                    table_data = []
                    for row in table.find_all('tr'):
                        row_data = []
                        for cell in row.find_all(['td', 'th']):
                            # 셀 병합 정보 처리
                            rowspan = int(cell.get('rowspan', 1))
                            colspan = int(cell.get('colspan', 1))
                            
                            # 셀 내용 가져오기
                            cell_text = cell.get_text(strip=True)
                            
                            # 병합된 셀 처리
                            for _ in range(colspan):
                                row_data.append(cell_text)
                        
                        if row_data:  # 빈 행 제외
                            table_data.append(row_data)
                    
                    if table_data:
                        # DataFrame으로 변환
                        df = pd.DataFrame(table_data)
                        
                        # 빈 행/열 제거
                        df = df.loc[:, (df != '').any()]
                        df = df.loc[(df != '').any(axis=1)]
                        
                        if not df.empty:
                            tables.append(df)
                            print(f"Added table with {len(df)} rows and {len(df.columns)} columns")
                        else:
                            print("Table is empty after cleaning")
                    else:
                        print("No data found in table")
                
            finally:
                # 임시 디렉토리 삭제
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        # 추출된 표가 있는 경우
        if tables:
            # Excel 파일 저장 디렉토리 생성
            os.makedirs(os.path.dirname(excel_path), exist_ok=True)
            
            print(f"\nSaving {len(tables)} tables to Excel file: {excel_path}")
            
            # 여러 시트로 Excel 파일 저장
            with pd.ExcelWriter(excel_path) as writer:
                for i, df in enumerate(tables):
                    sheet_name = f'Table_{i+1}'
                    df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
                    print(f"Saved table {i+1} to sheet '{sheet_name}'")
            
            return True
        
        print("No valid tables found in the document")
        return False
        
    except ImportError:
        raise ImportError("Required packages not found. Please install 'pyhwp' and 'olefile'")
    except (FileNotFoundError, ValueError) as e:
        raise type(e)(str(e))
    except Exception as e:
        raise Exception(f"Failed to extract tables: {str(e)}")

def extract_images_from_hwp(hwp_path: str, output_dir: str) -> List[str]:
    """
    HWP/HWPX 파일에서 이미지를 추출하여 지정된 디렉토리에 저장합니다.
    """
    try:
        import os
        import hashlib
        import zlib
        import zipfile
        from hwp5.filestructure import Hwp5File
        from hwp5.storage.ole import OleStorage
        import olefile
        
        # 파일 존재 여부 확인
        if not os.path.exists(hwp_path):
            raise FileNotFoundError(f"File not found: {hwp_path}")
            
        # 파일 확장자 확인
        ext = os.path.splitext(hwp_path)[1].lower()
        if ext not in ['.hwp', '.hwpx']:
            raise ValueError("File must have .hwp or .hwpx extension")
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\nExtracting images from: {hwp_path}")
        print(f"Output directory: {output_dir}")
        
        # 저장된 이미지 파일 경로 리스트
        saved_images = []
        
        if ext == '.hwpx':
            # HWPX 파일 처리
            with zipfile.ZipFile(hwp_path) as zf:
                # BinData 디렉토리의 파일 목록 가져오기
                bindata_files = [f for f in zf.namelist() if f.startswith('BinData/')]
                print(f"\nFound {len(bindata_files)} files in BinData directory")
                
                for bin_file in bindata_files:
                    print(f"\nProcessing: {bin_file}")
                    
                    # 파일 데이터 읽기
                    data = zf.read(bin_file)
                    
                    # 이미지 파일 확장자 확인
                    ext = None
                    if data.startswith(b'\xFF\xD8'):  # JPEG
                        ext = '.jpg'
                    elif data.startswith(b'\x89PNG'):  # PNG
                        ext = '.png'
                    elif data.startswith(b'GIF8'):  # GIF
                        ext = '.gif'
                    elif data.startswith(b'BM'):  # BMP
                        ext = '.bmp'
                    elif data.startswith(b'\x00\x00\x01\x00'):  # ICO
                        ext = '.ico'
                    elif data.startswith(b'\x00\x00\x02\x00'):  # CUR
                        ext = '.cur'
                    elif data.startswith(b'%PDF'):  # PDF
                        ext = '.pdf'
                    elif data[0:4] in [b'RIFF', b'WEBP']:  # WEBP
                        ext = '.webp'
                    
                    if ext:
                        print(f"Detected image type: {ext}")
                        # 파일명 생성 (중복 방지를 위해 해시 사용)
                        hash_name = hashlib.md5(data).hexdigest()[:8]
                        image_path = os.path.join(output_dir, f'image_{hash_name}{ext}')
                        
                        # 이미지 파일 저장
                        with open(image_path, 'wb') as f:
                            f.write(data)
                        saved_images.append(image_path)
                        print(f"Saved image to: {image_path}")
                    else:
                        print(f"Not an image file (magic bytes: {data[:8].hex()})")

        else:
            # HWP 파일 처리
            ole = olefile.OleFileIO(hwp_path)
            
            try:
                print("\nScanning for BinData...")
                
                # BinData 스토리지에서 파일 목록 가져오기
                bindata_list = []
                for entry in ole.listdir():
                    if 'BinData' in entry:
                        bindata_list.append(entry)
                
                print(f"Found {len(bindata_list)} BinData items")
                
                # 각 BinData 처리
                for entry in bindata_list:
                    print(f"\nProcessing: {'/'.join(entry)}")
                    
                    # 스트림 데이터 읽기
                    stream = ole.openstream(entry)
                    data = stream.read()
                    stream.close()
                    
                    # 압축 해제 시도
                    try:
                        decompressed = zlib.decompress(data, -15)  # 압축 해제 시도
                        print("Successfully decompressed data")
                        data = decompressed
                    except zlib.error:
                        print("Data is not compressed with zlib")
                    
                    # 이미지 파일 확장자 확인
                    ext = None
                    if data.startswith(b'\xFF\xD8'):  # JPEG
                        ext = '.jpg'
                    elif data.startswith(b'\x89PNG'):  # PNG
                        ext = '.png'
                    elif data.startswith(b'GIF8'):  # GIF
                        ext = '.gif'
                    elif data.startswith(b'BM'):  # BMP
                        ext = '.bmp'
                    elif data.startswith(b'\x00\x00\x01\x00'):  # ICO
                        ext = '.ico'
                    elif data.startswith(b'\x00\x00\x02\x00'):  # CUR
                        ext = '.cur'
                    elif data.startswith(b'%PDF'):  # PDF
                        ext = '.pdf'
                    elif data[0:4] in [b'RIFF', b'WEBP']:  # WEBP
                        ext = '.webp'
                    
                    # 압축 해제된 데이터의 매직 바이트 출력
                    print(f"Magic bytes after processing: {data[:8].hex()}")
                    
                    if ext:
                        print(f"Detected image type: {ext}")
                        # 파일명 생성 (중복 방지를 위해 해시 사용)
                        hash_name = hashlib.md5(data).hexdigest()[:8]
                        image_path = os.path.join(output_dir, f'image_{hash_name}{ext}')
                        
                        # 이미지 파일 저장
                        with open(image_path, 'wb') as f:
                            f.write(data)
                        saved_images.append(image_path)
                        print(f"Saved image to: {image_path}")
                    else:
                        print(f"Not an image file (magic bytes: {data[:8].hex()})")
                
                if not saved_images:
                    print("\nNo valid images found in BinData storage")
                    
            finally:
                ole.close()
        
        if saved_images:
            print(f"\nSuccessfully extracted {len(saved_images)} images")
            return saved_images
        else:
            print("\nNo images found in the document")
            return []
        
    except ImportError:
        raise ImportError("Required packages not found. Please install 'pyhwp' and 'olefile'")
    except (FileNotFoundError, ValueError) as e:
        raise type(e)(str(e))
    except Exception as e:
        raise Exception(f"Failed to extract images: {str(e)}")

def create_pdf_document() -> PDFDocument:
    """
    Create a new PDF document with Korean support.
    한글을 지원하는 새로운 PDF 문서를 생성합니다.
    
    Returns:
        PDFDocument: A new PDF document instance
                    새로운 PDF 문서 인스턴스
                    
    Raises:
        FileNotFoundError: If Korean font file is not found
                          한글 폰트 파일이 없는 경우
    """
    return PDFDocument()

# ============================================================================
# 시각화 유틸리티 (Visualization Utilities)
# ============================================================================

def create_matplotlib(figsize: tuple = (6, 4)) -> tuple[plt.Figure, plt.Axes, fm.FontProperties]:
    """
    한글 폰트가 설정된 matplotlib 그래프를 생성합니다.
    
    Args:
        figsize (tuple): 그래프 크기 (width, height)
        
    Returns:
        tuple[plt.Figure, plt.Axes, fm.FontProperties]: (figure, axis, font_properties)
        
    Raises:
        FileNotFoundError: 한글 폰트 파일이 없는 경우
    """
    # 한글 폰트 설정
    font_path = safe_path_join(os.path.expanduser("~"), ".airun", "NotoSansKR-Regular.ttf")
    if not os.path.exists(font_path):
        raise FileNotFoundError("Korean font file not found. Please ensure airun is properly installed.")
    
    # 폰트 속성 설정
    font_prop = fm.FontProperties(fname=font_path)
    plt.rcParams["font.family"] = font_prop.get_name()
    fm.fontManager.addfont(font_path)
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["font.size"] = 12
    
    # 그래프 생성
    fig, ax = plt.subplots(figsize=figsize)
    
    return fig, ax, font_prop

def save_plot(fig: plt.Figure, filename: str, dpi: int = 300) -> None:
    """
    matplotlib 그래프를 파일로 저장합니다.
    
    Args:
        fig (plt.Figure): matplotlib figure 객체
        filename (str): 저장할 파일 경로
        dpi (int): 이미지 해상도
    """
    fig.savefig(filename, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

def convert_dot_to_svg(dot_path: str, output_path: str = None) -> str:
    """
    DOT 파일을 SVG로 변환합니다.
    
    Args:
        dot_path (str): DOT 파일 경로
        output_path (str, optional): 출력할 SVG 파일 경로. 지정하지 않으면 DOT 파일과 같은 위치에 생성
        
    Returns:
        str: 생성된 SVG 파일 경로
        
    Raises:
        ImportError: graphviz 패키지가 설치되지 않은 경우
        FileNotFoundError: DOT 파일이 존재하지 않는 경우
        Exception: 변환 중 오류가 발생한 경우
    """
    try:
        # graphviz 패키지 설치 확인 및 설치
        install_if_missing('graphviz')
        
        import os
        import graphviz
        
        # DOT 파일 존재 여부 확인
        if not os.path.exists(dot_path):
            raise FileNotFoundError(f"DOT file not found: {dot_path}")
            
        # 출력 경로가 지정되지 않은 경우 기본값 설정
        if output_path is None:
            output_path = os.path.splitext(dot_path)[0] + '.svg'
            
        # DOT 파일 읽기
        with open(dot_path, 'r', encoding='utf-8') as f:
            dot_content = f.read()
            
        # DOT 내용을 Source 객체로 변환
        src = graphviz.Source(dot_content)
        
        # SVG로 렌더링
        # render()는 확장자를 자동으로 추가하므로, .svg 확장자 제거
        output_path_without_ext = os.path.splitext(output_path)[0]
        rendered_path = src.render(filename=output_path_without_ext, format='svg', cleanup=True)
        
        print(f"Successfully converted {dot_path} to {rendered_path}")
        return rendered_path
        
    except ImportError:
        raise ImportError("Required package 'graphviz' not found")
    except Exception as e:
        raise Exception(f"Failed to convert DOT to SVG: {str(e)}")

# ============================================================================
# 웹 관련 유틸리티 (Web Utilities)
# ============================================================================

def read_url(url: str) -> Union[str, bytes]:
    """
    Read and return the contents of a URL.
    URL의 내용을 읽어 반환합니다.
    
    Args:
        url (str): URL to read from
              읽을 URL
        
    Returns:
        Union[str, bytes]: Contents of the URL. Returns bytes for binary content (images, etc)
                          URL의 내용. 바이너리 콘텐츠(이미지 등)의 경우 bytes 반환
        
    Raises:
        requests.RequestException: If the URL request fails
                                 URL 요청 실패 시
    """
    response = requests.get(url, verify=False)
    response.raise_for_status()
    
    # Check content type
    content_type = response.headers.get('content-type', '').lower()
    if any(t in content_type for t in ['image/', 'video/', 'audio/', 'application/octet-stream']):
        return response.content
    return response.text

def get_selenium_driver():
    """셀레니움 웹드라이버를 생성합니다."""
    try:
        import platform
        import os
        import sys
        
        # 운영체제 확인
        is_windows = platform.system().lower() == 'windows'
        
        if is_windows:
            # Windows용 설정
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--silent')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-breakpad')
            chrome_options.add_argument('--disable-client-side-phishing-detection')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-features=site-per-process')
            chrome_options.add_argument('--disable-hang-monitor')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-prompt-on-repost')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--metrics-recording-only')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--safebrowsing-disable-auto-update')
            chrome_options.add_argument('--password-store=basic')
            
            # Chrome 실행 파일 경로 직접 지정
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if os.path.exists(chrome_path):
                chrome_options.binary_location = chrome_path
            
            driver = webdriver.Chrome(options=chrome_options)
            
        else:
            # Linux용 설정
            global _chrome_driver_path
            
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920x1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--lang=ko_KR')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            _chrome_driver_path = ChromeDriverManager().install()
            service = Service(_chrome_driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
        driver.set_page_load_timeout(30)
        return driver
        
    except Exception as e:
        print(f"[ERROR] Selenium WebDriver 초기화 실패: {str(e)}", file=sys.stderr)
        return None

def extract_web_content(url: str, extract_type: str = 'all', max_items: int = 10, session: requests.Session = None) -> dict:
    """
    웹사이트의 주요 콘텐츠를 추출합니다.
    
    Args:
        url (str): 콘텐츠를 추출할 웹사이트의 URL
        extract_type (str): 추출할 콘텐츠 타입 ('all', 'text', 'links', 'media')
        max_items (int): 추출할 최대 아이템 수
        session (requests.Session): 기존 세션 사용 (선택사항)
        
    Returns:
        dict: {
            'title': 페이지 제목,
            'content': 주요 콘텐츠 텍스트,
            'links': [{'url': 링크URL, 'text': 링크텍스트, 'type': 링크타입}, ...],
            'media': [{'url': 미디어URL, 'type': 미디어타입, 'title': 미디어제목}, ...],
            'metadata': {'description': 설명, 'keywords': [키워드들], 'author': 작성자, 'published_date': 발행일}
        }
    """
    try:
        # 필요한 패키지 설치
        install_if_missing('trafilatura')
        install_if_missing('requests')
        
        import trafilatura
        import requests
        from urllib.parse import urlparse
        from bs4 import BeautifulSoup
        import chardet
        import urllib3
        
        # print(f"\n[DEBUG] extract_web_content 시작")
        # print(f"[DEBUG] URL: {url}")
        # print(f"[DEBUG] extract_type: {extract_type}")
        # print(f"[DEBUG] max_items: {max_items}")
        
        # SSL 경고 메시지 비활성화
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # URL 유효성 검사
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            raise ValueError("Invalid URL format")
            
        # 세션이 없으면 새로 생성
        if session is None:
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
            })
        
        # print("[DEBUG] 웹페이지 다운로드 시작")
        # 웹페이지 다운로드 (SSL 검증 비활성화)
        response = session.get(url, timeout=10, verify=False)
        
        # 인코딩 자동 감지
        if response.encoding.lower() == 'iso-8859-1':
            encoding_detect = chardet.detect(response.content)
            detected_encoding = encoding_detect['encoding']
            if detected_encoding:
                response.encoding = detected_encoding
                # print(f"[DEBUG] 감지된 인코딩: {detected_encoding}")
        
        downloaded = response.text
        # print("[DEBUG] 웹페이지 다운로드 완료")
        
        if not downloaded:
            raise Exception("Failed to download webpage")
            
        # 결과 저장할 딕셔너리
        result = {
            'title': '',
            'content': '',
            'links': [],
            'media': [],
            'metadata': {}
        }
        
        # BeautifulSoup으로 파싱
        # print("[DEBUG] BeautifulSoup 파싱 시작")
        soup = BeautifulSoup(downloaded, 'lxml')
        
        # 제목 추출
        result['title'] = soup.title.string.strip() if soup.title else ''
        # print(f"[DEBUG] 추출된 제목: {result['title']}")
        
        # 메타데이터 추출
        meta_tags = soup.find_all('meta')
        metadata = {}
        for tag in meta_tags:
            if 'name' in tag.attrs and 'content' in tag.attrs:
                metadata[tag['name']] = tag['content']
        
        result['metadata'] = {
            'description': metadata.get('description', ''),
            'keywords': metadata.get('keywords', '').split(',') if metadata.get('keywords') else [],
            'author': metadata.get('author', ''),
            'published_date': metadata.get('published_date', '')
        }
        # print(f"[DEBUG] 추출된 메타데이터: {result['metadata']}")
        
        # 주요 콘텐츠 추출
        if extract_type in ['all', 'text']:
            # print("[DEBUG] 주요 콘텐츠 추출 시작")
            content = trafilatura.extract(downloaded, include_links=False, include_images=False, output_format='txt')
            result['content'] = content if content else "콘텐츠를 추출할 수 없습니다."
            # print(f"[DEBUG] 콘텐츠 추출 길이: {len(result['content'])}")
            
        # 링크 추출
        if extract_type in ['all', 'links']:
            # print("[DEBUG] 링크 추출 시작")
            links = []
            for link in soup.find_all('a', href=True)[:max_items]:
                href = link['href']
                # 상대 URL을 절대 URL로 변환
                if not href.startswith(('http://', 'https://')):
                    href = requests.compat.urljoin(url, href)
                links.append({
                    'url': href,
                    'text': link.get_text(strip=True),
                    'type': 'video' if 'youtube.com/watch' in href else 'link'
                })
            result['links'] = links
            # print(f"[DEBUG] 추출된 링크 수: {len(result['links'])}")
            
        # 미디어 추출
        if extract_type in ['all', 'media']:
            # print("[DEBUG] 미디어 추출 시작")
            media = []
            # 이미지 추출
            for img in soup.find_all('img', src=True)[:max_items]:
                src = img['src']
                if not src.startswith(('http://', 'https://')):
                    src = requests.compat.urljoin(url, src)
                media.append({
                    'url': src,
                    'type': 'image',
                    'title': img.get('alt', '')
                })
                # print(f"[DEBUG] 추출된 이미지 URL: {src}")
            # 비디오 추출
            for video in soup.find_all('video', src=True)[:max_items]:
                src = video['src']
                if not src.startswith(('http://', 'https://')):
                    src = requests.compat.urljoin(url, src)
                media.append({
                    'url': src,
                    'type': 'video',
                    'title': video.get('title', '')
                })
                # print(f"[DEBUG] 추출된 비디오 URL: {src}")
            result['media'] = media
            # print(f"[DEBUG] 추출된 미디어 수: {len(result['media'])}")
            
        # print("[DEBUG] extract_web_content 완료")
        return result
        
    except ImportError as e:
        raise ImportError(f"Required package not found: {str(e)}")
    except requests.RequestException as e:
        raise Exception(f"Failed to download webpage: {str(e)}")
    except ValueError as e:
        raise ValueError(f"Invalid parameter: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to extract web content: {str(e)}")

def open_in_browser(url: str) -> bool:
    """
    URL을 기본 브라우저에서 엽니다.
    
    Args:
        url (str): 열고자 하는 URL
        
    Returns:
        bool: 성공 여부
    """
    try:
        import webbrowser
        
        # URL 형식 검증
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # print(f"[INFO] 브라우저에서 URL 열기: {url}")
        webbrowser.open(url)
        return True
        
    except Exception as e:
        print(f"[ERROR] URL을 열 수 없습니다: {str(e)}")
        return False

# ============================================================================
# 검색 관련 함수 (Search Functions)
# ============================================================================

def search_content(path: str, query: str, file_types: List[str] = None) -> List[Tuple[str, List[str], int]]:
    """
    지정된 경로(파일 또는 디렉토리)에서 특정 파일들의 내용을 검색합니다.
    
    Args:
        path (str): 검색할 파일 또는 디렉토리 경로
        query (str): 검색할 텍스트
        file_types (List[str], optional): 검색할 파일 확장자 목록 (기본값: ['.txt', '.doc', '.docx', '.ppt', '.pptx', '.pdf', '.hwp', '.hwpx'])
    
    Returns:
        List[Tuple[str, List[str], int]]: [(파일경로, [검색된 라인들], 검색된 총 개수), ...]
        
    Raises:
        FileNotFoundError: 파일 또는 디렉토리가 존재하지 않는 경우
    """
    try:
        import os
        import docx
        from pptx import Presentation
        from PyPDF2 import PdfReader
        
        if file_types is None:
            file_types = ['.txt', '.doc', '.docx', '.ppt', '.pptx', '.pdf', '.hwp', '.hwpx']
            
        results = []
        query = query.lower()  # 대소문자 구분 없이 검색
        
        def process_file(file_path: str) -> Optional[Tuple[str, List[str], int]]:
            """단일 파일을 처리하는 내부 함수"""
            try:
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in file_types:
                    return None
                    
                content_lines = []
                match_count = 0
                
                # 텍스트 파일
                if ext == '.txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for line in lines:
                            if query in line.lower():
                                content_lines.append(line.strip())
                                match_count += 1
                
                # Word 문서
                elif ext in ['.docx']:
                    doc = docx.Document(file_path)
                    for para in doc.paragraphs:
                        text = para.text
                        if query in text.lower():
                            content_lines.append(text.strip())
                            match_count += 1
                
                # PowerPoint 문서
                elif ext in ['.pptx']:
                    prs = Presentation(file_path)
                    for slide in prs.slides:
                        for shape in slide.shapes:
                            if hasattr(shape, "text"):
                                text = shape.text
                                if query in text.lower():
                                    content_lines.append(text.strip())
                                    match_count += 1
                
                # PDF 문서
                elif ext == '.pdf':
                    reader = PdfReader(file_path)
                    for page in reader.pages:
                        text = page.extract_text()
                        lines = text.split('\n')
                        for line in lines:
                            if query in line.lower():
                                content_lines.append(line.strip())
                                match_count += 1
                
                # 한글 문서
                elif ext in ['.hwp', '.hwpx']:
                    text = convert_hwp_to_text(file_path)
                    lines = text.split('\n')
                    for line in lines:
                        if query in line.lower():
                            content_lines.append(line.strip())
                            match_count += 1
                
                if match_count > 0:
                    return (file_path, content_lines, match_count)
                return None
                
            except Exception as e:
                print("Warning: Failed to process %s: %s" % (file_path, str(e)))
                return None
        
        # 파일 또는 디렉토리 존재 여부 확인
        if not os.path.exists(path):
            raise FileNotFoundError("Path not found: %s" % path)
        
        # 단일 파일인 경우
        if os.path.isfile(path):
            result = process_file(path)
            if result:
                results.append(result)
        
        # 디렉토리인 경우
        else:
            for root, _, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    result = process_file(file_path)
                    if result:
                        results.append(result)
        
        return results
        
    except ImportError as e:
        raise ImportError("Required package not found: %s" % str(e))
    except Exception as e:
        raise Exception("Search failed: %s" % str(e))

def get_search_url(query: str) -> Tuple[str, str, str]:
    """
    자연어 검색 요청을 분석하여 적절한 검색 URL과 키워드를 반환합니다.
    
    Args:
        query (str): 자연어 검색 요청 (예: "유튜브에서 최신음악 찾아줘", "네이버 뉴스에서 속보 검색")
        
    Returns:
        Tuple[str, str, str]: (검색 URL 패턴, 실제 검색 키워드, 검색 타입)
    """
    # 검색 사이트 매핑
    SEARCH_SITES = {
        '유튜브': {
            'base_url': 'https://www.youtube.com',
            'keywords': ['유튜브', '유튭', 'youtube'],
            'type': 'video',
            'search_patterns': {
                'default': '/results?search_query={keyword}',
                'music': '/results?search_query={keyword}&sp=EgIQAQ%253D%253D',  # 음악 필터
                'live': '/results?search_query={keyword}&sp=EgJAAQ%253D%253D',  # 실시간 필터
                'playlist': '/results?search_query={keyword}&sp=EgIQAw%253D%253D'  # 재생목록 필터
            }
        },
        '네이버': {
            'base_url': 'https://search.naver.com',
            'keywords': ['네이버', 'naver'],
            'type': 'all',
            'search_patterns': {
                'default': '/search.naver?where=nexearch&query={keyword}',
                'news': '/search.naver?where=news&query={keyword}',
                'blog': '/search.naver?where=blog&query={keyword}',
                'cafe': '/search.naver?where=article&query={keyword}',
                'shopping': 'https://search.shopping.naver.com/search/all?query={keyword}'
            }
        },
        '구글': {
            'base_url': 'https://www.google.com',
            'keywords': ['구글', 'google'],
            'type': 'all',
            'search_patterns': {
                'default': '/search?q={keyword}',
                'news': '/search?tbm=nws&q={keyword}',
                'image': '/search?tbm=isch&q={keyword}',
                'video': '/search?tbm=vid&q={keyword}'
            }
        },
        '다음': {
            'base_url': 'https://search.daum.net',
            'keywords': ['다음', 'daum'],
            'type': 'all',
            'search_patterns': {
                'default': '/search?w=tot&q={keyword}',
                'news': '/search?w=news&q={keyword}',
                'image': '/search?w=img&q={keyword}',
                'video': '/search?w=vclip&q={keyword}',
                'blog': '/search?w=blog&q={keyword}'
            }
        }
    }
    
    # 검색어 전처리
    query = query.lower().strip()
    
    # 기본값 설정
    default_site = SEARCH_SITES['네이버']
    site_info = default_site
    search_type = 'default'
    
    # 검색 사이트 감지
    detected_site = None
    for site, info in SEARCH_SITES.items():
        for keyword in info['keywords']:
            if keyword in query.lower():
                detected_site = site
                site_info = info
                # 검색어에서 사이트 키워드와 관련된 부분 제거
                for k in info['keywords']:
                    query = query.replace(k, '').strip()
                break
        if detected_site:
            break
    
    # 검색 타입 감지
    search_keywords = {
        'news': ['뉴스', '속보', '신문'],
        'blog': ['블로그', '후기', '리뷰'],
        'image': ['이미지', '사진', '그림'],
        'video': ['동영상', '영상'],
        'shopping': ['쇼핑', '상품', '물건'],
        'music': ['음악', '노래', '뮤직'],
        'live': ['라이브', '실시간', '생방송'],
        'playlist': ['플레이리스트', '재생목록']
    }
    
    for stype, keywords in search_keywords.items():
        for keyword in keywords:
            if keyword in query:
                search_type = stype
                query = query.replace(keyword, '').strip()
                break
    
    # 검색어에서 불필요한 단어 제거
    remove_words = ['에서', '검색', '찾아', '찾아줘', '검색해줘', '보여줘', '재생', '재생해줘']
    for word in remove_words:
        query = query.replace(word, '').strip()
    
    # 검색 패턴 선택
    if search_type not in site_info['search_patterns']:
        search_type = 'default'
    
    search_pattern = site_info['search_patterns'][search_type]
    
    # 최종 URL 생성을 위한 기본 URL과 패턴 반환
    return site_info['base_url'], search_pattern, query

def create_search_result(title: str, url: str, description: str = "", image_url: str = None, result_type: str = "web", date: str = None) -> dict:
    """
    검색 결과를 표준화된 형식으로 생성하는 함수입니다.
    
    Args:
        title (str): 검색 결과 제목
        url (str): 검색 결과 URL
        description (str, optional): 검색 결과 설명
        image_url (str, optional): 이미지 URL (있는 경우)
        result_type (str, optional): 결과 타입 (web, video, news 등)
        date (str, optional): 검색 결과의 날짜 (YYYY-MM-DD 형식)
        
    Returns:
        dict: 표준화된 검색 결과
    """
    result = {
        'title': title,
        'url': url,
        'description': description,
        'type': result_type,
        'thumbnail': None,
        'image_url': None,
        'date': date  # 날짜 정보 추가
    }
    
    if image_url:
        result['thumbnail'] = image_url
        result['image_url'] = image_url
        
    return result

def search_youtube(query: str, max_results: int = None) -> List[dict]:
    """YouTube 검색을 수행합니다."""
    driver = None
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        driver = get_selenium_driver()
        wait = WebDriverWait(driver, 10)
        
        results = []
        search_url = f"https://www.youtube.com/results?search_query={query}"
        
        driver.get(search_url)
        video_elements = wait.until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ytd-video-renderer"))
        )
        
        limit = max_results if max_results is not None else 10
        for video in video_elements[:limit]:
            try:
                title_element = video.find_element(By.CSS_SELECTOR, "#video-title")
                title = title_element.get_attribute('title')
                url = title_element.get_attribute('href')
                thumbnail = video.find_element(By.CSS_SELECTOR, "#thumbnail img").get_attribute('src')
                description = video.find_element(By.CSS_SELECTOR, "#description-text").text
                
                results.append(create_search_result(
                    title=title,
                    url=url,
                    description=description,
                    image_url=thumbnail,
                    result_type='video'
                ))
            except Exception as e:
                continue
        
        return results
        
    except Exception as e:
        return []
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def search_naver(query: str, max_results: int = None) -> List[dict]:
    """네이버 검색을 수행합니다."""
    driver = None
    try:
        import sys
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        
        driver = get_selenium_driver()
        if not driver:
            return []
            
        results = []
        search_url = f"https://search.naver.com/search.naver?where=news&query={query}"
        
        # debug_print("[DEBUG] 네이버 검색 시작")
        driver.get(search_url)
        time.sleep(2)  # 페이지 로딩 대기
        
        # 검색 결과 요소 찾기
        search_results = driver.find_elements(By.CSS_SELECTOR, "div.news_wrap")
        
        limit = max_results if max_results is not None else 10
        for result in search_results[:limit]:
            try:
                # 제목과 링크 추출
                title_element = result.find_element(By.CSS_SELECTOR, "a.news_tit")
                title = title_element.text
                url = title_element.get_attribute("href")
                
                # 설명 추출
                description = ""
                try:
                    description = result.find_element(By.CSS_SELECTOR, "div.news_dsc").text
                except:
                    pass
                
                if title and url:
                    results.append(create_search_result(
                        title=title,
                        url=url,
                        description=description,
                        result_type='news'
                    ))
            except Exception as e:
                debug_print(f"[DEBUG] 네이버 결과 처리 중 오류: {str(e)}")
                continue
        
        return results
        
    except Exception as e:
        debug_print(f"[ERROR] 네이버 검색 실패: {str(e)}")
        return []
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def search_google(query: str, max_results: int = None) -> List[dict]:
    """구글 검색을 수행합니다."""
    driver = None
    try:
        import sys
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        
        driver = get_selenium_driver()
        if not driver:
            debug_print("[ERROR] Google 드라이버 초기화 실패")
            return []
            
        results = []
        search_url = f"https://www.google.co.kr/search?q={query}&hl=ko&lr=lang_ko"
        
        # debug_print("[DEBUG] 구글 검색 시작")
        driver.get(search_url)
        time.sleep(3)  # 페이지 로딩 대기
        
        # reCAPTCHA 체크
        if "recaptcha" in driver.page_source.lower() or "비정상적인 트래픽" in driver.page_source:
            debug_print("[DEBUG] reCAPTCHA 감지됨, 모바일 버전으로 재시도")
            # 모바일 버전으로 재시도
            driver.get(f"https://www.google.co.kr/search?q={query}&hl=ko&lr=lang_ko&source=mobile")
            time.sleep(3)
        
        # 검색 결과 요소 찾기
        search_results = driver.find_elements(By.CSS_SELECTOR, "div.g")
        if not search_results:
            search_results = driver.find_elements(By.CSS_SELECTOR, "div.xpd")  # 모바일 버전 선택자
        
        # debug_print(f"[DEBUG] Google 검색 결과 {len(search_results)}개 발견")
        
        limit = max_results if max_results is not None else 10
        for result in search_results[:limit]:
            try:
                # 제목과 링크 추출
                title_element = result.find_element(By.CSS_SELECTOR, "h3, div[role='heading']")
                title = title_element.text
                url = result.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
                
                # 설명 추출
                description = ""
                try:
                    description = result.find_element(By.CSS_SELECTOR, "div.VwiC3b, div.BNeawe").text
                except:
                    pass
                
                if title and url:
                    results.append(create_search_result(
                        title=title,
                        url=url,
                        description=description,
                        result_type='web'
                    ))
            except Exception as e:
                debug_print(f"[DEBUG] 결과 처리 중 오류: {str(e)}")
                continue
        
        return results
        
    except Exception as e:
        debug_print(f"[ERROR] Google 검색 실패: {str(e)}")
        return []
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def search_daum(query: str, max_results: int = 5) -> List[dict]:
    """
    다음 검색을 수행하고 결과를 반환합니다.
    """
    driver = None
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException
        import time

        # debug_print("[DEBUG] 다음 검색 시작")
        driver = get_selenium_driver()
        if not driver:
            debug_print("[ERROR] Daum 드라이버 초기화 실패")
            return []

        wait = WebDriverWait(driver, 10)
        
        search_url = f"https://search.daum.net/search?w=fusion&nil_search=btn&DA=NTB&q={query}"
        driver.get(search_url)
        time.sleep(2)  # 페이지 로딩 대기
                   
        results = []
        try:
            # 검색 결과 요소 찾기 - 새로운 HTML 구조
            docs = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "c-card")))
            
            limit = max_results if max_results is not None else 10
            for doc in docs[:limit]:
                try:
                    # 제목과 링크 추출
                    title_element = doc.find_element(By.CSS_SELECTOR, "div.item-title strong.tit-g a")
                    title = title_element.text.strip()
                    url = title_element.get_attribute("href")
                    
                    # 작성자/출처 정보 추출
                    source_info = ""
                    try:
                        source_info = doc.find_element(By.CSS_SELECTOR, "div.area_tit a.item-writer").text.strip()
                    except NoSuchElementException:
                        pass
                    
                    # 설명 추출
                    description = ""
                    try:
                        description = doc.find_element(By.CSS_SELECTOR, "p.conts-desc").text.strip()
                        if source_info:
                            description = f"[{source_info}] {description}"
                    except NoSuchElementException:
                        pass
                    
                    # 날짜 추출
                    date = ""
                    try:
                        date = doc.find_element(By.CSS_SELECTOR, "span.txt_desc").text.strip()
                    except NoSuchElementException:
                        pass
                    
                    if title and url:
                        results.append(create_search_result(
                            title=title,
                            url=url,
                            description=description,
                            result_type='web',
                            date=date
                        ))
                except Exception as e:
                    debug_print(f"[DEBUG] 다음 검색 결과 항목 처리 중 오류: {str(e)}")
                    continue
                    
        except TimeoutException:
            debug_print("[DEBUG] 다음 검색 결과 로딩 시간 초과")
        except Exception as e:
            debug_print(f"[DEBUG] 다음 검색 결과 처리 중 오류: {str(e)}")
        
        # debug_print(f"[DEBUG] 다음 검색 완료: {len(results)}개 결과")
        return results
        
    except Exception as e:
        debug_print(f"[DEBUG] 다음 검색 중 오류 발생: {str(e)}")
        return []
        
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def search_web(query: str, site: str = None, max_results: int = None) -> List[dict]:
    """
    웹 검색을 수행하는 함수
    
    Args:
        query (str): 검색어
        site (str, optional): 검색할 사이트 ('youtube', 'naver', 'google', 'daum')
        max_results (int, optional): 최대 검색 결과 수
    
    Returns:
        List[dict]: 검색 결과 목록
    """
    try:
        # 검색 사이트 지정이 있는 경우
        if site:
            site_lower = site.lower()
            if site_lower == 'youtube':
                return search_youtube(query, max_results)
            elif site_lower == 'naver':
                return search_naver(query, max_results)
            elif site_lower == 'google':
                return search_google(query, max_results)
            elif site_lower == 'daum':
                return search_daum(query, max_results)
            else:
                return []
        
        # 검색 사이트를 지정하지 않은 경우 구글에서만 검색
        return search_google(query, max_results)
            
    except Exception as e:
        return []

def open_search_result(results: List[dict], index: int = 0) -> bool:
    """
    검색 결과 중 지정된 인덱스의 URL을 브라우저에서 엽니다.
    
    Args:
        results (List[dict]): 검색 결과 리스트
        index (int): 열고자 하는 결과의 인덱스 (기본값: 0, 첫 번째 결과)
        
    Returns:
        bool: 성공 여부
    """
    try:
        if not results or len(results) <= index:
            print(f"[ERROR] 인덱스 {index}의 검색 결과가 없습니다.")
            return False
            
        result = results[index]
        if 'url' not in result:
            print("[ERROR] 검색 결과에 URL이 없습니다.")
            return False
            
        return open_in_browser(result['url'])
        
    except Exception as e:
        print(f"[ERROR] 검색 결과를 열 수 없습니다: {str(e)}")
        return False

# ============================================================================
# 이메일 관련 (Email Functions)
# ============================================================================

def send_email(to_email: str, subject: str, body: str, attachments: List[str] = None, html_body: str = None) -> bool:
    """
    이메일을 발송합니다.
    
    Args:
        to_email (str): 받는 사람 이메일 주소
        subject (str): 이메일 제목
        body (str): 이메일 본문 (텍스트)
        attachments (List[str], optional): 첨부 파일 경로 리스트
        html_body (str, optional): HTML 형식의 이메일 본문
        
    Returns:
        bool: 발송 성공 여부
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from email.mime.application import MIMEApplication
        from email.utils import formatdate
        import os
        
        # SMTP 설정 가져오기
        smtp_config = config.get_smtp_settings()
        
        print(f"\n[INFO] SMTP Settings:")
        print(f"- Server: {smtp_config['host']}")
        print(f"- Port: {smtp_config['port']}")
        print(f"- Account: {smtp_config['username']}")
        print(f"- Secure: {smtp_config['secure']}")
        
        # 메시지 생성
        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_config['username']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)
        
        # 텍스트 본문 추가
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # HTML 본문이 있는 경우 추가
        if html_body:
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))
        
        # 첨부 파일 처리
        if attachments:
            for file_path in attachments:
                try:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                            msg.attach(part)
                    else:
                        print(f"[WARNING] 첨부 파일을 찾을 수 없습니다: {file_path}")
                except Exception as e:
                    print(f"[WARNING] 첨부 파일 처리 중 오류 발생: {str(e)}")
                    continue
        
        # SMTP 서버 연결 및 이메일 발송
        with smtplib.SMTP(smtp_config['host'], smtp_config['port']) as server:
            if smtp_config['secure']:
                server.starttls()  # TLS 보안 연결
            server.login(smtp_config['username'], smtp_config['password'])
            server.send_message(msg)
            
        print(f"[INFO] 이메일이 성공적으로 발송되었습니다: {to_email}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 이메일 발송 실패: {str(e)}")
        return False

# ============================================================================
# AI 관련 클래스와 함수 (AI Related Classes and Functions)
# ============================================================================

class AIProvider:
    def __init__(self):
        # Install and import required packages
        self._install_required_packages()
        self._import_providers()
        
        # Load configuration
        self.config = config
        self.provider = config.get('USE_LLM', 'openai')
        self.language = config.get('LANGUAGE', 'en')
        
        # Default max tokens for each provider and model
        self.default_max_tokens = {
            'openai': {
                'gpt-3.5-turbo': 16385,
                'gpt-4': 8192,
                'gpt-4-32k': 32768,
                'gpt-4-turbo': 128000,
                'gpt-4-vision': 128000,
                'gpt-4-all': 128000
            },
            'anthropic': {
                'claude-3-opus': 200000,
                'claude-3-sonnet': 200000,
                'claude-3-haiku': 200000
            },
            'gemini': {
                'gemini-pro': 1000000,
                'gemini-ultra': 1000000
            },
            'groq': {
                'mixtral-8x7b-32768': 32768,
                'llama2-70b-4096': 4096
            },
            'ollama': {
                'llama3': 8192,
                'mistral': 8192,
                'mixtral': 32768
            }
        }
        
        # Default prompts
        self.default_prompts = {
            'summarize': "Please provide a clear and concise summary of the following text:",
            'translate': "Please translate the following text accurately:",
            'review': "Please review the following code for quality, bugs, and performance issues:"
        }
        
        # Load custom prompts if available
        self.custom_prompts = {
            'summarize': self._load_prompt('summarize.prompt'),
            'translate': self._load_prompt('translate.prompt'),
            'review': self._load_prompt('review.prompt')
        }
    
    def _install_required_packages(self):
        packages = ['openai', 'anthropic', 'google-generativeai', 'groq', 'requests']
        for package in packages:
            install_if_missing(package)
    
    def _import_providers(self):
        """Import required packages for each provider"""
        try:
            import openai
            self.openai = openai
        except ImportError:
            self.openai = None
            
        try:
            import anthropic
            self.anthropic = anthropic
        except ImportError:
            self.anthropic = None
            
        try:
            import google.generativeai as genai
            self.genai = genai
        except ImportError:
            self.genai = None
            
        try:
            from groq import Groq
            self.groq = Groq
        except ImportError:
            self.groq = None

    def _load_prompt(self, filename):
        try:
            # ~/.airun/ 디렉토리에서 프롬프트 파일 찾기
            prompt_path = os.path.join(os.path.expanduser("~"), ".airun", filename)
            # print(f"Loading prompt from: {prompt_path}")
            if os.path.exists(prompt_path):
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # print(f"Successfully loaded prompt: {filename}")
                return content
            # print(f"Prompt file not found: {prompt_path}, using default prompt")
            default_prompt = self.default_prompts.get(filename.split('.')[0])
            if default_prompt:
                # print(f"Using default prompt for {filename}")
                return default_prompt
            raise ValueError(f"No default prompt available for {filename}")
        except Exception as e:
            print(f"Error loading prompt file {filename}: {str(e)}")
            default_prompt = self.default_prompts.get(filename.split('.')[0])
            if default_prompt:
                print(f"Using default prompt for {filename}")
                return default_prompt
            raise ValueError(f"Failed to load prompt and no default available for {filename}")

    def _prepare_content(self, content):
        if isinstance(content, str) and os.path.exists(content):
            return read_file(content)
        return content

    def _call_provider(self, messages, max_tokens=None):
        # If max_tokens is not specified, use provider's default
        if max_tokens is None:
            max_tokens = self.default_max_tokens.get(self.provider, 2048)

        try:
            if self.provider == 'openai':
                if not config.get('OPENAI_API_KEY'):
                    raise ValueError("OpenAI API key is not configured.")
                if not self.openai:
                    raise ImportError("Failed to import openai package")
                    
                model = config.get('OPENAI_MODEL', 'gpt-4-turbo')
                client = self.openai.OpenAI(api_key=config.get('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content

            elif self.provider == 'anthropic':
                if not config.get('ANTHROPIC_API_KEY'):
                    raise ValueError("Anthropic API key is not configured.")
                    
                model = config.get('ANTHROPIC_MODEL', 'claude-3-opus-20240229')
                response = self.anthropic.messages.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens
                )
                return response.content

            elif self.provider == 'gemini':
                if not config.get('GOOGLE_API_KEY'):
                    raise ValueError("Google API key is not configured.")
                
                import google.generativeai as genai
                genai.configure(api_key=config.get('GOOGLE_API_KEY'))
                model = config.get('GEMINI_MODEL', 'gemini-1.5-pro')
                
                # Convert messages to Gemini format
                prompt = "\n".join([m['content'] for m in messages])
                response = self.genai.GenerativeModel(model).generate_content(
                    prompt,
                    generation_config=self.genai.types.GenerationConfig(
                        max_output_tokens=max_tokens
                    )
                )
                return response.text

            elif self.provider == 'groq':
                if not config.get('GROQ_API_KEY'):
                    raise ValueError("Groq API key is not configured.")
                
                from groq import Groq
                client = Groq(api_key=config.get('GROQ_API_KEY'))
                model = config.get('GROQ_MODEL', 'mixtral-8x7b-32768')
                
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content

            elif self.provider == 'ollama':
                import requests
                
                ollama_url = config.get('OLLAMA_PROXY_SERVER', 'http://localhost:11434')
                model = config.get('OLLAMA_MODEL', 'llama3:latest')
                
                if config.get('OLLAMA_PROXY_SERVER'):
                    response = requests.post(
                        ollama_url,
                        json={
                            'proxybody': {
                                'model': model,
                                'messages': messages,
                                'stream': False
                            }
                        }
                    )
                else:
                    response = requests.post(
                        'http://localhost:11434/api/chat',
                        json={
                            'model': model,
                            'messages': messages,
                            'stream': False
                        }
                    )
                
                response.raise_for_status()
                return response.json()['message']['content']

            else:
                raise ValueError(f"Unsupported AI provider: {self.provider}")

        except Exception as e:
            print("Error occurred while calling AI provider: %s" % str(e))
            raise

    def _get_model_max_tokens(self):
        """현재 사용 중인 모델의 최대 토큰 수를 반환합니다."""
        if self.provider == 'openai':
            model = self.config.get('OPENAI_MODEL', 'gpt-4-turbo')
            return self.default_max_tokens['openai'].get(model, 8192)  # 기본값 8192
        elif self.provider == 'anthropic':
            model = self.config.get('ANTHROPIC_MODEL', 'claude-3-opus')
            return self.default_max_tokens['anthropic'].get(model, 200000)
        elif self.provider == 'gemini':
            model = self.config.get('GEMINI_MODEL', 'gemini-pro')
            return self.default_max_tokens['gemini'].get(model, 1000000)
        elif self.provider == 'groq':
            model = self.config.get('GROQ_MODEL', 'mixtral-8x7b-32768')
            return self.default_max_tokens['groq'].get(model, 32768)
        elif self.provider == 'ollama':
            model = self.config.get('OLLAMA_MODEL', 'llama3')
            return self.default_max_tokens['ollama'].get(model, 8192)
        return 4000  # 기본값

class TextProcessor(AIProvider):
    # 모델별 비율 설정을 클래스 변수로 정의
    MODEL_RATIOS = {
        'openai': {
            'gpt-3.5-turbo': {'chunk': 0.4, 'summary': 0.3},
            'gpt-4': {'chunk': 0.5, 'summary': 0.4},
            'gpt-4-32k': {'chunk': 0.6, 'summary': 0.4},
            'gpt-4-turbo': {'chunk': 0.6, 'summary': 0.4},
            'gpt-4-vision': {'chunk': 0.6, 'summary': 0.4},
            'gpt-4-all': {'chunk': 0.6, 'summary': 0.4}
        },
        'anthropic': {
            'claude-3-opus': {'chunk': 0.6, 'summary': 0.4},
            'claude-3-sonnet': {'chunk': 0.6, 'summary': 0.4},
            'claude-3-haiku': {'chunk': 0.5, 'summary': 0.3}
        },
        'gemini': {
            'gemini-pro': {'chunk': 0.6, 'summary': 0.4},
            'gemini-ultra': {'chunk': 0.6, 'summary': 0.4}
        },
        'groq': {
            'mixtral-8x7b-32768': {'chunk': 0.5, 'summary': 0.35},
            'llama2-70b-4096': {'chunk': 0.4, 'summary': 0.3}
        },
        'ollama': {
            'llama3': {'chunk': 0.4, 'summary': 0.3},
            'mistral': {'chunk': 0.4, 'summary': 0.3},
            'mixtral': {'chunk': 0.5, 'summary': 0.35}
        }
    }
    
    def _get_model_ratios(self):
        """현재 모델의 비율을 반환합니다."""
        current_model = self.config.get(f'{self.provider.upper()}_MODEL', '')
        default_ratios = {'chunk': 0.4, 'summary': 0.3}
        return self.MODEL_RATIOS.get(self.provider, {}).get(current_model, default_ratios)

    def summarize(self, content, max_length=None):
        content = self._prepare_content(content)
        
        # 현재 모델의 최대 토큰 수 가져오기
        model_max_tokens = self._get_model_max_tokens()
        current_model = self.config.get(f'{self.provider.upper()}_MODEL', '')
        
        # 현재 모델의 비율 가져오기
        model_ratio = self._get_model_ratios()
        
        # OpenAI의 경우 max_tokens 제한
        if self.provider == 'openai':
            max_chunk_size = min(int(model_max_tokens * model_ratio['chunk']), 4000)  # OpenAI의 max_tokens 제한
            max_summary_tokens = min(int(model_max_tokens * model_ratio['summary']), 4000)
        else:
            max_chunk_size = int(model_max_tokens * model_ratio['chunk'])
            max_summary_tokens = int(model_max_tokens * model_ratio['summary'])
        
        print(f"[INFO] Current model: {current_model}")
        print(f"[INFO] Max tokens: {model_max_tokens}")
        print(f"[INFO] Using max chunk size of {max_chunk_size} tokens")
        print(f"[INFO] Max summary tokens: {max_summary_tokens}")
        
        # 청크 크기와 요약본 토큰 수 계산
        max_chunk_size = int(model_max_tokens * model_ratio['chunk'])
        max_summary_tokens = int(model_max_tokens * model_ratio['summary'])
        
        print(f"[INFO] Current model: {current_model}")
        print(f"[INFO] Max tokens: {model_max_tokens}")
        print(f"[INFO] Using max chunk size of {max_chunk_size} tokens")
        
        # 긴 텍스트를 의미 단위로 나누는 함수
        def split_into_semantic_chunks(text):
            chunks = []
            current_chunk = []
            current_size = 0
            
            # 단락 단위로 먼저 분리
            paragraphs = text.split('\n\n')
            
            for paragraph in paragraphs:
                # 토큰 수 추정 (한글: 1자당 2-3토큰, 영어: 1자당 0.3-0.5토큰)
                is_korean = any(ord('가') <= ord(c) <= ord('힣') for c in paragraph)
                token_ratio = 2.5 if is_korean else 0.4
                paragraph_size = int(len(paragraph.encode('utf-8')) * token_ratio)
                
                # 단락이 너무 길면 문장 단위로 분리
                if paragraph_size > max_chunk_size:
                    sentences = paragraph.replace('!', '.').replace('?', '.').split('.')
                    for sentence in sentences:
                        if not sentence.strip():
                            continue
                            
                        sentence = sentence.strip() + '.'
                        sentence_size = int(len(sentence.encode('utf-8')) * token_ratio)
                        
                        # 현재 청크가 제한에 근접하면 새 청크 시작
                        if current_size + sentence_size > max_chunk_size:
                            if current_chunk:
                                chunks.append('\n'.join(current_chunk))
                                current_chunk = []
                                current_size = 0
                        
                        current_chunk.append(sentence)
                        current_size += sentence_size
                else:
                    # 현재 청크가 제한에 근접하면 새 청크 시작
                    if current_size + paragraph_size > max_chunk_size:
                        if current_chunk:
                            chunks.append('\n'.join(current_chunk))
                            current_chunk = []
                            current_size = 0
                    
                    if paragraph.strip():
                        current_chunk.append(paragraph)
                        current_size += paragraph_size
            
            # 남은 내용 처리
            if current_chunk:
                chunks.append('\n'.join(current_chunk))
            
            return chunks
        
        try:
            # 텍스트를 의미 단위로 나누기
            chunks = split_into_semantic_chunks(content)
            print(f"[INFO] Dividing text into {len(chunks)} semantic chunks...")
            
            if len(chunks) == 1:
                # 단일 청크인 경우 직접 요약
                system_prompt = self.custom_prompts.get('summarize')
                if not system_prompt:
                    system_prompt = """Please provide a clear and concise summary of the following text, maintaining the key points and overall structure:
1. Maintain the logical flow and relationships between ideas
2. Preserve the hierarchical importance of information
3. Ensure key themes and concepts are properly connected
4. Provide a comprehensive yet concise overview"""
                
                user_lang = self.config.get('LANGUAGE', 'en')
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": f"The user's language is {user_lang}. Please provide the summary in this language."},
                    {"role": "user", "content": chunks[0]}
                ]
                
                return self._call_provider(messages, max_tokens=max_length or int(max_chunk_size * 0.5))
            
            # 여러 청크가 있는 경우 계층적 요약
            summaries = []
            print("[INFO] Starting hierarchical summarization...")
            
            # 1단계: 각 청크의 핵심 내용 추출 (더 짧은 요약)
            for i, chunk in enumerate(chunks, 1):
                print(f"[INFO] Extracting key points from chunk {i}/{len(chunks)}...")
                messages = [
                    {"role": "system", "content": "Extract only the most essential points from this text in a very concise manner:"},
                    {"role": "user", "content": chunk}
                ]
                key_points = self._call_provider(messages, max_tokens=int(max_chunk_size * 0.3))
                summaries.append(key_points)
            
            # 중간 요약들이 너무 길면 다시 나누어 요약
            while len('\n\n'.join(summaries).encode('utf-8')) // 3 > max_chunk_size:
                print("[INFO] Intermediate summaries too long, performing additional summarization...")
                new_summaries = []
                temp_summaries = []
                current_size = 0
                
                for summary in summaries:
                    summary_size = len(summary.encode('utf-8')) // 3
                    if current_size + summary_size > max_chunk_size:
                        if temp_summaries:
                            combined = '\n\n'.join(temp_summaries)
                            messages = [
                                {"role": "system", "content": "Create an extremely concise summary of these points:"},
                                {"role": "user", "content": combined}
                            ]
                            new_summary = self._call_provider(messages, max_tokens=int(max_chunk_size * 0.3))
                            new_summaries.append(new_summary)
                            temp_summaries = [summary]
                            current_size = summary_size
                    else:
                        temp_summaries.append(summary)
                        current_size += summary_size
                
                if temp_summaries:
                    combined = '\n\n'.join(temp_summaries)
                    messages = [
                        {"role": "system", "content": "Create an extremely concise summary of these points:"},
                        {"role": "user", "content": combined}
                    ]
                    new_summary = self._call_provider(messages, max_tokens=int(max_chunk_size * 0.3))
                    new_summaries.append(new_summary)
                
                summaries = new_summaries
            
            # 2단계: 최종 요약 생성
            print("[INFO] Creating final summary...")
            system_prompt = self.custom_prompts.get('summarize')
            if not system_prompt:
                system_prompt = """Please provide a clear and concise summary of the following text, maintaining the key points and overall structure:
1. Maintain the logical flow and relationships between ideas
2. Preserve the hierarchical importance of information
3. Ensure key themes and concepts are properly connected
4. Provide a comprehensive yet concise overview"""

            final_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "system", "content": f"The user's language is {self.language}. Create the summary in this language."},
                {"role": "user", "content": '\n\n'.join(summaries)}
            ]
            
            # max_tokens를 4096 이하로 제한
            max_final_tokens = min(max_length or int(max_chunk_size * 0.5), 4000)  # 여유있게 4000으로 제한
            print(f"[INFO] Using max_tokens of {max_final_tokens} for final summary")
            
            return self._call_provider(final_messages, max_tokens=max_final_tokens)
            
        except Exception as e:
            print(f"[ERROR] Summarization failed: {str(e)}")
            raise

    def translate(self, content, target_language):
        content = self._prepare_content(content)
        
        # 현재 모델의 최대 토큰 수 가져오기
        model_max_tokens = self._get_model_max_tokens()
        current_model = self.config.get(f'{self.provider.upper()}_MODEL', '')
        
        # 현재 모델의 비율 가져오기
        model_ratio = self._get_model_ratios()
        
        # OpenAI의 경우 max_tokens 제한
        if self.provider == 'openai':
            max_chunk_size = min(int(model_max_tokens * model_ratio['chunk']), 4000)
            max_response_tokens = min(int(model_max_tokens * model_ratio['summary']), 4000)
        else:
            max_chunk_size = int(model_max_tokens * model_ratio['chunk'])
            max_response_tokens = int(model_max_tokens * model_ratio['summary'])
        
        print(f"\n[INFO] 번역 작업 시작")
        print(f"[INFO] 현재 모델: {current_model}")
        print(f"[INFO] 최대 토큰 수: {model_max_tokens}")
        print(f"[INFO] 청크 크기: {max_chunk_size} 토큰")
        print(f"[INFO] 응답 토큰 수: {max_response_tokens}")
        
        try:
            import tempfile
            import os
            
            # 입력 텍스트 크기 계산
            content_size = len(content.encode('utf-8'))
            print(f"[INFO] 입력 텍스트 크기: {content_size / 1024:.2f}KB")
            
            # 입력 텍스트가 1MB를 초과하는 경우 임시 파일 사용
            use_temp_files = content_size > 1024 * 1024
            temp_dir = None
            
            if use_temp_files:
                temp_dir = tempfile.mkdtemp(prefix='translation_')
                print(f"[INFO] 임시 디렉토리 생성됨: {temp_dir}")
                print(f"[INFO] 임시 디렉토리 존재 여부: {os.path.exists(temp_dir)}")
            
            # 텍스트를 청크로 나누는 함수
            def split_into_chunks(text):
                chunks = []
                current_chunk = []
                current_size = 0
                chunk_count = 0
                
                print(f"[INFO] 텍스트 분할 시작...")
                
                # 문단 단위로 먼저 분리
                paragraphs = text.split('\n\n')
                print(f"[INFO] 총 {len(paragraphs)}개의 문단 발견")
                
                for i, paragraph in enumerate(paragraphs, 1):
                    # 토큰 수 추정
                    is_korean = any(ord('가') <= ord(c) <= ord('힣') for c in paragraph)
                    token_ratio = 2.5 if is_korean else 0.4
                    paragraph_size = int(len(paragraph.encode('utf-8')) * token_ratio)
                    
                    # 현재 청크가 제한에 근접하면 새 청크 시작
                    if current_size + paragraph_size > max_chunk_size:
                        if current_chunk:
                            chunk_text = '\n'.join(current_chunk)
                            if use_temp_files:
                                chunk_file = os.path.join(temp_dir, f'chunk_{chunk_count}.txt')
                                with open(chunk_file, 'w', encoding='utf-8') as f:
                                    f.write(chunk_text)
                                print(f"[INFO] 청크 {chunk_count} 저장됨: {chunk_file} ({len(chunk_text.encode('utf-8'))/1024:.2f}KB)")
                                chunks.append(chunk_file)
                            else:
                                chunks.append(chunk_text)
                            chunk_count += 1
                            current_chunk = []
                            current_size = 0
                    
                    current_chunk.append(paragraph)
                    current_size += paragraph_size
                    print(f"[INFO] 문단 {i}/{len(paragraphs)} 처리 중... (현재 청크 크기: {current_size} 토큰)")
                
                # 남은 내용 처리
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk)
                    if use_temp_files:
                        chunk_file = os.path.join(temp_dir, f'chunk_{chunk_count}.txt')
                        with open(chunk_file, 'w', encoding='utf-8') as f:
                            f.write(chunk_text)
                        print(f"[INFO] 마지막 청크 {chunk_count} 저장됨: {chunk_file} ({len(chunk_text.encode('utf-8'))/1024:.2f}KB)")
                        chunks.append(chunk_file)
                    else:
                        chunks.append(chunk_text)
                
                print(f"[INFO] 총 {len(chunks)}개의 청크로 분할 완료")
                return chunks
            
            # 텍스트를 청크로 나누기
            chunks = split_into_chunks(content)
            
            # 번역된 청크를 저장할 리스트 또는 임시 파일들
            translated_chunks = []
            
            # 언어 코드 정규화
            normalized_target = normalize_language_code(target_language)
            print(f"[INFO] 대상 언어 코드: {normalized_target}")
            
            # 번역 프롬프트 준비
            system_prompt = self.custom_prompts.get('translate')
            if not system_prompt:
                system_prompt = """Please translate the following text to the specified target language.
                Maintain the original meaning, nuance, and formatting as accurately as possible.
                Preserve all line breaks and paragraph structures."""
            
            # 각 청크 번역
            for i, chunk in enumerate(chunks, 1):
                print(f"\n[INFO] 청크 {i}/{len(chunks)} 번역 시작...")
                
                # 청크 내용 읽기
                if use_temp_files:
                    print(f"[INFO] 청크 파일 읽기: {chunk}")
                    with open(chunk, 'r', encoding='utf-8') as f:
                        chunk_content = f.read()
                    print(f"[INFO] 청크 크기: {len(chunk_content.encode('utf-8'))/1024:.2f}KB")
                else:
                    chunk_content = chunk
                
                # 번역 수행
                print(f"[INFO] AI 모델에 번역 요청 중...")
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": f"Target language: {target_language} (normalized code: {normalized_target})"},
                    {"role": "user", "content": chunk_content}
                ]
                
                translated_text = self._call_provider(messages, max_tokens=max_chunk_size)
                print(f"[INFO] 번역 완료 (결과 크기: {len(translated_text.encode('utf-8'))/1024:.2f}KB)")
                
                # 번역된 텍스트 저장
                if use_temp_files:
                    translated_file = os.path.join(temp_dir, f'translated_{i}.txt')
                    with open(translated_file, 'w', encoding='utf-8') as f:
                        f.write(translated_text)
                    print(f"[INFO] 번역 결과 저장됨: {translated_file}")
                    translated_chunks.append(translated_file)
                else:
                    translated_chunks.append(translated_text)
            
            print("\n[INFO] 번역된 청크 병합 중...")
            # 번역된 청크 합치기
            if use_temp_files:
                final_text = []
                for chunk_file in translated_chunks:
                    print(f"[INFO] 번역된 파일 읽기: {chunk_file}")
                    with open(chunk_file, 'r', encoding='utf-8') as f:
                        final_text.append(f.read())
                result = '\n'.join(final_text)
            else:
                result = '\n'.join(translated_chunks)
            
            print(f"[INFO] 최종 번역 완료 (결과 크기: {len(result.encode('utf-8'))/1024:.2f}KB)")
            return result
            
        except Exception as e:
            print(f"[ERROR] 번역 실패: {str(e)}")
            raise
            
        finally:
            # 임시 파일 및 디렉토리 정리
            if use_temp_files and temp_dir:
                try:
                    import shutil
                    print(f"\n[INFO] 임시 파일 정리 중...")
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                        print(f"[INFO] 임시 디렉토리 삭제됨: {temp_dir}")
                except Exception as e:
                    print(f"[WARNING] 임시 파일 정리 실패: {str(e)}")

    def review_code(self, content):
        content = self._prepare_content(content)
        
        # Use custom prompt if available
        system_prompt = self.custom_prompts.get('review')
        if not system_prompt:
            system_prompt = "Please review the following code for quality, bugs, and performance issues:"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        
        return self._call_provider(messages)

def normalize_language_code(language: str) -> str:
    """
    언어 이름이나 코드를 ISO 639-1 코드로 정규화합니다.
    
    Args:
        language (str): 언어 이름 또는 코드 (예: '한국어', 'korean', 'ko', '영어', 'english', 'en' 등)
        
    Returns:
        str: 정규화된 ISO 639-1 언어 코드
    """
    # 언어 코드 매핑
    LANGUAGE_CODES = {
        # 한국어
        '한국어': 'ko',
        'korean': 'ko',
        'ko': 'ko',
        'kor': 'ko',
        
        # 영어
        '영어': 'en',
        'english': 'en',
        'en': 'en',
        'eng': 'en',
        
        # 일본어
        '일본어': 'ja',
        'japanese': 'ja',
        'ja': 'ja',
        'jpn': 'ja',
        
        # 중국어
        '중국어': 'zh',
        'chinese': 'zh',
        'zh': 'zh',
        'chi': 'zh',
        '중국어(간체)': 'zh-CN',
        '중국어(번체)': 'zh-TW',
        'simplified chinese': 'zh-CN',
        'traditional chinese': 'zh-TW',
        
        # 프랑스어
        '프랑스어': 'fr',
        'french': 'fr',
        'fr': 'fr',
        'fra': 'fr',
        
        # 독일어
        '독일어': 'de',
        'german': 'de',
        'de': 'de',
        'deu': 'de',
        
        # 스페인어
        '스페인어': 'es',
        'spanish': 'es',
        'es': 'es',
        'spa': 'es',
        
        # 이탈리아어
        '이탈리아어': 'it',
        'italian': 'it',
        'it': 'it',
        'ita': 'it',
        
        # 러시아어
        '러시아어': 'ru',
        'russian': 'ru',
        'ru': 'ru',
        'rus': 'ru',
        
        # 베트남어
        '베트남어': 'vi',
        'vietnamese': 'vi',
        'vi': 'vi',
        'vie': 'vi',
        
        # 태국어
        '태국어': 'th',
        'thai': 'th',
        'th': 'th',
        'tha': 'th',
        
        # 인도네시아어
        '인도네시아어': 'id',
        'indonesian': 'id',
        'id': 'id',
        'ind': 'id'
    }
    
    # 입력값 전처리
    normalized = language.lower().strip()
    
    # 매핑된 코드 반환 또는 입력값 그대로 반환
    return LANGUAGE_CODES.get(normalized, normalized)

def summarize_content(content, provider=None, max_length=None):
    processor = TextProcessor()
    return processor.summarize(content, max_length)

def translate_content(content, target_language, provider=None):
    processor = TextProcessor()
    return processor.translate(content, target_language)

def review_code(content, provider=None):
    processor = TextProcessor()
    return processor.review_code(content)

# ============================================================================
# 디버깅 유틸리티 (Debug Utilities)
# ============================================================================

def debug_print(message: str) -> None:
    """
    디버그 메시지를 stderr로 출력합니다.
    
    Args:
        message (str): 출력할 디버그 메시지
    """
    print(message, file=sys.stderr)


if __name__ == "__main__":
    import sys
