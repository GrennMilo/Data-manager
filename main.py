import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

# --- Configuration ---
LV_TEMP_COL = 'T Heater 1' # Use 10th column for temperature
LV_PRESSURE_COL = 'Pressure setpoint' # Use 14th column for pressure
LV_H2_FLOW_COL = 'H2 Actual Flow' # 5th Column
LV_N2_FLOW_COL = 'N2 Actual Flow' # 8th Column
LV_N2_POISON_SP_COL = 'N2 poisoning set-point' # 15th Column
GC_NH3_COL = 'NH3' # GC NH3 column
MERGE_TOLERANCE = pd.Timedelta('5 minutes') # Tolerance for matching LV and GC timestamps

# --- Utility Functions ---
def create_reports_folder(base_folder="reports"):
    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
    return base_folder

def get_unique_filename_prefix():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# --- File Processing Functions ---
def process_lv_file(filename):
    # Read the LV file, skipping the first 2 metadata lines.
    # The 3rd line is the header, 4th is units.
    # Use tab as separator, specify python engine to avoid warning
    df = pd.read_csv(filename, sep='\\t', skiprows=2, engine='python', header=None)
    
    # Assign header from the first row of the read data (original line 3)
    df.columns = df.iloc[0]
    # Drop the now redundant header row and the units row (original lines 3 and 4)
    df = df.iloc[2:].reset_index(drop=True)
    
    # Strip any extra whitespace from column names 
    df.columns = df.columns.str.strip()
    
    # Convert the 'DateTime' column (using 2-digit year format) and rename it to 'Date'
    df['Date'] = pd.to_datetime(df['DateTime'], format='%d/%m/%y %H:%M:%S', dayfirst=True, errors='coerce')
    # Drop the original 'DateTime' column
    if 'DateTime' in df.columns:
        df = df.drop(columns=['DateTime'])
    # Remove rows where Date could not be parsed
    df.dropna(subset=['Date'], inplace=True)

    # Define essential numeric columns including the CORRECTED temp/pressure AND newly added flows
    numeric_cols_lv = ['RelativeTime', LV_H2_FLOW_COL, LV_N2_FLOW_COL, LV_TEMP_COL, LV_PRESSURE_COL, LV_N2_POISON_SP_COL]
    # Add any other critical LV columns needed for analysis/plotting

    # Corrected loop for numeric conversion
    # Iterate over a static list of column names
    for col_name in df.columns.tolist():
        # Attempt numeric conversion ONLY for essential columns 
        if col_name in numeric_cols_lv:
             try:
                 # Apply conversion to the column using its name
                 df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
             except ValueError:
                 print(f"Warning: Could not convert column '{col_name}' in LV file to numeric. Skipping.")

    # Drop rows ONLY if essential numeric columns (needed for plotting/stages) are NaN
    df.dropna(subset=numeric_cols_lv, how='any', inplace=True)

    # Stage Detection (ensure sorting first)
    df = df.sort_values(by='Date').reset_index(drop=True)
    df['Stage'] = 0
    if not df.empty:
        current_stage = 1
        df.loc[0, 'Stage'] = current_stage
        for i in range(1, len(df)):
            # Check if RelativeTime exists and is valid before comparison
            if 'RelativeTime' in df.columns and pd.notna(df.loc[i, 'RelativeTime']) and pd.notna(df.loc[i-1, 'RelativeTime']):
                if df.loc[i, 'RelativeTime'] < df.loc[i-1, 'RelativeTime']:
                    current_stage += 1
            # Always assign the current stage, even if RelativeTime was invalid for comparison
            df.loc[i, 'Stage'] = current_stage
    else:
        print("Warning: LV DataFrame empty before stage detection.")

    return df


def process_gc_file(filename):
    # Read the GC file with the header from the first line
    # Use tab as separator, specify python engine to avoid warning
    df = pd.read_csv(filename, sep='\\t', engine='python')
    df.columns = df.columns.str.strip()
    # Convert the 'Date' column to datetime using format dd.mm.yyyy HH:MM:SS
    df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y %H:%M:%S', errors='coerce') 
    # Remove rows where Date could not be parsed
    df.dropna(subset=['Date'], inplace=True)

    numeric_cols_gc = ['Area', 'H2', 'Area           _2', 'N2', 'Area           _4', 'NH3'] # Add other relevant GC numeric cols
    for col in df.columns:
        if col in numeric_cols_gc:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except ValueError:
                 print(f"Warning: Could not convert column '{col}' in GC file to numeric. Skipping.")
        # else: # Optional conversion for other columns
        #    df[col] = pd.to_numeric(df[col], errors='ignore') 

    # Optional: drop rows if key GC data like NH3 is missing
    # df.dropna(subset=['NH3'], inplace=True)
    return df


def merge_step_data(df_lv_step, df_gc):
    if df_lv_step.empty or df_gc.empty:
        return pd.DataFrame()

    df_lv_step = df_lv_step.sort_values('Date')
    df_gc_sorted = df_gc.sort_values('Date') # Sort GC data once if reused

    merged_step_df = pd.merge_asof(df_lv_step, df_gc_sorted, on='Date',
                                   direction='nearest',
                                   tolerance=MERGE_TOLERANCE,
                                   suffixes=['_LV', '_GC'])
    return merged_step_df


def merge_overall_data(df_lv, df_gc):
    if df_lv.empty or df_gc.empty:
        print("Warning: Cannot perform overall merge, one or both DataFrames are empty.")
        # Return whichever is not empty, or an empty DF if both are
        return df_lv if not df_lv.empty else df_gc 
        
    df_lv_sorted = df_lv.sort_values('Date')
    df_gc_sorted = df_gc.sort_values('Date')
    
    # Perform an asof merge on the full datasets
    merged_overall_df = pd.merge_asof(df_lv_sorted, df_gc_sorted, on='Date',
                                      direction='nearest',
                                      tolerance=MERGE_TOLERANCE, 
                                      suffixes=['_LV', '_GC'])
    # Alternative: Outer merge to keep all rows from both
    # merged_overall_df = pd.merge(df_lv_sorted, df_gc_sorted, on='Date', how='outer', suffixes=['_LV', '_GC'])
    # merged_overall_df = merged_overall_df.sort_values('Date')
    
    print(f"Overall merged data shape: {merged_overall_df.shape}")
    return merged_overall_df


def plot_overall_merged_data(merged_df, folder, prefix):
    if merged_df.empty:
        print("Overall merged data is empty. Skipping overall plot and CSV save.")
        return

    # Save overall merged data to CSV in the main timestamped folder
    overall_csv_filename = os.path.join(folder, f"{prefix}_overall_merged_data.csv")
    try:
        merged_df.to_csv(overall_csv_filename, index=False)
        print(f"Saved overall merged data to: {overall_csv_filename}")
    except Exception as e:
        print(f"Error saving overall merged data to CSV: {e}")

    # --- Plotting --- 
    fig, axs = plt.subplots(3, 1, figsize=(15, 18), sharex=True)
    fig.suptitle('Overall Merged Data Analysis', fontsize=16)

    # Define column names, handling potential suffixes
    # Check if columns exist in the merged_df before trying to use them
    temp_col_lv = f"{LV_TEMP_COL}_LV" if f"{LV_TEMP_COL}_LV" in merged_df.columns else LV_TEMP_COL
    nh3_col_gc = f"{GC_NH3_COL}_GC" if f"{GC_NH3_COL}_GC" in merged_df.columns else GC_NH3_COL
    h2_flow_col = f"{LV_H2_FLOW_COL}_LV" if f"{LV_H2_FLOW_COL}_LV" in merged_df.columns else LV_H2_FLOW_COL
    n2_flow_col = f"{LV_N2_FLOW_COL}_LV" if f"{LV_N2_FLOW_COL}_LV" in merged_df.columns else LV_N2_FLOW_COL
    n2_poison_sp_col = f"{LV_N2_POISON_SP_COL}_LV" if f"{LV_N2_POISON_SP_COL}_LV" in merged_df.columns else LV_N2_POISON_SP_COL
    pressure_col = f"{LV_PRESSURE_COL}_LV" if f"{LV_PRESSURE_COL}_LV" in merged_df.columns else LV_PRESSURE_COL

    # Panel 1: LV Temp vs GC NH3
    ax1 = axs[0]
    ax1_twin = ax1.twinx()
    color_temp = 'tab:red'
    color_nh3 = 'tab:green'
    ax1.set_ylabel(f'LV Temp ({LV_TEMP_COL}) (C)', color=color_temp)
    ax1_twin.set_ylabel(f'GC NH3 ({GC_NH3_COL}) (%)', color=color_nh3)
    
    plot_temp = False
    if temp_col_lv in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[temp_col_lv]):
        ax1.plot(merged_df['Date'], merged_df[temp_col_lv], label=f'LV Temp ({temp_col_lv})', color=color_temp, marker='.', linestyle='-')
        plot_temp = True
    ax1.tick_params(axis='y', labelcolor=color_temp)
    ax1.grid(True)
    
    plot_nh3 = False
    if nh3_col_gc in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[nh3_col_gc]):
        ax1_twin.plot(merged_df['Date'], merged_df[nh3_col_gc], label=f'GC NH3 ({nh3_col_gc})', color=color_nh3, marker='o', linestyle=':')
        plot_nh3 = True
    ax1_twin.tick_params(axis='y', labelcolor=color_nh3)
    
    ax1.set_title('LV Temperature vs GC NH3')
    # Combine legends for Panel 1
    lines, labels = ax1.get_legend_handles_labels() if plot_temp else ([], [])
    lines2, labels2 = ax1_twin.get_legend_handles_labels() if plot_nh3 else ([], [])
    ax1_twin.legend(lines + lines2, labels + labels2, loc='upper left')

    # Panel 2: LV Flows
    ax2 = axs[1]
    plot_h2 = False
    if h2_flow_col in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[h2_flow_col]):
        ax2.plot(merged_df['Date'], merged_df[h2_flow_col], label=f'LV H2 Flow ({h2_flow_col})', marker='.', linestyle='-')
        plot_h2 = True
    plot_n2 = False
    if n2_flow_col in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[n2_flow_col]):
        ax2.plot(merged_df['Date'], merged_df[n2_flow_col], label=f'LV N2 Flow ({n2_flow_col})', marker='.', linestyle='--')
        plot_n2 = True
    plot_n2_poison = False
    if n2_poison_sp_col in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[n2_poison_sp_col]):
        ax2.plot(merged_df['Date'], merged_df[n2_poison_sp_col], label=f'LV N2 Poison SP ({n2_poison_sp_col})', marker='x', linestyle=':')
        plot_n2_poison = True
        
    ax2.set_ylabel('Flow / Setpoint (ml/min)')
    if plot_h2 or plot_n2 or plot_n2_poison:
        ax2.legend(loc='upper left')
    ax2.grid(True)
    ax2.set_title('LV Flows & Setpoints')

    # Panel 3: LV Pressure
    ax3 = axs[2]
    plot_pressure = False
    if pressure_col in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[pressure_col]):
        ax3.plot(merged_df['Date'], merged_df[pressure_col], label=f'LV Pressure ({pressure_col})', marker='.', linestyle='-', color='purple')
        plot_pressure = True
        
    ax3.set_ylabel('Pressure (bar)')
    if plot_pressure:
        ax3.legend(loc='upper left')
    ax3.grid(True)
    ax3.set_title('LV Pressure Setpoint')
    ax3.set_xlabel('Date') # Only set xlabel on the bottom plot
    
    # Common formatting
    plt.xticks(rotation=45)
    fig.tight_layout(rect=[0, 0.03, 1, 0.95]) # Adjust layout for suptitle
    plot_filename = os.path.join(folder, f"{prefix}_overall_analysis.png")
    plt.savefig(plot_filename)
    plt.close(fig)
    print(f"Saved overall analysis plot to: {plot_filename}")


def plot_per_step_data(step_df, step_number, step_folder_path, prefix):
    if step_df.empty:
        print(f"No data to plot for step {step_number}.")
        return
        
    # Ensure the step-specific folder exists
    os.makedirs(step_folder_path, exist_ok=True)

    # Save step-specific merged data to CSV
    step_csv_filename = os.path.join(step_folder_path, f"step_{step_number}_data.csv") # Use consistent simple name
    try:
        step_df.to_csv(step_csv_filename, index=False)
        print(f"Saved step {step_number} data to CSV: {step_csv_filename}")
    except Exception as e:
        print(f"Error saving step {step_number} data to CSV: {e}")

    # Save step-specific merged data to JSON
    step_json_filename = os.path.join(step_folder_path, f"step_{step_number}_data.json")
    try:
        # Convert Timestamp columns to string to ensure JSON serializability if they are not already
        # Making a copy to avoid modifying the original DataFrame if it's used later
        df_for_json = step_df.copy()
        for col in df_for_json.select_dtypes(include=['datetime64[ns]']).columns:
            df_for_json[col] = df_for_json[col].astype(str) # Convert datetime to string
        df_for_json.to_json(step_json_filename, orient='records', indent=4, lines=False)
        print(f"Saved step {step_number} data to JSON: {step_json_filename}")
    except Exception as e:
        print(f"Error saving step {step_number} data to JSON: {e}")

    # --- Plotting --- 
    fig, axs = plt.subplots(3, 1, figsize=(15, 18), sharex=True)
    fig.suptitle(f'Step {step_number} Analysis', fontsize=16)

    # Define column names, checking for suffixes
    temp_col_lv = f"{LV_TEMP_COL}_LV" if f"{LV_TEMP_COL}_LV" in step_df.columns else LV_TEMP_COL
    pressure_col_lv = f"{LV_PRESSURE_COL}_LV" if f"{LV_PRESSURE_COL}_LV" in step_df.columns else LV_PRESSURE_COL
    nh3_col_gc = f"{GC_NH3_COL}_GC" if f"{GC_NH3_COL}_GC" in step_df.columns else GC_NH3_COL
    n2_flow_col_lv = f"{LV_N2_FLOW_COL}_LV" if f"{LV_N2_FLOW_COL}_LV" in step_df.columns else LV_N2_FLOW_COL
    h2_flow_col_lv = f"{LV_H2_FLOW_COL}_LV" if f"{LV_H2_FLOW_COL}_LV" in step_df.columns else LV_H2_FLOW_COL

    # Subplot 1: LV Temp (Corrected) and LV Pressure (Corrected)
    ax0_twin = axs[0].twinx()
    plot_temp = False
    if temp_col_lv in step_df.columns and pd.api.types.is_numeric_dtype(step_df[temp_col_lv]):
        axs[0].plot(step_df['Date'], step_df[temp_col_lv], label=f'LV Temp ({temp_col_lv})', color='red', marker='.')
        plot_temp = True
    axs[0].set_ylabel(f'Temp ({LV_TEMP_COL}) (C)', color='red')
    axs[0].tick_params(axis='y', labelcolor='red')
    
    plot_pressure = False
    if pressure_col_lv in step_df.columns and pd.api.types.is_numeric_dtype(step_df[pressure_col_lv]):
        ax0_twin.plot(step_df['Date'], step_df[pressure_col_lv], label=f'LV Pressure ({pressure_col_lv})', color='blue', linestyle='--')
        plot_pressure = True
    ax0_twin.set_ylabel(f'Pressure ({LV_PRESSURE_COL}) (bar)', color='blue')
    ax0_twin.tick_params(axis='y', labelcolor='blue')
    axs[0].set_title('LV Temperature & Pressure')
    # Combine legends
    lines, labels = axs[0].get_legend_handles_labels() if plot_temp else ([],[])
    lines2, labels2 = ax0_twin.get_legend_handles_labels() if plot_pressure else ([],[])
    ax0_twin.legend(lines + lines2, labels + labels2, loc='upper left')

    # Subplot 2: LV Flows (N2, H2)
    plot_n2_flow = False
    if n2_flow_col_lv in step_df.columns and pd.api.types.is_numeric_dtype(step_df[n2_flow_col_lv]):
        axs[1].plot(step_df['Date'], step_df[n2_flow_col_lv], label=f'LV N2 Flow ({n2_flow_col_lv})', marker='.')
        plot_n2_flow = True
    plot_h2_flow = False
    if h2_flow_col_lv in step_df.columns and pd.api.types.is_numeric_dtype(step_df[h2_flow_col_lv]):
        axs[1].plot(step_df['Date'], step_df[h2_flow_col_lv], label=f'LV H2 Flow ({h2_flow_col_lv})', marker='.')
        plot_h2_flow = True
    axs[1].set_ylabel('Flow (ml/min)')
    if plot_n2_flow or plot_h2_flow:
      axs[1].legend(loc='upper left')
    axs[1].set_title('LV Gas Flows')

    # Subplot 3: GC % NH3
    plot_nh3 = False
    if nh3_col_gc in step_df.columns and pd.api.types.is_numeric_dtype(step_df[nh3_col_gc]):
        axs[2].plot(step_df['Date'], step_df[nh3_col_gc], label=f'GC NH3 ({nh3_col_gc})', color='green', marker='o')
        plot_nh3 = True
    axs[2].set_ylabel('NH3 (%)', color='green')
    axs[2].tick_params(axis='y', labelcolor='green')
    if plot_nh3:
      axs[2].legend(loc='upper left')
    axs[2].set_title('GC NH3 Concentration')

    # Common formatting
    for ax in axs:
        ax.grid(True)
        ax.tick_params(axis='x', rotation=45)
    axs[2].set_xlabel('Date')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plot_filename = os.path.join(step_folder_path, f"step_{step_number}_analysis.png") # Use consistent simple name
    plt.savefig(plot_filename)
    plt.close(fig) # Close the figure to free memory
    print(f"Saved step {step_number} plot to: {plot_filename}")


if __name__ == '__main__':
    # Create the main timestamped folder first
    timestamp_prefix = get_unique_filename_prefix()
    base_reports_folder = "reports" 
    main_output_folder = os.path.join(base_reports_folder, timestamp_prefix)
    os.makedirs(main_output_folder, exist_ok=True)
    print(f"Created main output folder: {main_output_folder}")

    lv_file_path = 'LVOriginalFile - 2025-05-02T101602.806.txt'
    gc_file_path = 'GCOriginalFile - 2025-05-02T101602.806.txt'

    print(f"Processing LV file: {lv_file_path}")
    df_lv_full = process_lv_file(lv_file_path)
    if df_lv_full.empty:
        print("LV DataFrame is empty after processing. Exiting.")
        exit()
    # Check if essential columns exist after processing
    required_lv_cols = [LV_TEMP_COL, LV_PRESSURE_COL, LV_H2_FLOW_COL, LV_N2_FLOW_COL, LV_N2_POISON_SP_COL, 'RelativeTime', 'Date']
    missing_lv_cols = [col for col in required_lv_cols if col not in df_lv_full.columns]
    if missing_lv_cols:
        print(f"Error: Required LV columns missing after processing: {missing_lv_cols}")
        exit()
    if 'Stage' not in df_lv_full.columns or df_lv_full['Stage'].empty or df_lv_full['Stage'].max() == 0:
        print("Warning: Stage detection failed or resulted in 0 stages.")
        num_stages = 0
    else: 
        num_stages = df_lv_full['Stage'].max()
        print(f"LV Data Time Range: {df_lv_full['Date'].min()} to {df_lv_full['Date'].max()}")
        print(f"Detected {num_stages} stages in LV data.")

    print(f"\nProcessing GC file: {gc_file_path}")
    df_gc_full = process_gc_file(gc_file_path)
    if df_gc_full.empty:
        print("GC DataFrame is empty after processing.")

    # --- Perform Overall Merge --- 
    print("\nPerforming overall data merge...")
    df_merged_overall = merge_overall_data(df_lv_full, df_gc_full)

    # --- Plot Overall Data (Merged) --- 
    # Pass the main timestamped output folder
    plot_overall_merged_data(df_merged_overall, main_output_folder, timestamp_prefix)

    # --- Process and Plot Per Step --- 
    if not df_gc_full.empty and num_stages > 0:
        print("\nProcessing and plotting per stage...")
        for step_num in range(1, num_stages + 1):
            print(f"\n--- Processing Step {step_num} ---")
            df_lv_step = df_lv_full[df_lv_full['Stage'] == step_num].copy()
            
            if df_lv_step.empty:
                print(f"No LV data for step {step_num}.")
                continue

            # Define step-specific folder INSIDE the main timestamped folder
            step_folder_path = os.path.join(main_output_folder, f"step_{step_num}")
            
            # Merge this step's LV data with the full GC data
            merged_step_df = merge_step_data(df_lv_step, df_gc_full)

            if not merged_step_df.empty:
                print(f"Merged data for Step {step_num} - Shape: {merged_step_df.shape}")
                # Plot and save data/plot to the specific step folder (pass step_folder_path)
                # Use the base timestamp prefix for consistency in filenames within step folders
                plot_per_step_data(merged_step_df, step_num, step_folder_path, timestamp_prefix) 
            else:
                print(f"No data merged for Step {step_num} using tolerance {MERGE_TOLERANCE}. Plot/CSV for this step will be skipped.")
    elif df_gc_full.empty:
        print("\nGC data is empty, skipping per-step merged analysis plots and CSVs.")
    elif num_stages == 0:
        print("\nNo stages detected in LV data, skipping per-step analysis.")

    print("\nScript finished.") 