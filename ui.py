#!/usr/bin/env python3
import tkinter as tk
from tkinter import filedialog

from config import (
    ROW_HEADERS, 
    COL_HEADERS, 
    DEFAULT_THRESHOLD1, 
    DEFAULT_THRESHOLD2
)
from table import DataTable
from csv_handler import (
    parse_csv,
    average_distributed_results,
    print_distributed_table
)

class VAGEDCSuiteDataViewer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("VAGEDCSuite Data Viewer")
        self.geometry("1200x500")

        # Main frame to hold left toolbar & the table
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Toolbar (left side) ---
        toolbar_frame = tk.Frame(main_frame, bg="#f0f0f0", width=200)
        # Force a static width.
        toolbar_frame.pack_propagate(False)
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

        # --- Mode Selector ---
        mode_label = tk.Label(toolbar_frame, text="Display Mode:")
        mode_label.pack(anchor="w")
        # Now we include six modes.
        self.mode_options = [
            "Show original map",
            "Show original map color change",
            "Show updated map",
            "Show updated map color change",
            "Show fixed map",
            "Show fixed map color change"
        ]
        self.mode_var = tk.StringVar(value=self.mode_options[0])
        # Trace changes so that the table updates immediately on selection change.
        self.mode_var.trace_add("write", self.mode_changed)
        mode_menu = tk.OptionMenu(
            toolbar_frame,
            self.mode_var,
            *self.mode_options
        )
        mode_menu.pack(anchor="w", pady=(0, 10))

        # --- Checkbox to toggle column adjustment ---
        self.apply_column_fix_var = tk.BooleanVar(value=False)
        column_fix_checkbox = tk.Checkbutton(
            toolbar_frame,
            text="Adjust column differences",
            variable=self.apply_column_fix_var,
            bg="#f0f0f0"
        )
        column_fix_checkbox.pack(anchor="w", pady=(10, 0))

        # --- Fix table Button ---
        fix_button = tk.Button(toolbar_frame, text="Fix table", command=self.fix_table)
        fix_button.pack(pady=10, fill=tk.X)

        # --- Copy to VAGEDCSuite Button ---
        copy_button = tk.Button(toolbar_frame, text="Copy to VAGEDCSuite", command=self.copy_to_vagedcsuite)
        copy_button.pack(pady=10, fill=tk.X)

        # --- The Table (right side) ---
        self.data_table = DataTable(main_frame)

        # Store the last pasted table (a 2D list of strings) and CSV result.
        self.last_pasted_data = None
        self.color_table = None

    def paste_from_clipboard(self):
        """Reads specialized data format from clipboard and updates the table."""
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

        self.last_pasted_data = data_matrix
        # Update the display based on the current mode.
        self.mode_changed()

    def pick_csv_file(self):
        """
        Opens a file dialog to pick one or more CSV files, parses each one,
        and stores the averaged result from all CSV files.
        """
        # Use askopenfilenames (note the plural) to allow multiple file selection.
        file_paths = filedialog.askopenfilenames(
            title="Select CSV Files",
            filetypes=[("CSV Files", ("*.csv", "*.CSV")), ("All Files", "*.*")]
        )
        if not file_paths:
            return

        try:
            th1 = float(self.th1_var.get())
        except ValueError:
            th1 = DEFAULT_THRESHOLD1
        try:
            th2 = float(self.th2_var.get())
        except ValueError:
            th2 = DEFAULT_THRESHOLD2

        # Accumulate distributed results from each CSV file.
        all_distributed = []
        for file_path in file_paths:
            # parse_csv returns a list of dictionaries (distributed_results) for that file.
            distributed_results = parse_csv(file_path, th1, th2)
            # Extend our overall list.
            all_distributed.extend(distributed_results)

        # Average the accumulated results.
        avg_parsed_data = average_distributed_results(all_distributed, ROW_HEADERS, COL_HEADERS)
        print("\n--- Averaged Distributed Table - Final ---")
        print_distributed_table(avg_parsed_data, ROW_HEADERS, COL_HEADERS)

        self.color_table = avg_parsed_data

        # Update the table view (if pasted data already exists).
        if self.last_pasted_data is not None:
            self.mode_changed()


    def mode_changed(self, *args):
        """
        Callback when the display mode selection changes.
        Updates the table based on the chosen mode.
        """
        new_mode = self.mode_var.get()
        if new_mode == "Show original map":
            if self.last_pasted_data:
                self.data_table.update_table(self.last_pasted_data)
        elif new_mode == "Show original map color change":
            if self.last_pasted_data:
                self.data_table.update_table(self.last_pasted_data)
                if self.color_table is not None:
                    self.data_table.update_colors_from_csv(self.color_table)
                else:
                    print("CSV data not loaded; cannot update color change mode.")
        elif new_mode == "Show updated map":
            if self.last_pasted_data and self.color_table is not None:
                self.data_table.update_table_with_sum(self.last_pasted_data, self.color_table, use_csv_color=False)
            else:
                print("Either pasted data or CSV data is missing.")
        elif new_mode == "Show updated map color change":
            if self.last_pasted_data and self.color_table is not None:
                self.data_table.update_table_with_sum(self.last_pasted_data, self.color_table, use_csv_color=True)
                self.data_table.update_colors_from_csv(self.color_table)
            else:
                print("Either pasted data or CSV data is missing.")
        elif new_mode == "Show fixed map":
            if self.last_pasted_data and self.color_table is not None:
                self.data_table.fix_table(apply_column_fix=self.apply_column_fix_var.get())
            else:
                print("Either pasted data or CSV data is missing.")
        elif new_mode == "Show fixed map color change":
            if self.last_pasted_data and self.color_table is not None:
                self.data_table.fix_table(apply_column_fix=self.apply_column_fix_var.get())
                self.data_table.update_colors_from_csv(self.color_table)
            else:
                print("Either pasted data or CSV data is missing.")

    def fix_table(self):
        """Callback for the 'Fix table' button. Also changes the view to Show fixed map."""
        self.data_table.fix_table(apply_column_fix=self.apply_column_fix_var.get())
        self.mode_var.set("Show fixed map")

    def copy_to_vagedcsuite(self):
        """
        Reads the currently displayed map from the table,
        converts each cell's value back into the VAGEDCSuite integer format,
        and copies the resulting string to the clipboard.
        The conversion is the reverse of what 'Paste from VAGEDCSuite' does.
        """
        chunks = []
        # Iterate over the table's cells.
        for i, row in enumerate(self.data_table.cell_labels):
            for j, lbl in enumerate(row):
                text = lbl.cget("text")
                if text and text.endswith("%"):
                    # Remove the "%" and replace comma with dot.
                    try:
                        num_value = float(text.rstrip("%").replace(",", "."))
                    except ValueError:
                        continue
                    # Reverse the transformation: 
                    # pasted: num_value = (10000 - val) / 100  ==>  val = 10000 - num_value * 100
                    val_int = int(round(10000 - num_value * 100))
                    chunk = f"{j}:{i}:{val_int}"
                    chunks.append(chunk)
        if chunks:
            # Join chunks with ":~", prefix with "2" and suffix with "~"
            result = "2" + ":~".join(chunks) + "~"
            self.clipboard_clear()
            self.clipboard_append(result)
            print("Copied to clipboard:")
            print(result)
        else:
            print("No cell values to copy.")

def main():
    """Entry point for the application."""
    app = VAGEDCSuiteDataViewer()
    app.mainloop()

if __name__ == "__main__":
    main()
