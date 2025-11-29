import sys
import os

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTextBrowser,
    QFileDialog,
    QToolBar,
    QAction,
    QMessageBox,
    QStatusBar,
    QInputDialog,
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from PyPDF2 import PdfReader
from ebooklib import epub
import ebooklib  # needed for ITEM_DOCUMENT
from bs4 import BeautifulSoup  # need: pip install beautifulsoup4


class FeReaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- Reader state ---
        self.current_book_type = None  # "pdf" or "epub"
        self.current_book_path = None
        self.current_book_title = "Untitled"
        self.pages = []               # list of strings (text or HTML)
        self.current_index = 0
        self.current_font_size = 12

        # --- UI setup ---
        self.setWindowTitle("FeReader - PDF & EPUB Reader")
        self.resize(900, 600)

        self.text_view = QTextBrowser()
        self.text_view.setOpenExternalLinks(True)
        self.text_view.setFont(QFont("Segoe UI", self.current_font_size))
        self.setCentralWidget(self.text_view)

        self._create_toolbar()
        self._create_statusbar()

        self._update_view()

    # ----------------- UI creation -----------------

    def _create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Open file
        open_action = QAction("Open", self)
        open_action.setStatusTip("Open PDF or EPUB file")
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        toolbar.addSeparator()

        # Previous page
        prev_action = QAction("Prev", self)
        prev_action.setStatusTip("Previous page")
        prev_action.triggered.connect(self.go_prev)
        toolbar.addAction(prev_action)

        # Next page
        next_action = QAction("Next", self)
        next_action.setStatusTip("Next page")
        next_action.triggered.connect(self.go_next)
        toolbar.addAction(next_action)

        # Go to page
        goto_action = QAction("Go to...", self)
        goto_action.setStatusTip("Go to page number")
        goto_action.triggered.connect(self.go_to_page_dialog)
        toolbar.addAction(goto_action)

        toolbar.addSeparator()

        # Zoom in
        zoom_in_action = QAction("A+", self)
        zoom_in_action.setStatusTip("Increase font size")
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        # Zoom out
        zoom_out_action = QAction("A-", self)
        zoom_out_action.setStatusTip("Decrease font size")
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        toolbar.addSeparator()

        # About
        about_action = QAction("About", self)
        about_action.setStatusTip("About FeReader")
        about_action.triggered.connect(self.show_about)
        toolbar.addAction(about_action)

    def _create_statusbar(self):
        status = QStatusBar()
        self.setStatusBar(status)
        self._update_statusbar()

    def _update_statusbar(self):
        if self.pages:
            info = f"{self.current_book_title}  |  Page {self.current_index + 1} / {len(self.pages)}"
        else:
            info = "No document loaded"
        self.statusBar().showMessage(info)

    # ----------------- File handling -----------------

    def open_file(self):
        dialog_filter = "Documents (*.pdf *.epub);;PDF Files (*.pdf);;EPUB Files (*.epub);;All Files (*.*)"
        path, _ = QFileDialog.getOpenFileName(self, "Open document", "", dialog_filter)

        if not path:
            return

        ext = os.path.splitext(path)[1].lower()

        try:
            if ext == ".pdf":
                self.load_pdf(path)
            elif ext == ".epub":
                self.load_epub(path)
            else:
                QMessageBox.warning(self, "Unsupported file", "Only PDF and EPUB are supported.")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file:\n{e}")
            return

        self.current_book_path = path
        self.current_book_title = os.path.basename(path)
        self.current_index = 0
        self._update_view()

    def load_pdf(self, path):
        self.current_book_type = "pdf"
        self.pages = []

        reader = PdfReader(path)
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            self.pages.append(text if text.strip() else "[Empty page]")

    def load_epub(self, path):
        self.current_book_type = "epub"
        self.pages = []

        book = epub.read_epub(path)

        # Collect all document-type items
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            raw_html = item.get_content().decode("utf-8", errors="ignore")

            # Use BeautifulSoup to normalize HTML
            soup = BeautifulSoup(raw_html, "html.parser")
            clean_html = soup.prettify()

            self.pages.append(clean_html)

        if not self.pages:
            self.pages.append("<h3>No readable content found.</h3>")

    # ----------------- Navigation -----------------

    def _update_view(self):
        if not self.pages:
            self.text_view.setPlainText("No document loaded.")
        else:
            content = self.pages[self.current_index]
            if self.current_book_type == "epub":
                self.text_view.setHtml(content)
            else:
                self.text_view.setPlainText(content)

        font = self.text_view.font()
        font.setPointSize(self.current_font_size)
        self.text_view.setFont(font)

        self._update_statusbar()

    def go_prev(self):
        if not self.pages:
            return
        if self.current_index > 0:
            self.current_index -= 1
            self._update_view()

    def go_next(self):
        if not self.pages:
            return
        if self.current_index < len(self.pages) - 1:
            self.current_index += 1
            self._update_view()

    def go_to_page_dialog(self):
        if not self.pages:
            return

        max_page = len(self.pages)
        current_page_display = self.current_index + 1

        value, ok = QInputDialog.getInt(
            self,
            "Go to page",
            f"Enter page number (1 - {max_page}):",
            value=current_page_display,
            min=1,
            max=max_page,
        )
        if ok:
            self.current_index = value - 1
            self._update_view()

    # ----------------- Zoom -----------------

    def zoom_in(self):
        self.current_font_size += 1
        if self.current_font_size > 40:
            self.current_font_size = 40
        self._update_view()

    def zoom_out(self):
        self.current_font_size -= 1
        if self.current_font_size < 8:
            self.current_font_size = 8
        self._update_view()

    # ----------------- Misc -----------------

    def show_about(self):
        QMessageBox.information(
            self,
            "About FeReader",
            "FeReader\nSimple PDF & EPUB Reader\nPowered by PyQt5, PyPDF2, and ebooklib.",
        )


def main():
    app = QApplication(sys.argv)
    window = FeReaderWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
