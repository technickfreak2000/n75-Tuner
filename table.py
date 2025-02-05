"""
Manages the table layout and per-cell coloring logic.
"""

import tkinter as tk
from config import ROW_HEADERS, COL_HEADERS

# -----------------------
# Tooltip helper class
# -----------------------
class ToolTip:
    """
    A simple tooltip for a widget.
    """
    def __init__(self, widget, text='tooltip text'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.showtip()

    def leave(self, event=None):
        self.hidetip()

    def showtip(self):
        if self.tipwindow or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert") if self.widget.bbox("insert") else (0, 0, 0, 0)
        x = x + self.widget.winfo_rootx() + 20
        y = y + self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        if self.tipwindow:
            self.tipwindow.destroy()
        self.tipwindow = None

    def update_text(self, text):
        self.text = text

# -----------------------
# DataTable class
# -----------------------
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
            row_label = tk.Label(
                self.table_frame, text=row_text,
                width=10, bd=1, relief="solid", bg="#cccccc"
            )
            row_label.grid(row=r+1, column=0, sticky="nsew")

            row_cells = []
            for c in range(len(self.col_headers)):
                cell = tk.Label(
                    self.table_frame, text="",
                    width=10, bd=1, relief="solid", anchor="center"
                )
                cell.grid(row=r+1, column=c+1, sticky="nsew")
                row_cells.append(cell)
            self.cell_labels.append(row_cells)

        self.table_frame.grid_rowconfigure(0, weight=0)
        for r in range(1, 1 + len(self.row_headers)):
            self.table_frame.grid_rowconfigure(r, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=0)
        for c in range(1, 1 + len(self.col_headers)):
            self.table_frame.grid_columnconfigure(c, weight=1)

    def update_table(self, data_matrix):
        """
        Update each cell with the corresponding string.
        Applies the default color scheme (if the text ends with '%', a linear mapping from 20 to 80 is used).
        """
        for r in range(len(self.row_headers)):
            for c in range(len(self.col_headers)):
                cell_text = data_matrix[r][c]
                lbl = self.cell_labels[r][c]
                lbl.config(text=cell_text)
                # Remove any previous tooltip.
                if hasattr(lbl, "tooltip"):
                    lbl.tooltip.hidetip()
                    del lbl.tooltip
                # Clear any stored attributes.
                if hasattr(lbl, "old_value"):
                    del lbl.old_value
                if hasattr(lbl, "new_value"):
                    del lbl.new_value

                if cell_text.endswith("%"):
                    try:
                        val = float(cell_text[:-1].replace(",", "."))
                    except ValueError:
                        val = 20.0
                    fraction = (val - 20) / (80 - 20)
                    fraction = max(0.0, min(1.0, fraction))
                    red = int(255 * fraction)
                    green = int(255 * (1.0 - fraction))
                    blue = 0
                    color_hex = f"#{red:02x}{green:02x}{blue:02x}"
                    lbl.config(bg=color_hex)
                else:
                    lbl.config(bg="white")

    def update_colors_from_csv(self, csv_table):
        """
        Updates the cell background colors using CSV values.
        For each cell, looks up its CSV value (keyed by (row_header, col_header))
        and applies:
          - 0 → green (#00ff00)
          - For positive values: 0 maps to green and the maximum positive maps to red.
          - For negative values: 0 maps to green and the most negative maps to blue.
        """
        pos_values = [v for v in csv_table.values() if v > 0]
        neg_values = [v for v in csv_table.values() if v < 0]
        max_positive = max(pos_values) if pos_values else 0
        min_negative = min(neg_values) if neg_values else 0

        for i, row_header in enumerate(self.row_headers):
            for j, col_header in enumerate(self.col_headers):
                value = csv_table.get((row_header, col_header), 0)
                lbl = self.cell_labels[i][j]
                if value == 0:
                    color = "#00ff00"
                elif value > 0:
                    fraction = value / max_positive if max_positive != 0 else 0
                    red = int(255 * fraction)
                    green = 255 - red
                    blue = 0
                    color = f"#{red:02x}{green:02x}{blue:02x}"
                else:
                    fraction = value / min_negative if min_negative != 0 else 0
                    blue = int(255 * fraction)
                    green = 255 - blue
                    red = 0
                    color = f"#{red:02x}{green:02x}{blue:02x}"
                lbl.config(bg=color)

    def update_table_with_sum(self, pasted_data, csv_table, use_csv_color=False):
        """
        For each cell, parses the original (pasted) value and adds the CSV value,
        updates the cell text to show the updated value, and attaches a tooltip showing
        "old value -> new value". Also stores the parsed old and new values in the label.
        If use_csv_color is False, the default color mapping is applied.
        If True, the CSV color mapping (via update_colors_from_csv) is used.
        """
        num_rows = len(pasted_data)
        num_cols = len(self.col_headers)
        for i in range(num_rows):
            for j in range(num_cols):
                old_text = pasted_data[i][j]
                lbl = self.cell_labels[i][j]
                # Parse the old value.
                if old_text.endswith("%"):
                    try:
                        old_value = float(old_text[:-1].replace(",", "."))
                    except ValueError:
                        old_value = 0
                else:
                    try:
                        old_value = float(old_text.replace(",", "."))
                    except ValueError:
                        old_value = 0
                # Lookup the CSV value.
                row_header = self.row_headers[i]
                col_header = self.col_headers[j]
                csv_value = csv_table.get((row_header, col_header), 0)
                new_value = old_value + csv_value
                # Store these values for later use.
                lbl.old_value = old_value
                lbl.new_value = new_value

                new_text = f"{new_value:.2f}".replace(".", ",") + "%"
                lbl.config(text=new_text)
                tooltip_text = f"{old_text} -> {new_text}"
                if hasattr(lbl, "tooltip"):
                    lbl.tooltip.update_text(tooltip_text)
                else:
                    lbl.tooltip = ToolTip(lbl, tooltip_text)

        # Now update colors.
        if not use_csv_color:
            for i in range(num_rows):
                for j in range(num_cols):
                    lbl = self.cell_labels[i][j]
                    cell_text = lbl.cget("text")
                    if cell_text.endswith("%"):
                        try:
                            val = float(cell_text[:-1].replace(",", "."))
                        except ValueError:
                            val = 20.0
                    else:
                        try:
                            val = float(cell_text.replace(",", "."))
                        except ValueError:
                            val = 20.0
                    fraction = (val - 20) / (80 - 20)
                    fraction = max(0.0, min(1.0, fraction))
                    red = int(255 * fraction)
                    green = int(255 * (1.0 - fraction))
                    blue = 0
                    color_hex = f"#{red:02x}{green:02x}{blue:02x}"
                    lbl.config(bg=color_hex)
        else:
            self.update_colors_from_csv(csv_table)

    def fix_table(self):
        """
        Fixes the updated table as follows:
          1. For each cell, round the updated value using standard rounding
             (so 19,37 → 19 and 19,98 → 20).
          2. Then, for each column (iterating from bottom to top), if the cell above
             is not at least 1 greater than the cell below, adjust it to be exactly 1 more.
             This column-fixing is applied only to cells with values above 20 (cells ≤20 are ignored).
        After fixing, each cell’s tooltip is updated to show:
          "old value -> new value -> new value rounded -> fixed value"
        The fixed values are displayed as XX,XX%.
        """
        num_rows = len(self.row_headers)
        num_cols = len(self.col_headers)
        # Create matrices for the rounded and fixed values.
        rounded = [[0 for _ in range(num_cols)] for _ in range(num_rows)]
        fixed = [[0 for _ in range(num_cols)] for _ in range(num_rows)]

        # First, for each cell, get the updated value (from lbl.new_value) and round it.
        # Use standard rounding (so that 19,37 rounds to 19 and 19,98 rounds to 20).
        for i in range(num_rows):
            for j in range(num_cols):
                lbl = self.cell_labels[i][j]
                if hasattr(lbl, "new_value"):
                    new_val = lbl.new_value
                else:
                    try:
                        text = lbl.cget("text")
                        new_val = float(text.replace(",", ".").rstrip("%"))
                    except:
                        new_val = 0
                rounded[i][j] = round(new_val)
                fixed[i][j] = rounded[i][j]

        # Then, for each column, from bottom to top,
        # adjust only cells whose values are above 20.
        for j in range(num_cols):
            for i in range(num_rows - 1, 0, -1):
                # Only adjust if both the current cell and the one above are greater than 20.
                if fixed[i][j] > 20 and fixed[i-1][j] > 20:
                    if fixed[i-1][j] < fixed[i][j] + 1:
                        fixed[i-1][j] = fixed[i][j] + 1

        # Update each cell's text and tooltip.
        for i in range(num_rows):
            for j in range(num_cols):
                lbl = self.cell_labels[i][j]
                old_val = lbl.old_value if hasattr(lbl, "old_value") else 0
                new_val = lbl.new_value if hasattr(lbl, "new_value") else 0
                new_rounded = rounded[i][j]
                fixed_val = fixed[i][j]
                # Format each value as XX,XX%
                old_text = f"{old_val:.2f}".replace(".", ",") + "%"
                new_text = f"{new_val:.2f}".replace(".", ",") + "%"
                new_rounded_text = f"{new_rounded:.2f}".replace(".", ",") + "%"
                fixed_text = f"{fixed_val:.2f}".replace(".", ",") + "%"
                # Update the cell's text to the fixed value.
                lbl.config(text=fixed_text)
                tooltip_text = f"{old_text} -> {new_text} -> {new_rounded_text} -> {fixed_text}"
                if hasattr(lbl, "tooltip"):
                    lbl.tooltip.update_text(tooltip_text)
                else:
                    lbl.tooltip = ToolTip(lbl, tooltip_text)
