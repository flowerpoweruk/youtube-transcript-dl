import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                             QPushButton, QLabel, QProgressBar, QTextEdit, QFileDialog,
                             QTabWidget)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import yt_dlp

class YouTubeCaptionDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.history = self.load_history()
        self.errors = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle('YouTube Caption Downloader')
        self.setGeometry(100, 100, 600, 400)
        self.setStyleSheet('''
            QWidget {
                background-color: #f0f0f0;
                font-family: Arial, sans-serif;
            }
            QLineEdit, QTextEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
        ''')

        layout = QVBoxLayout()

        # Title
        title_label = QLabel('YouTube Caption Downloader')
        title_label.setStyleSheet('font-size: 24px; font-weight: bold; color: #333; margin-bottom: 20px;')
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # URL input
        url_layout = QHBoxLayout()
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText('Paste YouTube URLs here (one per line)')
        self.url_input.setFixedHeight(100)
        url_layout.addWidget(self.url_input)

        button_layout = QVBoxLayout()
        self.download_button = QPushButton('Download')
        self.download_button.clicked.connect(self.download_captions)
        button_layout.addWidget(self.download_button)

        self.save_location_button = QPushButton('Set Save Location')
        self.save_location_button.clicked.connect(self.set_save_location)
        button_layout.addWidget(self.save_location_button)

        url_layout.addLayout(button_layout)

        layout.addLayout(url_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel('Enter YouTube URLs and click Download')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Tabs for Error Report and History
        tabs = QTabWidget()
        
        self.error_report = QTextEdit()
        self.error_report.setReadOnly(True)
        tabs.addTab(self.error_report, "Error Report")

        self.history_view = QTextEdit()
        self.history_view.setReadOnly(True)
        tabs.addTab(self.history_view, "Download History")

        layout.addWidget(tabs)

        self.setLayout(layout)

        self.save_location = os.path.expanduser("~/Downloads")
        self.update_history_view()

    def get_video_id(self, url):
        """Extract video ID from YouTube URL"""
        parsed_url = urlparse(url)
        if parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:]
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                p = parse_qs(parsed_url.query)
                return p['v'][0]
            if parsed_url.path[:7] == '/embed/':
                return parsed_url.path.split('/')[2]
            if parsed_url.path[:3] == '/v/':
                return parsed_url.path.split('/')[2]
        return None

    def download_captions(self):
        urls = self.url_input.toPlainText().split('\n')
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            self.status_label.setText('Please enter valid YouTube URLs')
            return

        self.progress_bar.setValue(0)
        self.download_button.setEnabled(False)
        self.errors = []

        for i, url in enumerate(urls):
            self.status_label.setText(f'Processing URL {i+1} of {len(urls)}...')
            self.process_url(url)
            self.progress_bar.setValue(int((i+1) / len(urls) * 100))
            QApplication.processEvents()

        self.download_button.setEnabled(True)
        self.status_label.setText('Download complete')
        self.update_error_report()
        self.save_history()
        self.update_history_view()

    def process_url(self, url):
        try:
            video_id = self.get_video_id(url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")

            if video_id in self.history:
                self.errors.append(f"Skipped {url}: Already processed before")
                return

            # Get video info
            ydl_opts = {}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info['title']

            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            full_text = ' '.join([entry['text'] for entry in transcript])

            # Save captions
            filename = f"{title} - {video_id}.txt"
            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            if not filename.lower().endswith('.txt'):
                filename += '.txt'
            filepath = os.path.join(self.save_location, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(full_text)

            self.history[video_id] = {'url': url, 'title': title, 'filename': filename}

        except Exception as e:
            self.errors.append(f"Error processing {url}: {str(e)}")

    def set_save_location(self):
        dir_ = QFileDialog.getExistingDirectory(self, "Select Save Location")
        if dir_:
            self.save_location = dir_
            self.status_label.setText(f'Save location set to: {self.save_location}')

    def update_error_report(self):
        self.error_report.clear()
        if self.errors:
            self.error_report.setText('\n'.join(self.errors))
        else:
            self.error_report.setText("No errors occurred during the last download.")

    def load_history(self):
        try:
            with open('download_history.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_history(self):
        with open('download_history.json', 'w') as f:
            json.dump(self.history, f)

    def update_history_view(self):
        self.history_view.clear()
        for video_id, info in self.history.items():
            self.history_view.append(f"Title: {info['title']}")
            self.history_view.append(f"URL: {info['url']}")
            self.history_view.append(f"Filename: {info['filename']}")
            self.history_view.append("")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = YouTubeCaptionDownloader()
    ex.show()
    sys.exit(app.exec())
