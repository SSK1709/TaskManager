import sqlite3
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QFrame, QLabel,
    QPushButton, QScrollArea, QGridLayout, QWidget, QListWidget,
    QListWidgetItem, QInputDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QColor, QDrag
import sys

DB_FILE = "tasks.db"

# Database Helper Functions
def initialize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            category TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def load_tasks():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT description, priority, category FROM tasks")
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def save_task(description, priority, category):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (description, priority, category) VALUES (?, ?, ?)", (description, priority, category))
    conn.commit()
    conn.close()

def delete_task(description, category):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE description = ? AND category = ?", (description, category))
    conn.commit()
    conn.close()

class TaskList(QListWidget):
    def __init__(self, category, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.category = category

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mime_data = QMimeData()

            color = item.background().color().name()
            mime_data.setHtml(f"{color}|{item.text()}|{self.category}")
            drag.setMimeData(mime_data)
            drag.exec(supportedActions)

    def dragEnterEvent(self, event):
        if event.mimeData().hasHtml():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasHtml():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasHtml():
            color, item_text, source_category = event.mimeData().html().split("|", 2)
            item = QListWidgetItem(item_text)
            item.setBackground(QColor(color))
            self.addItem(item)
            event.accept()

            # Save to new category in database
            save_task(item_text, self.get_priority_color(item), self.category)

            # Delete from the source category
            delete_task(item_text, source_category)

            source = event.source()
            if source is not self and isinstance(source, QListWidget):
                source.takeItem(source.currentRow())
        else:
            event.ignore()

    def get_priority_color(self, task_item):
        bg_color = task_item.background().color()
        if bg_color == QColor(192, 192, 192):
            return "Menial"
        elif bg_color == QColor(255, 120, 0):
            return "Semi Important"
        elif bg_color == QColor(255, 0, 0):
            return "Urgent"

from PyQt6.QtWidgets import QMessageBox

import re
from PyQt6.QtWidgets import QMessageBox

class TaskBoard(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.Box)
        self.setFrameShadow(QFrame.Shadow.Raised)

        self.title = title
        self.layout = QVBoxLayout(self)

        # Header
        self.header = QLabel(self.title)
        self.header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.header)

        # Task List
        self.task_list = TaskList(self.title)
        self.layout.addWidget(self.task_list)

        # Buttons Layout
        self.buttons_layout = QVBoxLayout()

        # Add Task Button (only for "To Do" board)
        if title == "To Do":
            self.add_task_button = QPushButton("Add Task")
            self.add_task_button.clicked.connect(self.add_task)
            self.buttons_layout.addWidget(self.add_task_button)

        # Delete Task Button
        self.delete_task_button = QPushButton("Delete Task")
        self.delete_task_button.clicked.connect(self.delete_task)
        self.buttons_layout.addWidget(self.delete_task_button)

        # Add the button layout to the main layout
        self.layout.addLayout(self.buttons_layout)

    def add_task(self):
        task_text, ok = QInputDialog.getText(self, "New Task", "Enter task description:")
        if not ok or not task_text.strip():  # Handle cancel or empty input
            return

        # Validation: Check if task contains only letters and spaces
        if not re.fullmatch(r"[A-Za-z ]+", task_text):
            self.show_error_message("Task description can only contain letters and spaces.")
            return

        if len(task_text) > 100:  # Example: Limit to 100 characters
            self.show_error_message("Task description is too long. Please keep it under 100 characters.")
            return

        # Prompt for priority
        priority, ok = QInputDialog.getItem(self, "Select Priority", "Select task priority:",
                                             ["Menial", "Semi Important", "Urgent"], 0, False)
        if ok and priority:
            task_item = QListWidgetItem(task_text)
            self.set_priority_color(task_item, priority)
            self.task_list.addItem(task_item)

            # Save to database
            save_task(task_text, priority, self.title)

    def show_error_message(self, message):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Icon.Warning)
        error_dialog.setWindowTitle("Invalid Task")
        error_dialog.setText(message)
        error_dialog.exec()

    def delete_task(self):
        selected_item = self.task_list.currentItem()
        if selected_item:
            description = selected_item.text()

            # Remove from database
            delete_task(description, self.title)

            # Remove from UI
            self.task_list.takeItem(self.task_list.row(selected_item))

    def set_priority_color(self, task_item, priority):
        if priority == "Menial":
            task_item.setBackground(QColor(192, 192, 192))
        elif priority == "Semi Important":
            task_item.setBackground(QColor(255, 120, 0))
        elif priority == "Urgent":
            task_item.setBackground(QColor(255, 0, 0))




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Task Manager - Board View")
        self.setGeometry(100, 100, 1200, 800)

        self.board_layout = QGridLayout()

        self.boards = []
        self.create_board("To Do")
        self.create_board("In Progress")
        self.create_board("Done")

        self.load_tasks_from_database()

        container = QWidget()
        container.setLayout(self.board_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(container)

        self.setCentralWidget(scroll_area)

    def create_board(self, title):
        board = TaskBoard(title)
        self.boards.append(board)
        self.board_layout.addWidget(board, 0, len(self.boards) - 1)

    def load_tasks_from_database(self):
        tasks = load_tasks()
        for description, priority, category in tasks:
            for board in self.boards:
                if board.title == category:
                    task_item = QListWidgetItem(description)
                    board.set_priority_color(task_item, priority)
                    board.task_list.addItem(task_item)

def main():
    initialize_database()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
