import csv
from config import (
    ROW_HEADERS, 
    COL_HEADERS
)

def parse_csv(file_path, th1, th2):
    """
    Opens the CSV file at 'file_path', reads each row into a data structure,
    and then analyzes and prints a formatted table to the console.
    
    Skips invalid rows. Checks:
      - If Inj Qty requested > previous => "Acceleration start detected"
      - If Actual intake press is above Spec intake press by at least a threshold => "TH1" or "TH2"
      - If Actual intake press is below Spec intake press by at least a threshold => "UnderTH1" or "UnderTH2"
    
    Also prints the Inj Qty (actual).
    """

    print(f"\n--- Parsing CSV: {file_path} ---")
    print(f"Using Threshold1={th1}, Threshold2={th2}")

    # First, load the CSV data into a list of dictionaries.
    data = []
    with open(file_path, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter=",")
        for row in reader:
            # Ensure there are at least 11 columns (indexed 0 to 10)
            if len(row) < 11:
                continue

            try:
                row_data = {
                    'time': float(row[1]),
                    'eng_speed': float(row[2]),
                    'spec_int': float(row[3]),
                    'act_int': float(row[4]),
                    'inj_qty_actual': float(row[8]),  # Inj Qty (Actual)
                    'inj_qty_req': float(row[10])
                }
            except ValueError:
                continue  # Skip rows with invalid data

            data.append(row_data)

    # Print header (includes InjQtyActual as 'InjAct')
    print(f"{'TIME':<6} {'EngSpd':<6} {'SpecInt':<8} {'ActInt':<8} {'InjAct':<8} {'InjReq':<8}  Notes")

    last_inj_qty_requested = None
    last_inj_qty_actual = None
    last_eng_speed = None
    acceleration_detected = False
    calculated_overboost = False
    calculated_underboost = False
    # Use numeric counters instead of booleans
    last_overboost_count = 0
    last_underboost_count = 0

    distributed_results = []

    # Process the data structure
    for row in data:
        time_val       = row['time']
        eng_speed      = row['eng_speed']
        spec_int       = row['spec_int']
        act_int        = row['act_int']
        inj_qty_actual = row['inj_qty_actual']
        inj_qty_req    = row['inj_qty_req']

        notes = []

        # 1) Check for acceleration start.
        # When the current injection quantity request exceeds the previous one,
        # mark that acceleration has begun.
        skip_eng_speed_check = False
        if last_inj_qty_requested is not None and not acceleration_detected:
            if inj_qty_req > last_inj_qty_requested:
                acceleration_detected = True
                skip_eng_speed_check = True
                print("--- Acceleration start detected ---")

        # Check for acceleration end by comparing engine speeds.
        if acceleration_detected and not skip_eng_speed_check:
            if eng_speed < last_eng_speed or inj_qty_actual == 0 or inj_qty_req == 0:
                acceleration_detected = False
                print("--- Acceleration end detected ---")

        if acceleration_detected:
            # 2) Check the difference between actual and spec intake pressures.
            diff = act_int - spec_int

            # Overboost detection (when diff is positive)
            if diff >= th2:
                if last_overboost_count == 0:
                    calculated_overboost = True
                    notes.append("TH2 <-")
                    notes.append("---- Calculating with actual fuel: " + str(inj_qty_actual))
                    notes.append("---- Weight: " + str(1 + weight(th2, th1 + th2, diff)))
                    distributed_results.append(distribute_value(eng_speed, inj_qty_actual, 1 + weight(th2, th1 + th2, diff), ROW_HEADERS, COL_HEADERS))
                elif last_overboost_count == 1 and calculated_overboost is False:
                    calculated_overboost = True
                    if last_inj_qty_actual is not None and last_eng_speed is not None:
                        notes.append("TH2 <-")
                        notes.append("---- Calculating with last fuel: " + str(last_inj_qty_actual) +
                                     " with last eng speed: " + str(last_eng_speed))
                        notes.append("---- Weight: " + str(1 + weight(th2, th1 + th2, diff)))
                        distributed_results.append(distribute_value(last_eng_speed, last_inj_qty_actual, 1 + weight(th2, th1 + th2, diff), ROW_HEADERS, COL_HEADERS))
                else:
                    notes.append("TH2")
                last_overboost_count += 1
                last_underboost_count = 0
                calculated_underboost = False
            elif diff >= th1:
                if last_overboost_count == 0:
                    notes.append("TH1 <-")
                    calculated_overboost = True
                    notes.append("---- Calculating with actual fuel: " + str(inj_qty_actual))
                    notes.append("---- Weight: " + str(weight(th1, th2, diff)))
                    distributed_results.append(distribute_value(eng_speed, inj_qty_actual, weight(th1, th2, diff), ROW_HEADERS, COL_HEADERS))
                elif last_overboost_count == 1 and calculated_overboost is False:
                    calculated_overboost = True
                    notes.append("TH1 <-")
                    if last_inj_qty_actual is not None and last_eng_speed is not None:
                        notes.append("---- Calculating with last fuel: " + str(last_inj_qty_actual) +
                                     " with last eng speed: " + str(last_eng_speed))
                        notes.append("---- Weight: " + str(weight(th1, th2, diff)))
                        distributed_results.append(distribute_value(last_eng_speed, last_inj_qty_actual, weight(th1, th2, diff), ROW_HEADERS, COL_HEADERS))
                else:
                    notes.append("TH1")
                last_overboost_count += 1
                last_underboost_count = 0
                calculated_underboost = False
            elif diff > 0:
                if last_overboost_count == 0:
                    last_overboost_count += 1
                    notes.append("<TH1 <-")
                elif last_overboost_count == 1 and calculated_overboost is False:
                    notes.append("<TH1 <-")
                    last_overboost_count = 1
                else:
                    notes.append("<TH1")
                    last_overboost_count += 1
                last_underboost_count = 0
                calculated_underboost = False

            # Underboost detection (when diff is negative)
            elif diff <= -th2:
                if last_underboost_count == 0:
                    calculated_underboost = True
                    notes.append("UnderTH2 <-")
                    notes.append("---- Calculating with actual fuel: " + str(inj_qty_actual))
                    w = weight(th2, th1 + th2, abs(diff))
                    notes.append("---- Weight: " + str(-1 - w))
                    distributed_results.append(distribute_value(eng_speed, inj_qty_actual, -1 - w, ROW_HEADERS, COL_HEADERS))
                elif last_underboost_count == 1 and calculated_underboost is False:
                    calculated_underboost = True
                    if last_inj_qty_actual is not None and last_eng_speed is not None:
                        notes.append("UnderTH2 <-")
                        notes.append("---- Calculating with last fuel: " + str(last_inj_qty_actual) +
                                     " with last eng speed: " + str(last_eng_speed))
                        w = weight(th2, th1 + th2, abs(diff))
                        notes.append("---- Weight: " + str(-1 - w))
                        distributed_results.append(distribute_value(last_eng_speed, last_inj_qty_actual, -1 - w, ROW_HEADERS, COL_HEADERS))
                else:
                    notes.append("UnderTH2")
                last_underboost_count += 1
                last_overboost_count = 0
                calculated_overboost = False
            elif diff <= -th1:
                if last_underboost_count == 0:
                    calculated_underboost = True
                    notes.append("UnderTH1 <-")
                    notes.append("---- Calculating with actual fuel: " + str(inj_qty_actual))
                    w = weight(th1, th2, abs(diff))
                    notes.append("---- Weight: " + str(-w))
                    distributed_results.append(distribute_value(eng_speed, inj_qty_actual, -w, ROW_HEADERS, COL_HEADERS))
                elif last_underboost_count == 1 and calculated_underboost is False:
                    calculated_underboost = True
                    if last_inj_qty_actual is not None and last_eng_speed is not None:
                        notes.append("UnderTH1 <-")
                        notes.append("---- Calculating with last fuel: " + str(last_inj_qty_actual) +
                                     " with last eng speed: " + str(last_eng_speed))
                        w = weight(th1, th2, abs(diff))
                        notes.append("---- Weight: " + str(-w))
                        distributed_results.append(distribute_value(last_eng_speed, last_inj_qty_actual, -w, ROW_HEADERS, COL_HEADERS))
                else:
                    notes.append("UnderTH1")
                last_underboost_count += 1
                last_overboost_count = 0
                calculated_overboost = False
            elif diff < 0:
                if last_underboost_count == 0:
                    last_underboost_count += 1
                    notes.append("<UnderTH1 <-")
                elif last_underboost_count == 1 and calculated_underboost is False:
                    notes.append("<UnderTH1 <-")
                    last_underboost_count = 1
                else:
                    notes.append("<UnderTH1")
                    last_underboost_count += 1
                last_overboost_count = 0
                calculated_overboost = False
            else:
                # No boost condition detected; reset both counters.
                last_overboost_count = 0
                last_underboost_count = 0
                calculated_overboost = False
                calculated_underboost = False

            # Print the formatted row with boost notes.
            print(
                f"{time_val:<6.2f} "
                f"{int(eng_speed):<6} "
                f"{spec_int:<8.1f} "
                f"{act_int:<8.1f} "
                f"{inj_qty_actual:<8.1f} "
                f"{inj_qty_req:<8.1f}  "
                + " ".join(notes)
            )
        else:
            # When not accelerating, reset boost counters.
            last_overboost_count = 0
            last_underboost_count = 0

        last_inj_qty_requested = inj_qty_req
        last_eng_speed = eng_speed
        last_inj_qty_actual = inj_qty_actual
    
    # Average all distributed results and print the averaged table.
    avg_result = average_distributed_results(distributed_results, ROW_HEADERS, COL_HEADERS)
    print("\n--- Averaged Distributed Table ---")
    print_distributed_table(avg_result, ROW_HEADERS, COL_HEADERS)

    print("--- Finished parsing CSV ---")
    return avg_result

def weight(lower, upper, value):
    """
    Returns the normalized weight for 'value' between lower and upper.
    If value is greater than or equal to upper, returns 1.
    If value is less than or equal to lower, returns 0.
    Otherwise returns (value - lower) / (upper - lower).
    """
    if value >= upper:
        return 1.0
    if value <= lower:
        return 0.0
    return (value - lower) / (upper - lower)

def distribute_value(input_row, input_col, value, row_headers, col_headers):
    """
    Distributes the given 'value' across the four nearest cells (via bilinear interpolation)
    defined by row_headers and col_headers.
    
    Parameters:
      input_row (float): the row value to match against row_headers.
      input_col (float): the column value to match against col_headers.
      value (float): the weight or value to distribute.
      row_headers (list of float): list of numeric row header values, assumed sorted in descending order.
      col_headers (list of str): list of column header strings (with comma as decimal separator).
    
    Returns:
      dict: Keys are tuples (row_header, col_header), and values are the distributed portions of 'value'.
    """
    # --- Process column headers: convert to floats for calculation ---
    col_values = []
    for s in col_headers:
        try:
            col_values.append(float(s.replace(',', '.')))
        except ValueError:
            raise ValueError(f"Column header '{s}' cannot be converted to a number.")

    # --- Determine interpolation factors for the rows ---
    row_interp = {}
    if input_row >= row_headers[0]:
        # Input is above the highest header; assign all weight to the highest header.
        row_interp[row_headers[0]] = 1.0
    elif input_row <= row_headers[-1]:
        # Input is below the lowest header; assign all weight to the lowest header.
        row_interp[row_headers[-1]] = 1.0
    else:
        # Find the two neighboring row headers such that:
        #   row_headers[i] >= input_row >= row_headers[i+1]
        for i in range(len(row_headers) - 1):
            R_hi = row_headers[i]
            R_lo = row_headers[i + 1]
            if R_hi >= input_row >= R_lo:
                if R_hi - R_lo == 0:
                    row_interp[R_hi] = 1.0
                else:
                    # Compute the linear fraction:
                    # Fraction for R_hi = (input_row - R_lo) / (R_hi - R_lo)
                    # Fraction for R_lo = 1 - fraction for R_hi
                    f = (input_row - R_lo) / (R_hi - R_lo)
                    row_interp[R_hi] = f
                    row_interp[R_lo] = 1 - f
                break

    # --- Determine interpolation factors for the columns ---
    col_interp = {}
    if input_col <= col_values[0]:
        col_interp[col_headers[0]] = 1.0
    elif input_col >= col_values[-1]:
        col_interp[col_headers[-1]] = 1.0
    else:
        # Find the two neighboring column headers such that:
        #   col_values[j] <= input_col <= col_values[j+1]
        for j in range(len(col_values) - 1):
            C_lo = col_values[j]
            C_hi = col_values[j + 1]
            if C_lo <= input_col <= C_hi:
                if C_hi - C_lo == 0:
                    col_interp[col_headers[j]] = 1.0
                else:
                    # For the lower column header, weight is (C_hi - input_col)/(C_hi - C_lo)
                    # For the upper column header, weight is (input_col - C_lo)/(C_hi - C_lo)
                    w_lower = (C_hi - input_col) / (C_hi - C_lo)
                    w_upper = (input_col - C_lo) / (C_hi - C_lo)
                    col_interp[col_headers[j]] = w_lower
                    col_interp[col_headers[j + 1]] = w_upper
                break

    # --- Combine the row and column interpolation factors (bilinear interpolation) ---
    distributed = {}
    for r_key, r_weight in row_interp.items():
        for c_key, c_weight in col_interp.items():
            # The distributed value in a cell is the product of the row and column fractions times the input value.
            distributed[(r_key, c_key)] = value * r_weight * c_weight

    return distributed

def average_distributed_results(distributed_results, row_headers, col_headers):
    """
    Averages the distributed values across all dictionaries in distributed_results.
    
    For each cell (row_header, col_header) defined by the provided row and column headers,
    this function calculates the average value using only non-zero values from the distributed
    results. If all values for a cell are 0, the averaged result will be 0.
    
    Parameters:
      distributed_results (list): List of dictionaries (from distribute_value) to average.
      row_headers (list): List of row header values.
      col_headers (list): List of column header strings.
    
    Returns:
      dict: A dictionary with keys (row_header, col_header) and the averaged non-zero values.
    """
    avg_distributed = {}
    
    for row in row_headers:
        for col in col_headers:
            # Collect only non-zero values for the current cell.
            non_zero_values = [result.get((row, col), 0) for result in distributed_results
                                 if result.get((row, col), 0) != 0]
            if non_zero_values:
                avg_distributed[(row, col)] = sum(non_zero_values) / len(non_zero_values)
            else:
                avg_distributed[(row, col)] = 0
    return avg_distributed

def print_distributed_table(distributed, row_headers, col_headers):
    """
    Prints a complete table of the distributed values. The table has row_headers as rows
    and col_headers as columns. If a cell did not receive a distributed value, a 0.0 is printed.
    
    Parameters:
      distributed (dict): Dictionary with keys (row_header, col_header) and their associated value.
      row_headers (list): List of row header values (numeric).
      col_headers (list): List of column header values (strings).
    """
    # Print column headers.
    header_line = "Row\\Col".ljust(10)  # Label for the row header column.
    for col in col_headers:
        header_line += f"{col:>10}"
    print(header_line)
    
    # Print each row.
    for row in row_headers:
        row_line = f"{row:<10}"  # Row header printed left-aligned.
        for col in col_headers:
            # Get the distributed value, or default to 0.
            cell_val = distributed.get((row, col), 0)
            row_line += f"{cell_val:>10.2f}"
        print(row_line)