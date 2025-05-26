from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTableView, QPushButton, QFileDialog, QMessageBox,
                             QLineEdit, QLabel, QGroupBox, QInputDialog, QAction,
                             QTextEdit, QDialog, QDialogButtonBox, QCheckBox, QScrollArea)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import qdarkstyle
import pandas as pd
from table_model import VCFTableModel, VCFProxyModel
from vcf_handler import VCFHandler
import re
from PyQt5.QtWidgets import QApplication
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

def normalize_phone(phone):
    """Normalizes phone numbers by removing non-digit characters and ensuring proper format"""
    if pd.isna(phone):
        return phone
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone))
    
    # If empty after cleaning, return original
    if not digits:
        return phone
    
    # If starts with 0, remove it
    if digits.startswith('0'):
        digits = digits[1:]
    
    # If starts with 90, remove it
    if digits.startswith('90'):
        digits = digits[2:]
    
    # If less than 10 digits, return original
    if len(digits) < 10:
        return phone
    
    # Format as +90 5XX XXX XX XX
    if len(digits) == 10:
        return f"+90 {digits[:3]} {digits[3:6]} {digits[6:8]} {digits[8:]}"
    
    return phone

class MatchDialog(QDialog):
    def __init__(self, matches, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Matching Records")
        self.setMinimumSize(600, 400)
        
        # Store matches
        self.matches = matches
        self.selected_indices = []
        self.checkboxes = []  # Store checkboxes for select all functionality
        
        # Create layout
        layout = QVBoxLayout()
        
        # Add Select All button
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        layout.addWidget(select_all_btn)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Add matches with checkboxes
        for ref_name, contact_name, score in matches:
            match_widget = QWidget()
            match_layout = QHBoxLayout()
            
            # Checkbox
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(lambda state, idx=len(self.selected_indices): self.on_checkbox_changed(state, idx))
            match_layout.addWidget(checkbox)
            self.checkboxes.append(checkbox)  # Store checkbox
            
            # Match details
            details = QLabel(f"Reference: {ref_name}\nContact: {contact_name}\nScore: {score}%")
            match_layout.addWidget(details)
            
            match_widget.setLayout(match_layout)
            scroll_layout.addWidget(match_widget)
            self.selected_indices.append(None)  # Placeholder for selected index
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def select_all(self):
        """Selects all checkboxes"""
        for checkbox in self.checkboxes:
            checkbox.setChecked(True)
    
    def on_checkbox_changed(self, state, index):
        if state == Qt.Checked:
            self.selected_indices[index] = self.matches[index][1]  # Store contact name
        else:
            self.selected_indices[index] = None
    
    def get_selected_matches(self):
        return [idx for idx in self.selected_indices if idx is not None]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VCF Editor")
        self.setMinimumSize(800, 600)
        
        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Table model and view
        self.table_model = VCFTableModel()
        self.proxy_model = VCFProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setAlternatingRowColors(True)  # Alternating row colors
        self.table_view.setSelectionBehavior(QTableView.SelectRows)  # Row selection
        self.table_view.setSelectionMode(QTableView.ExtendedSelection)  # Multiple selection
        self.layout.addWidget(self.table_view)
        
        # Filter fields
        self.create_filter_section()
        
        # Buttons
        self.create_buttons()
        
        # VCF handler
        self.vcf_handler = VCFHandler()
        
        # Create menu
        self.create_menu()
        
        # Apply style
        self.apply_theme('dark')  # Default theme
        
        # Fuzzy match threshold
        self.fuzzy_threshold = 80  # Default threshold for fuzzy matching
    
    def apply_theme(self, theme):
        """Applies theme"""
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    def create_filter_section(self):
        """Creates filtering fields"""
        filter_group = QGroupBox("Filtering")
        filter_layout = QHBoxLayout()
        
        # Filter field for each column
        self.filter_inputs = {}
        for column in self.table_model._columns:
            filter_widget = QWidget()
            filter_widget_layout = QVBoxLayout()
            
            label = QLabel(column)
            input_field = QLineEdit()
            input_field.setPlaceholderText(f"Search {column}... (use !word1,word2 for except)")
            input_field.textChanged.connect(lambda text, col=column: self.filter_changed(col, text))
            
            filter_widget_layout.addWidget(label)
            filter_widget_layout.addWidget(input_field)
            filter_widget.setLayout(filter_widget_layout)
            
            self.filter_inputs[column] = input_field
            filter_layout.addWidget(filter_widget)
        
        filter_group.setLayout(filter_layout)
        self.layout.addWidget(filter_group)
    
    def filter_changed(self, column, text):
        """Called when filter text changes"""
        self.proxy_model.set_filter(self.table_model._columns.index(column), text)
    
    def create_buttons(self):
        """Creates basic operation buttons"""
        button_layout = QHBoxLayout()  # Main layout will be horizontal
        
        # Left column
        left_column = QVBoxLayout()
        left_column.addWidget(QLabel("File Operations"))
        
        # File operation buttons
        self.btn_open = QPushButton("Open VCF")
        self.btn_save = QPushButton("Save VCF")
        self.btn_save_ios = QPushButton("Save VCF (iOS)")
        self.btn_export = QPushButton("Export as CSV")
        
        for btn in [self.btn_open, self.btn_save, self.btn_save_ios, self.btn_export]:
            left_column.addWidget(btn)
        
        # Right column
        right_column = QVBoxLayout()
        right_column.addWidget(QLabel("Data Editing"))
        
        # Data editing buttons
        self.btn_remove_duplicates = QPushButton("Remove Duplicates")
        self.btn_normalize_phones = QPushButton("Normalize Phone Numbers")
        self.btn_title_case = QPushButton("Title Case Names")
        self.btn_append_code = QPushButton("Append Code to Names")
        self.btn_last_word_upper = QPushButton("Make Last Word Upper")
        self.btn_replace_text = QPushButton("Replace/Delete Text")
        self.btn_delete_selected = QPushButton("Delete Selected")
        self.btn_find_matches = QPushButton("Find Matches from List")
        
        for btn in [self.btn_remove_duplicates, self.btn_normalize_phones,
                   self.btn_title_case, self.btn_append_code,
                   self.btn_last_word_upper, self.btn_replace_text,
                   self.btn_delete_selected, self.btn_find_matches]:
            right_column.addWidget(btn)
        
        # Add columns to main layout
        button_layout.addLayout(left_column)
        button_layout.addLayout(right_column)
        
        self.layout.addLayout(button_layout)
        
        # Signal connections
        self.btn_open.clicked.connect(self.open_vcf)
        self.btn_save.clicked.connect(self.save_vcf)
        self.btn_save_ios.clicked.connect(self.save_vcf_ios)
        self.btn_export.clicked.connect(self.export_csv)
        self.btn_remove_duplicates.clicked.connect(self.remove_duplicates)
        self.btn_normalize_phones.clicked.connect(self.normalize_phones)
        self.btn_title_case.clicked.connect(self.title_case_names)
        self.btn_append_code.clicked.connect(self.append_code_to_names)
        self.btn_last_word_upper.clicked.connect(self.last_word_upper)
        self.btn_replace_text.clicked.connect(self.replace_text)
        self.btn_delete_selected.clicked.connect(self.delete_selected)
        self.btn_find_matches.clicked.connect(self.find_matches_from_list)
    
    def create_menu(self):
        """Creates main menu"""
        menubar = self.menuBar()
        
        # File menu
        self.file_menu = menubar.addMenu("File")
        self.action_open = QAction("Open VCF", self)
        self.action_save = QAction("Save VCF", self)
        self.action_save_ios = QAction("Save VCF (iOS)", self)
        self.action_export = QAction("Export as CSV", self)
        self.action_exit = QAction("Exit", self)
        
        self.file_menu.addAction(self.action_open)
        self.file_menu.addAction(self.action_save)
        self.file_menu.addAction(self.action_save_ios)
        self.file_menu.addAction(self.action_export)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.action_exit)
        
        # Edit menu
        self.edit_menu = menubar.addMenu("Edit")
        self.edit_menu.addAction("Remove Duplicates", self.remove_duplicates)
        self.edit_menu.addAction("Normalize Phone Numbers", self.normalize_phones)
        self.edit_menu.addAction("Title Case Names", self.title_case_names)
        self.edit_menu.addAction("Append Code to Names", self.append_code_to_names)
        self.edit_menu.addAction("Make Last Word Upper", self.last_word_upper)
        self.edit_menu.addAction("Replace/Delete Text", self.replace_text)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction("Delete Selected", self.delete_selected)
        self.edit_menu.addAction("Find Matches from List", self.find_matches_from_list)
        
        # View menu
        self.view_menu = menubar.addMenu("View")
        
        # Signal connections
        self.action_open.triggered.connect(self.open_vcf)
        self.action_save.triggered.connect(self.save_vcf)
        self.action_save_ios.triggered.connect(self.save_vcf_ios)
        self.action_export.triggered.connect(self.export_csv)
        self.action_exit.triggered.connect(self.close)
    
    def open_vcf(self):
        """Opens VCF file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open VCF File", "", "VCF Files (*.vcf)"
        )
        if file_name:
            try:
                df = self.vcf_handler.parse_vcf(file_name)
                self.table_model.set_data(df)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error opening file: {str(e)}")
    
    def save_vcf(self):
        """Saves as VCF file"""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save as VCF", "", "VCF Files (*.vcf)"
        )
        if file_name:
            try:
                df = self.table_model.get_data()
                
                # Ask for iOS compatibility
                ios_compatible = QMessageBox.question(
                    self,
                    "iOS Compatibility",
                    "Do you want to save in iOS-compatible format?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                ) == QMessageBox.Yes
                
                self.vcf_handler.export_vcf(df, file_name, ios_compatible)
                QMessageBox.information(self, "Success", "File saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving file: {str(e)}")
    
    def save_vcf_ios(self):
        """Saves as iOS-compatible VCF file"""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save as iOS VCF", "", "VCF Files (*.vcf)"
        )
        if file_name:
            try:
                df = self.table_model.get_data()
                self.vcf_handler.export_vcf(df, file_name, ios_compatible=True)
                QMessageBox.information(self, "Success", "File saved successfully in iOS-compatible format.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error saving file: {str(e)}")
    
    def export_csv(self):
        """Exports as CSV"""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export as CSV", "", "CSV Files (*.csv)"
        )
        if file_name:
            try:
                df = self.table_model.get_data()
                df.to_csv(file_name, index=False)
                QMessageBox.information(self, "Success", "File exported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error exporting file: {str(e)}")
    
    def get_selected_rows(self):
        """Returns indices of selected rows"""
        selected_rows = []
        for index in self.table_view.selectionModel().selectedRows():
            # Convert from proxy model to source model index
            source_index = self.proxy_model.mapToSource(index)
            selected_rows.append(source_index.row())
        return selected_rows
    
    def remove_duplicates(self):
        """Removes duplicate records using both exact and fuzzy matching"""
        df = self.table_model.get_data()
        if df.empty:
            QMessageBox.warning(self, "Warning", "No data in table.")
            return
        
        # Get selected rows
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select records to check.")
            return
        
        # Get matching type
        match_type, ok = QInputDialog.getItem(
            self, "Select Matching Type",
            "How would you like to check for duplicates?",
            ["Exact Match (Name + Phone)", "Fuzzy Name Match", "Exact Phone Match"],
            0, False
        )
        
        if not ok:
            return
        
        # Check for duplicates in selected rows
        selected_df = df.iloc[selected_rows].copy()
        duplicates = pd.Series(False, index=selected_df.index)
        
        if match_type == "Exact Match (Name + Phone)":
            duplicates = selected_df.duplicated(subset=['Name', 'Phone'], keep='first')
        elif match_type == "Exact Phone Match":
            duplicates = selected_df.duplicated(subset=['Phone'], keep='first')
        else:  # Fuzzy Name Match
            # Get fuzzy match threshold
            threshold, ok = QInputDialog.getInt(
                self, "Fuzzy Match Threshold",
                "Enter similarity threshold (0-100):",
                self.fuzzy_threshold, 0, 100, 5
            )
            
            if not ok:
                return
            
            self.fuzzy_threshold = threshold
            
            # Find fuzzy matches
            names = selected_df['Name'].tolist()
            for i, name1 in enumerate(names):
                if pd.isna(name1):
                    continue
                for j, name2 in enumerate(names[i+1:], i+1):
                    if pd.isna(name2):
                        continue
                    if fuzz.ratio(name1.lower(), name2.lower()) >= threshold:
                        duplicates.iloc[j] = True
        
        if not duplicates.any():
            QMessageBox.information(self, "Info", "No duplicates found in selected records.")
            return
        
        # Show duplicates and ask for confirmation
        duplicate_count = duplicates.sum()
        
        # Create a scrollable text area for details
        details = QTextEdit()
        details.setReadOnly(True)
        details.setMaximumHeight(200)
        
        # Add duplicate records to text area
        details.append(f"Found {duplicate_count} duplicate records in {len(selected_rows)} selected records:\n")
        for idx, row in selected_df[duplicates].iterrows():
            details.append(f"Name: {row['Name']}\nPhone: {row['Phone']}\n---")
        
        # Create custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Duplicate Records")
        layout = QVBoxLayout()
        
        # Add text area
        layout.addWidget(details)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # Remove duplicates from selected rows
            selected_df = selected_df[~duplicates]
            
            # Create a new DataFrame with non-selected rows
            non_selected_df = df.drop(index=df.index[selected_rows])
            
            # Concatenate non-selected rows with deduplicated selected rows
            df = pd.concat([non_selected_df, selected_df])
            
            # Update the table model
            self.table_model.set_data(df)
            
            QMessageBox.information(self, "Success", f"Deleted {duplicate_count} duplicate records.")
    
    def normalize_phones(self):
        """Normalizes phone numbers"""
        df = self.table_model.get_data()
        if df.empty:
            QMessageBox.warning(self, "Warning", "No data in table.")
            return
        
        # Get selected rows
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select records to edit.")
            return
        
        # Save old phone numbers
        old_phones = df.loc[selected_rows, 'Phone'].copy()
        
        # Normalize
        df.loc[selected_rows, 'Phone'] = df.loc[selected_rows, 'Phone'].apply(normalize_phone)
        
        # Calculate changed count
        changed_count = (old_phones != df.loc[selected_rows, 'Phone']).sum()
        
        # Show results
        if changed_count > 0:
            # Create a scrollable text area for details
            details = QTextEdit()
            details.setReadOnly(True)
            details.setMaximumHeight(200)
            
            # Add changed numbers to text area
            details.append(f"Normalized {changed_count} phone numbers out of {len(selected_rows)} selected records:\n")
            changed_phones = pd.DataFrame({
                'Old Number': old_phones[old_phones != df.loc[selected_rows, 'Phone']],
                'New Number': df.loc[selected_rows, 'Phone'][old_phones != df.loc[selected_rows, 'Phone']]
            })
            for _, row in changed_phones.iterrows():
                details.append(f"{row['Old Number']} → {row['New Number']}")
            
            # Create custom dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Phone Number Changes")
            layout = QVBoxLayout()
            
            # Add text area
            layout.addWidget(details)
            
            # Add OK button
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(dialog.accept)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            dialog.exec_()
        else:
            QMessageBox.information(self, "Info", "No valid phone numbers found to normalize.")
        
        self.table_model.set_data(df)
    
    def title_case_names(self):
        """Converts names to title case"""
        df = self.table_model.get_data()
        if df.empty:
            QMessageBox.warning(self, "Warning", "No data in table.")
            return
        
        # Get selected rows
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select records to edit.")
            return
        
        # Save old names
        old_names = df.loc[selected_rows, 'Name'].copy()
        
        # Apply title case
        df.loc[selected_rows, 'Name'] = df.loc[selected_rows, 'Name'].str.title()
        
        # Calculate changed count
        changed_count = (old_names != df.loc[selected_rows, 'Name']).sum()
        
        # Show results
        if changed_count > 0:
            # Create a scrollable text area for details
            details = QTextEdit()
            details.setReadOnly(True)
            details.setMaximumHeight(200)
            
            # Add changed names to text area
            details.append(f"Converted {changed_count} names to title case out of {len(selected_rows)} selected records:\n")
            changed_names = pd.DataFrame({
                'Old Name': old_names[old_names != df.loc[selected_rows, 'Name']],
                'New Name': df.loc[selected_rows, 'Name'][old_names != df.loc[selected_rows, 'Name']]
            })
            for _, row in changed_names.iterrows():
                details.append(f"{row['Old Name']} → {row['New Name']}")
            
            # Create custom dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Name Changes")
            layout = QVBoxLayout()
            
            # Add text area
            layout.addWidget(details)
            
            # Add OK button
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(dialog.accept)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            dialog.exec_()
        else:
            QMessageBox.information(self, "Info", "No names found to convert.")
        
        self.table_model.set_data(df)
    
    def append_code_to_names(self):
        """Appends code to names"""
        df = self.table_model.get_data()
        if df.empty:
            QMessageBox.warning(self, "Warning", "No data in table.")
            return
        
        # Get selected rows
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select records to edit.")
            return
        
        code, ok = QInputDialog.getText(
            self, "Append Code",
            "Enter code to append:"
        )
        
        if ok and code:
            position, ok = QInputDialog.getItem(
                self, "Select Position",
                "Select where to add the code:",
                ["Add to Start", "Add to End"],
                0, False
            )
            
            if ok:
                # Save old names
                old_names = df.loc[selected_rows, 'Name'].copy()
                
                # Add code
                if position == "Add to Start":
                    df.loc[selected_rows, 'Name'] = code + " " + df.loc[selected_rows, 'Name']
                else:
                    df.loc[selected_rows, 'Name'] = df.loc[selected_rows, 'Name'] + " " + code
                
                # Calculate changed count
                changed_count = (old_names != df.loc[selected_rows, 'Name']).sum()
                
                # Show results
                if changed_count > 0:
                    # Create a scrollable text area for details
                    details = QTextEdit()
                    details.setReadOnly(True)
                    details.setMaximumHeight(200)
                    
                    # Add changed names to text area
                    details.append(f"Added code to {changed_count} names out of {len(selected_rows)} selected records:\n")
                    changed_names = pd.DataFrame({
                        'Old Name': old_names[old_names != df.loc[selected_rows, 'Name']],
                        'New Name': df.loc[selected_rows, 'Name'][old_names != df.loc[selected_rows, 'Name']]
                    })
                    for _, row in changed_names.iterrows():
                        details.append(f"{row['Old Name']} → {row['New Name']}")
                    
                    # Create custom dialog
                    dialog = QDialog(self)
                    dialog.setWindowTitle("Name Changes")
                    layout = QVBoxLayout()
                    
                    # Add text area
                    layout.addWidget(details)
                    
                    # Add OK button
                    button_box = QDialogButtonBox(QDialogButtonBox.Ok)
                    button_box.accepted.connect(dialog.accept)
                    layout.addWidget(button_box)
                    
                    dialog.setLayout(layout)
                    dialog.exec_()
                else:
                    QMessageBox.information(self, "Info", "No names found to modify.")
                
                self.table_model.set_data(df)
    
    def last_word_upper(self):
        """Makes the last word of names uppercase"""
        df = self.table_model.get_data()
        if df.empty:
            QMessageBox.warning(self, "Warning", "No data in table.")
            return
        
        # Get selected rows
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select records to edit.")
            return
        
        # Save old names
        old_names = df.loc[selected_rows, 'Name'].copy()
        
        # Make last word uppercase
        def make_last_word_upper(name):
            if pd.isna(name):
                return name
            words = name.split()
            if words:
                words[-1] = words[-1].upper()
            return ' '.join(words)
        
        df.loc[selected_rows, 'Name'] = df.loc[selected_rows, 'Name'].apply(make_last_word_upper)
        
        # Calculate changed count
        changed_count = (old_names != df.loc[selected_rows, 'Name']).sum()
        
        # Show results
        if changed_count > 0:
            # Create a scrollable text area for details
            details = QTextEdit()
            details.setReadOnly(True)
            details.setMaximumHeight(200)
            
            # Add changed names to text area
            details.append(f"Made last word uppercase in {changed_count} names out of {len(selected_rows)} selected records:\n")
            changed_names = pd.DataFrame({
                'Old Name': old_names[old_names != df.loc[selected_rows, 'Name']],
                'New Name': df.loc[selected_rows, 'Name'][old_names != df.loc[selected_rows, 'Name']]
            })
            for _, row in changed_names.iterrows():
                details.append(f"{row['Old Name']} → {row['New Name']}")
            
            # Create custom dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Name Changes")
            layout = QVBoxLayout()
            
            # Add text area
            layout.addWidget(details)
            
            # Add OK button
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(dialog.accept)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            dialog.exec_()
        else:
            QMessageBox.information(self, "Info", "No names found to modify.")
        
        self.table_model.set_data(df)
    
    def replace_text(self):
        """Replaces or deletes text in selected records"""
        df = self.table_model.get_data()
        if df.empty:
            QMessageBox.warning(self, "Warning", "No data in table.")
            return
        
        # Get selected rows
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select records to edit.")
            return
        
        # Get search text
        search_text, ok = QInputDialog.getText(
            self, "Replace/Delete Text",
            "Enter text to search:"
        )
        
        if ok and search_text:
            # Get replacement text
            replace_text, ok = QInputDialog.getText(
                self, "Replace/Delete Text",
                "Enter new text (leave empty to delete):"
            )
            
            if ok:
                # Save old names
                old_names = df.loc[selected_rows, 'Name'].copy()
                
                # Replace or delete text
                df.loc[selected_rows, 'Name'] = df.loc[selected_rows, 'Name'].str.replace(
                    search_text, replace_text, case=False, regex=False
                )
                
                # Calculate changed count
                changed_count = (old_names != df.loc[selected_rows, 'Name']).sum()
                
                # Show results
                if changed_count > 0:
                    # Create a scrollable text area for details
                    details = QTextEdit()
                    details.setReadOnly(True)
                    details.setMaximumHeight(200)
                    
                    # Add changed names to text area
                    action = "deleted" if not replace_text else "replaced"
                    details.append(f"{action.capitalize()} '{search_text}' in {changed_count} names out of {len(selected_rows)} selected records:\n")
                    changed_names = pd.DataFrame({
                        'Old Name': old_names[old_names != df.loc[selected_rows, 'Name']],
                        'New Name': df.loc[selected_rows, 'Name'][old_names != df.loc[selected_rows, 'Name']]
                    })
                    for _, row in changed_names.iterrows():
                        details.append(f"{row['Old Name']} → {row['New Name']}")
                    
                    # Create custom dialog
                    dialog = QDialog(self)
                    dialog.setWindowTitle("Name Changes")
                    layout = QVBoxLayout()
                    
                    # Add text area
                    layout.addWidget(details)
                    
                    # Add OK button
                    button_box = QDialogButtonBox(QDialogButtonBox.Ok)
                    button_box.accepted.connect(dialog.accept)
                    layout.addWidget(button_box)
                    
                    dialog.setLayout(layout)
                    dialog.exec_()
                else:
                    QMessageBox.information(self, "Info", f"No names containing '{search_text}' found.")
                
                self.table_model.set_data(df) 
    
    def delete_selected(self):
        """Deletes selected records"""
        df = self.table_model.get_data()
        if df.empty:
            QMessageBox.warning(self, "Warning", "No data in table.")
            return
        
        # Get selected rows
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select records to delete.")
            return
        
        # Create a scrollable text area for details
        details = QTextEdit()
        details.setReadOnly(True)
        details.setMaximumHeight(200)
        
        # Add selected records to text area
        details.append(f"Selected {len(selected_rows)} records to delete:\n")
        for idx in selected_rows:
            row = df.iloc[idx]
            details.append(f"Name: {row['Name']}\nPhone: {row['Phone']}\n---")
        
        # Create custom dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Delete Records")
        layout = QVBoxLayout()
        
        # Add text area
        layout.addWidget(details)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # Remove selected rows
            df = df.drop(index=df.index[selected_rows])
            
            # Update the table model
            self.table_model.set_data(df)
            
            QMessageBox.information(self, "Success", f"Deleted {len(selected_rows)} records.")
    
    def find_matches_from_list(self):
        """Finds matches from a reference list"""
        # Get reference list file
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Reference List", "", "Text Files (*.txt);;CSV Files (*.csv)"
        )
        
        if not file_name:
            return
        
        try:
            # Read reference list
            if file_name.endswith('.csv'):
                ref_df = pd.read_csv(file_name)
                ref_names = ref_df.iloc[:, 0].tolist()  # Assume names are in first column
            else:
                with open(file_name, 'r', encoding='utf-8') as f:
                    ref_names = [line.strip() for line in f if line.strip()]
            
            # Get current contact names
            df = self.table_model.get_data()
            contact_names = df['Name'].tolist()
            
            # Get matching type
            match_type, ok = QInputDialog.getItem(
                self, "Select Matching Type",
                "How would you like to match names?",
                ["Exact Match", "Token Sort Ratio", "Token Set Ratio"],
                0, False
            )
            
            if not ok:
                return
            
            # Get threshold
            threshold, ok = QInputDialog.getInt(
                self, "Match Threshold",
                "Enter similarity threshold (0-100):",
                self.fuzzy_threshold, 0, 100, 5
            )
            
            if not ok:
                return
            
            self.fuzzy_threshold = threshold
            
            # Find matches
            matches = []
            for ref_name in ref_names:
                if match_type == "Exact Match":
                    # Exact match
                    exact_matches = [(ref_name, name, 100) for name in contact_names 
                                   if name.lower() == ref_name.lower()]
                    matches.extend(exact_matches)
                else:
                    # Fuzzy match
                    scorer = fuzz.token_sort_ratio if match_type == "Token Sort Ratio" else fuzz.token_set_ratio
                    fuzzy_matches = process.extract(
                        ref_name,
                        contact_names,
                        scorer=scorer,
                        limit=3
                    )
                    good_matches = [(ref_name, name, score) for name, score in fuzzy_matches if score >= threshold]
                    matches.extend(good_matches)
            
            if not matches:
                QMessageBox.information(self, "Info", "No matches found.")
                return
            
            # Show matches dialog
            dialog = MatchDialog(matches, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_names = dialog.get_selected_matches()
                
                if not selected_names:
                    QMessageBox.warning(self, "Warning", "No matches selected.")
                    return
                
                # Select matched rows in table
                self.table_view.clearSelection()
                selection_model = self.table_view.selectionModel()
                
                # Get the source model indices
                for name in selected_names:
                    # Find all rows with this name
                    matches = df.index[df['Name'] == name].tolist()
                    for idx in matches:
                        # Convert to proxy model index
                        source_index = self.table_model.index(idx, 0)
                        proxy_index = self.proxy_model.mapFromSource(source_index)
                        if proxy_index.isValid():
                            # Select the row
                            selection_model.select(proxy_index, selection_model.Select | selection_model.Rows)
                
                QMessageBox.information(self, "Success", 
                    f"Selected {len(selected_names)} matches. You can now perform operations on these records.")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error processing reference list: {str(e)}") 