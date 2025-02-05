"""
Manages the table layout and per-cell coloring logic.
"""

import tkinter as tk
from config import ROW_HEADERS, COL_HEADERS

class DataTable:
    def __init__(self, parent):
        """
        :param parent: A parent widget (Frame) where the table should live.
        """
        self.parent = parent
        self.row_headers = ROW_HEADERS
        self.col_headers = COL_HEADERS

        self.cell_labels = []  # 2D list of tk.Label references
        self.table_frame = tk.Frame(self.parent)
        self.table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.build_table()

    def build_table(self):
        """Create a grid of Labels: row/col headers + data cells."""
        # Clear anything in the table_frame (if rebuilding)
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        # -- Column Headers --
        for c, text in enumerate(self.col_headers):
            label = tk.Label(
                self.table_frame, text=text,
                width=10, bd=1, relief="solid", bg="#cccccc"
            )
            label.grid(row=0, column=c+1, sticky="nsew")

        # -- Row Headers + Data Cells --
        self.cell_labels.clear()
        for r, row_text in enumerate(self.row_headers):
            # Row Header (left column)
            row_label = tk.Label(
                self.table_frame, text=row_text,
                width=10, bd=1, relief="solid", bg="#cccccc"
            )
            row_label.grid(row=r+1, column=0, sticky="nsew")

            # Data cells
            row_cells = []
            for c in range(len(self.col_headers)):
                cell = tk.Label(
                    self.table_frame, text="",
                    width=10, bd=1, relief="solid", anchor="center"
                )
                cell.grid(row=r+1, column=c+1, sticky="nsew")
                row_cells.append(cell)

            self.cell_labels.append(row_cells)

        # Make the grid expand
        self.table_frame.grid_rowconfigure(0, weight=0)  # header row
        for r in range(1, 1 + len(self.row_headers)):
            self.table_frame.grid_rowconfigure(r, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=0)  # row headers
        for c in range(1, 1 + len(self.col_headers)):
            self.table_frame.grid_columnconfigure(c, weight=1)

    def update_table(self, data_matrix):
        """
        Update each cell in the grid with the corresponding string.
        Apply color if the string ends with '%'.

        :param data_matrix: 2D list [row][col] of strings.
        """
        for r in range(len(self.row_headers)):
            for c in range(len(self.col_headers)):
                cell_text = data_matrix[r][c]
                lbl = self.cell_labels[r][c]

                # Update text
                lbl.config(text=cell_text)

                # If the text ends with '%', interpret for coloring
                if cell_text.endswith("%"):
                    # e.g. "56,78%" => "56.78"
                    raw_value_str = cell_text[:-1].replace(",", ".")
                    try:
                        val = float(raw_value_str)
                    except ValueError:
                        val = 20.0  # fallback

                    # Linear mapping from 20 => green, 80 => red
                    fraction = (val - 20) / (80 - 20)
                    fraction = max(0.0, min(1.0, fraction))

                    red = int(255 * fraction)
                    green = int(255 * (1.0 - fraction))
                    blue = 0
                    color_hex = f"#{red:02x}{green:02x}{blue:02x}"

                    lbl.config(bg=color_hex)
                else:
                    # Non-numeric => white background
                    lbl.config(bg="white")
