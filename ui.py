"""
Defines the main Tkinter-based UI, including thresholds, buttons,
and calls into table.py and csv.py.
"""

import tkinter as tk
from tkinter import filedialog

from config import (
    ROW_HEADERS, 
    COL_HEADERS, 
    DEFAULT_THRESHOLD1, 
    DEFAULT_THRESHOLD2
)
from table import DataTable
from csv_handler import parse_csv

class VAGEDCSuiteDataViewer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("VAGEDCSuite Data Viewer")
        self.geometry("1100x500")

        # Main frame to hold left toolbar & the table
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1) --- Toolbar (left side) ---
        toolbar_frame = tk.Frame(main_frame, bg="#f0f0f0", width=150)
        toolbar_frame.pack(side=tk.LEFT, fill=tk.Y)

        # Threshold 1
        th1_label = tk.Label(toolbar_frame, text="Threshold 1:")
        th1_label.pack(anchor="w")
        self.th1_var = tk.StringVar(value=str(DEFAULT_THRESHOLD1))
        th1_entry = tk.Entry(toolbar_frame, textvariable=self.th1_var, width=10)
        th1_entry.pack(anchor="w", pady=(0, 10))

        # Threshold 2
        th2_label = tk.Label(toolbar_frame, text="Threshold 2:")
        th2_label.pack(anchor="w")
        self.th2_var = tk.StringVar(value=str(DEFAULT_THRESHOLD2))
        th2_entry = tk.Entry(toolbar_frame, textvariable=self.th2_var, width=10)
        th2_entry.pack(anchor="w", pady=(0, 10))

        # --- Mode Selector ---
        mode_label = tk.Label(toolbar_frame, text="Display Mode:")
        mode_label.pack(anchor="w")
        self.mode_var = tk.StringVar(value="Show original map")
        # Trace changes to the mode variable:
        self.mode_var.trace_add("write", self.mode_changed)

        mode_menu = tk.OptionMenu(
            toolbar_frame,
            self.mode_var,
            "Show original map",
            "Show original map color change"
        )
        mode_menu.pack(anchor="w", pady=(0, 10))

        # Button: "Paste from VAGEDCSuite"
        paste_button = tk.Button(
            toolbar_frame, 
            text="Paste from VAGEDCSuite", 
            command=self.paste_from_clipboard
        )
        paste_button.pack(pady=10, padx=10)

        # Button: "Pick CSV File"
        pick_csv_button = tk.Button(
            toolbar_frame,
            text="Pick CSV File",
            command=self.pick_csv_file
        )
        pick_csv_button.pack(pady=10, fill=tk.X)

        # 2) --- The Table (right side) ---
        self.data_table = DataTable(main_frame)

    def paste_from_clipboard(self):
        """Reads specialized data format from clipboard, updates the table cells/colors."""
        try:
            data_str = self.clipboard_get().strip()
        except tk.TclError:
            print("No valid clipboard data.")
            return

        if not (data_str.startswith("2") and data_str.endswith("~")):
            print("Invalid data pasted!")
            return

        data_str = data_str[1:].strip()  # remove leading '2'
        chunks = data_str.split(':~')
        chunks = [c.strip() for c in chunks if c.strip()]

        row_count = len(ROW_HEADERS)
        col_count = len(COL_HEADERS)

        data_matrix = [
            ["" for _ in range(col_count)] 
            for __ in range(row_count)
        ]

        for chunk in chunks:
            parts = chunk.split(':')
            if len(parts) != 3:
                continue

            col_str, row_str, val_str = parts
            try:
                col = int(col_str)
                row = int(row_str)
                val = int(val_str)
            except ValueError:
                continue

            if 0 <= row < row_count and 0 <= col < col_count:
                num_value = (10000 - val) / 100.0
                cell_text = f"{num_value:.2f}".replace('.', ',') + "%"
                data_matrix[row][col] = cell_text

        # Store the pasted data so we can reapply it later.
        self.last_pasted_data = data_matrix

        # Update the table with the pasted data.
        self.data_table.update_table(data_matrix)

        # If currently in the "color change" mode, update colors immediately.
        if self.mode_var.get() == "Show original map color change":
            if hasattr(self, "color_table") and self.color_table is not None:
                self.data_table.update_colors_from_csv(self.color_table)
            else:
                print("CSV data not loaded. Please pick a CSV file first.")

    def pick_csv_file(self):
        """
        Opens a file dialog to pick a CSV file and parse it.
        Output is printed to console and the averaged result is stored.
        """
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV Files", ("*.csv", "*.CSV")), ("All Files", "*.*")]
        )
        if not file_path:
            return

        # Convert threshold inputs
        try:
            th1 = float(self.th1_var.get())
        except ValueError:
            th1 = DEFAULT_THRESHOLD1

        try:
            th2 = float(self.th2_var.get())
        except ValueError:
            th2 = DEFAULT_THRESHOLD2

        # Save the averaged CSV table for use in color mapping.
        self.color_table = parse_csv(file_path, th1, th2)

    def mode_changed(self, *args):
        """
        Callback triggered when the display mode selection changes.
        If the mode is set to "Show original map color change" and CSV data is loaded,
        update the table using the CSV color scheme. Otherwise, revert to the original table.
        """
        new_mode = self.mode_var.get()
        if new_mode == "Show original map color change":
            if hasattr(self, "color_table") and self.color_table is not None:
                self.data_table.update_colors_from_csv(self.color_table)
            else:
                print("CSV data not loaded; cannot update color change mode.")
        else:  # new_mode is "Show original map"
            if hasattr(self, "last_pasted_data"):
                self.data_table.update_table(self.last_pasted_data)

