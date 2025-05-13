import pandas as pd
# No longer need matplotlib directly here, but need plotly
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio # To write JSON
import os
from datetime import datetime
import json # For saving plot json
import plotly.utils # For PlotlyJSONEncoder
import plotly.colors # For comparison plot colors

# Define consistent layout settings for dark theme
dark_theme_layout_updates = dict(
    font_family="Inter",
    font_color="#e1e3e8", # --text-primary
    paper_bgcolor='rgba(0,0,0,0)', # Transparent background
    plot_bgcolor='rgba(0,0,0,0)',  # Transparent plot area
    height=650, # Increased plot height
    xaxis=dict(
        gridcolor='rgba(0,0,0,0)', # --border-color REMOVED GRID
        linecolor='#495057',
        zerolinecolor='#495057',
        title_font_color="#adb5bd", # --text-secondary
        tickfont_color="#adb5bd"
    ),
    yaxis=dict( # Default y-axis
        gridcolor='rgba(0,0,0,0)', # REMOVED GRID
        linecolor='#495057',
        zerolinecolor='#495057',
        title_font_color="#adb5bd",
        tickfont_color="#adb5bd"
    ),
    # Apply similar styling to other potential y-axes (yaxis2, yaxis3, yaxis4)
    # Note: These need to be applied specifically where multiple axes exist
    yaxis2=dict(
        gridcolor='rgba(0,0,0,0)', # REMOVED GRID
        linecolor='#495057',
        zerolinecolor='#495057',
        title_font_color="#adb5bd",
        tickfont_color="#adb5bd"
    ),
    yaxis3=dict(
        gridcolor='rgba(0,0,0,0)', # REMOVED GRID
        linecolor='#495057',
        zerolinecolor='#495057',
        title_font_color="#adb5bd",
        tickfont_color="#adb5bd"
    ),
    yaxis4=dict(
        gridcolor='rgba(0,0,0,0)', # REMOVED GRID
        linecolor='#495057',
        zerolinecolor='#495057',
        title_font_color="#adb5bd",
        tickfont_color="#adb5bd"
    ),
    legend=dict(
        orientation="h", # Horizontal legend
        yanchor="bottom",
        y=1.05, # Adjusted y slightly for more space if title is long
        xanchor="right",
        x=1,
        bgcolor='rgba(0,0,0,0)', # Transparent legend background
        bordercolor='#495057'
    ),
    hovermode='x unified', # Improved hover experience
    hoverlabel=dict(
        bgcolor="#272c36", # --bg-dark-secondary
        font_size=12,
        font_family="Inter",
        font_color="#e1e3e8" # --text-primary
    ),
    margin=dict(l=60, r=40, t=50, b=40) # Adjust margins slightly
)

# --- Configuration (can be overridden by Flask app if needed) ---
LV_TEMP_COL = 'T Heater 1'
LV_PRESSURE_COL = 'Pressure setpoint'
LV_H2_FLOW_COL = 'H2 Actual Flow'
LV_N2_FLOW_COL = 'N2 Actual Flow'
LV_N2_POISON_SP_COL = 'N2 poisoning set-point'
GC_NH3_COL = 'NH3'
MERGE_TOLERANCE = pd.Timedelta('5 minutes')

# --- File Processing Functions (mostly same as your main.py) ---
def process_lv_file(filename):
    df = pd.read_csv(filename, sep='\t', skiprows=2, engine='python', header=None)
    df.columns = df.iloc[0]
    df = df.iloc[2:].reset_index(drop=True)
    df.columns = df.columns.str.strip()

    df['Date'] = pd.to_datetime(df['DateTime'], format='%d/%m/%y %H:%M:%S', errors='coerce')
    if 'DateTime' in df.columns:
        df = df.drop(columns=['DateTime'])
    df.dropna(subset=['Date'], inplace=True)

    numeric_cols_lv = ['RelativeTime', LV_H2_FLOW_COL, LV_N2_FLOW_COL, LV_TEMP_COL, LV_PRESSURE_COL, LV_N2_POISON_SP_COL]
    
    for col_name in df.columns.tolist():
        if col_name in numeric_cols_lv:
            try:
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
            except ValueError:
                print(f"Warning: Could not convert LV column '{col_name}' to numeric.")
    
    df.dropna(subset=numeric_cols_lv, how='any', inplace=True)
    
    df = df.sort_values(by='Date').reset_index(drop=True)
    df['Stage'] = 0
    if not df.empty:
        current_stage = 1
        df.loc[0, 'Stage'] = current_stage
        for i in range(1, len(df)):
            if 'RelativeTime' in df.columns and pd.notna(df.loc[i, 'RelativeTime']) and pd.notna(df.loc[i-1, 'RelativeTime']):
                if df.loc[i, 'RelativeTime'] < df.loc[i-1, 'RelativeTime']:
                    current_stage += 1
            df.loc[i, 'Stage'] = current_stage
    return df

def process_gc_file(filename):
    df = pd.read_csv(filename, sep='\t', engine='python')
    df.columns = df.columns.str.strip()
    df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y %H:%M:%S', errors='coerce')
    df.dropna(subset=['Date'], inplace=True)
    numeric_cols_gc = ['Area', 'H2', 'Area           _2', 'N2', 'Area           _4', GC_NH3_COL]
    for col_name in df.columns.tolist():
        if col_name in numeric_cols_gc:
            try:
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
            except ValueError:
                 print(f"Warning: Could not convert GC column '{col_name}' to numeric.")
    return df

def merge_step_data(df_lv_step, df_gc):
    if df_lv_step.empty or df_gc.empty:
        return pd.DataFrame()
    df_lv_step = df_lv_step.sort_values('Date')
    df_gc_sorted = df_gc.sort_values('Date')
    merged_step_df = pd.merge_asof(df_lv_step, df_gc_sorted, on='Date',
                                   direction='nearest',
                                   tolerance=MERGE_TOLERANCE,
                                   suffixes=['_LV', '_GC'])
    return merged_step_df

def merge_overall_data(df_lv, df_gc):
    if df_lv.empty:
        print("Warning: LV DataFrame is empty for overall merge.")
        return df_gc.copy() if not df_gc.empty else pd.DataFrame()
    if df_gc.empty:
        print("Warning: GC DataFrame is empty for overall merge.")
        return df_lv.copy()

    df_lv_sorted = df_lv.sort_values('Date')
    df_gc_sorted = df_gc.sort_values('Date')
    merged_overall_df = pd.merge_asof(df_lv_sorted, df_gc_sorted, on='Date',
                                      direction='nearest',
                                      tolerance=MERGE_TOLERANCE, 
                                      suffixes=['_LV', '_GC'])
    print(f"Overall merged data shape: {merged_overall_df.shape}")
    return merged_overall_df

# --- Plotting Functions (Rewritten for Plotly, saving JSON) ---
def plot_overall_merged_data(merged_df, output_folder_path):
    if merged_df.empty:
        print("Overall merged data is empty. Skipping overall plot and CSV save.")
        return None, None # plot_json_path, csv_path

    os.makedirs(output_folder_path, exist_ok=True)
    overall_csv_filename = os.path.join(output_folder_path, "overall_merged_data.csv")
    plot_json_filename = os.path.join(output_folder_path, "overall_plot.json") # Save as JSON
    
    try:
        merged_df.to_csv(overall_csv_filename, index=False)
        print(f"Saved overall merged data to: {overall_csv_filename}")
    except Exception as e:
        print(f"Error saving overall merged data to CSV: {e}")
        overall_csv_filename = None

    # --- Create figure with multiple Y axes ---
    # Instead of make_subplots, we create a regular figure
    # and define layout for multiple y-axes
    fig = go.Figure()

    # Column name handling (check for suffixes)
    temp_col = f"{LV_TEMP_COL}_LV" if f"{LV_TEMP_COL}_LV" in merged_df.columns else LV_TEMP_COL
    nh3_col = f"{GC_NH3_COL}_GC" if f"{GC_NH3_COL}_GC" in merged_df.columns else GC_NH3_COL
    h2_flow_col = f"{LV_H2_FLOW_COL}_LV" if f"{LV_H2_FLOW_COL}_LV" in merged_df.columns else LV_H2_FLOW_COL
    n2_flow_col = f"{LV_N2_FLOW_COL}_LV" if f"{LV_N2_FLOW_COL}_LV" in merged_df.columns else LV_N2_FLOW_COL
    n2_poison_col = f"{LV_N2_POISON_SP_COL}_LV" if f"{LV_N2_POISON_SP_COL}_LV" in merged_df.columns else LV_N2_POISON_SP_COL
    pressure_col = f"{LV_PRESSURE_COL}_LV" if f"{LV_PRESSURE_COL}_LV" in merged_df.columns else LV_PRESSURE_COL
    date_col = 'Date' # Assuming 'Date' is the common column after merge

    # --- Add Traces, assigning to different Y axes ---
    # Y Axis 1 (Left): Temperature
    if temp_col in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[temp_col]):
        fig.add_trace(go.Scatter(x=merged_df[date_col], y=merged_df[temp_col], name=f'LV Temp ({temp_col})', 
                                 mode='lines+markers', marker=dict(color='red'), yaxis='y1'))

    # Y Axis 2 (Right): NH3
    if nh3_col in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[nh3_col]):
        fig.add_trace(go.Scatter(x=merged_df[date_col], y=merged_df[nh3_col], name=f'GC NH3 ({nh3_col})', 
                                 mode='lines+markers', line=dict(dash='dot', color='lime'), yaxis='y2'))

    # Y Axis 3 (Right, shifted): Flows & Setpoints
    if h2_flow_col in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[h2_flow_col]):
        fig.add_trace(go.Scatter(x=merged_df[date_col], y=merged_df[h2_flow_col], name=f'LV H2 Flow ({h2_flow_col})', 
                                 mode='lines+markers', marker=dict(color='orange'), yaxis='y3'))
    if n2_flow_col in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[n2_flow_col]):
        fig.add_trace(go.Scatter(x=merged_df[date_col], y=merged_df[n2_flow_col], name=f'LV N2 Flow ({n2_flow_col})', 
                                 mode='lines+markers', line=dict(dash='dash', color='purple'), yaxis='y3'))
    if n2_poison_col in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[n2_poison_col]):
        fig.add_trace(go.Scatter(x=merged_df[date_col], y=merged_df[n2_poison_col], name=f'LV N2 Poison SP ({n2_poison_col})', 
                                 mode='lines+markers', line=dict(dash='dot', color='magenta'), yaxis='y3'))

    # Y Axis 4 (Left, shifted): Pressure
    if pressure_col in merged_df.columns and pd.api.types.is_numeric_dtype(merged_df[pressure_col]):
        fig.add_trace(go.Scatter(x=merged_df[date_col], y=merged_df[pressure_col], name=f'LV Pressure ({pressure_col})', 
                                 mode='lines+markers', marker=dict(color='cyan'), yaxis='y4'))

    # --- Update Layout with Multiple Axes, Dark Theme --- 
    fig.update_layout(
        title_text='Overall Merged Data Analysis', 
        height=600, # Adjust height as needed for single plot area
        hovermode='x unified',
        xaxis=dict(domain=[0.1, 0.9]), # Domain adjusted to make space for multiple Y axes
        yaxis=dict(
            title=f"Temp ({temp_col}) (C)", 
            titlefont=dict(color='red'), 
            tickfont=dict(color='red'),
            side='left',
        ),
        yaxis2=dict(
            title=f"NH3 ({nh3_col}) (%)", 
            titlefont=dict(color='lime'), 
            tickfont=dict(color='lime'),
            anchor='x', 
            overlaying='y', 
            side='right'
        ),
        yaxis3=dict(
            title="Flow / SP (ml/min)", 
            titlefont=dict(color='orange'), 
            tickfont=dict(color='orange'),
            anchor='free', 
            overlaying='y', 
            side='right', 
            position=0.95 # Position slightly inwards from yaxis2
        ),
         yaxis4=dict(
            title="Pressure (bar)", 
            titlefont=dict(color='cyan'), 
            tickfont=dict(color='cyan'),
            anchor='free', 
            overlaying='y', 
            side='left',
            position=0.05 # Position slightly inwards from yaxis1
        ),
        paper_bgcolor='#2c2c2c', # Match body background
        plot_bgcolor='#383838',  # Match results background
        font=dict(color='#e0e0e0'), # Light font for title, general text
        legend=dict(
            bgcolor='#383838', 
            bordercolor='#4a4a4a',
            orientation='h', # Horizontal legend
            yanchor='bottom',
            y=1.02, # Position legend above plot
            xanchor='right',
            x=1
        )
    )
    # Update axis styles (gridlines)
    axis_style = dict(
        gridcolor='rgba(0,0,0,0)', # REMOVED GRID
        linecolor='#5a5a5a',
        zerolinecolor='#5a5a5a'
    )
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style) # Apply to all y-axes implicitly

    # --- Save Plotly JSON ---
    try:
        pio.write_json(fig, plot_json_filename)
        print(f"Saved overall Plotly plot to: {plot_json_filename}")
    except Exception as e:
        print(f"Error saving overall Plotly plot JSON: {e}")
        plot_json_filename = None

    return plot_json_filename, overall_csv_filename

def plot_per_step_data(step_df, step_number, step_output_folder_path):
    if step_df.empty:
        print(f"No data to plot for step {step_number}.")
        return None, None, None # plot_json_path, csv_path, json_path

    os.makedirs(step_output_folder_path, exist_ok=True)
    csv_filename = os.path.join(step_output_folder_path, f"step_{step_number}_data.csv")
    json_filename = os.path.join(step_output_folder_path, f"step_{step_number}_data.json")
    plot_json_filename = os.path.join(step_output_folder_path, f"step_{step_number}_plot.json") # Save plot as JSON

    try:
        step_df.to_csv(csv_filename, index=False)
        print(f"Saved step {step_number} data to CSV: {csv_filename}")
    except Exception as e: print(f"Error saving step {step_number} CSV: {e}"); csv_filename = None
    try:
        # Prepare DataFrame for JSON serialization (convert datetime)
        df_for_json = step_df.copy()
        for col in df_for_json.select_dtypes(include=['datetime64[ns]']).columns:
            # Ensure NaT values are handled correctly (e.g., convert to None or empty string)
            df_for_json[col] = df_for_json[col].apply(lambda x: x.isoformat() if pd.notnull(x) else None)
        df_for_json.to_json(json_filename, orient='records', indent=4, lines=False, date_format='iso')
        print(f"Saved step {step_number} data to JSON: {json_filename}")
    except Exception as e: print(f"Error saving step {step_number} JSON: {e}"); json_filename = None

    # --- Create single figure with multiple Y axes --- 
    fig = go.Figure()

    # Column name handling (check for suffixes, same as overall plot logic)
    temp_col = f"{LV_TEMP_COL}_LV" if f"{LV_TEMP_COL}_LV" in step_df.columns else LV_TEMP_COL
    pressure_col = f"{LV_PRESSURE_COL}_LV" if f"{LV_PRESSURE_COL}_LV" in step_df.columns else LV_PRESSURE_COL
    nh3_col = f"{GC_NH3_COL}_GC" if f"{GC_NH3_COL}_GC" in step_df.columns else GC_NH3_COL
    n2_flow_col = f"{LV_N2_FLOW_COL}_LV" if f"{LV_N2_FLOW_COL}_LV" in step_df.columns else LV_N2_FLOW_COL
    h2_flow_col = f"{LV_H2_FLOW_COL}_LV" if f"{LV_H2_FLOW_COL}_LV" in step_df.columns else LV_H2_FLOW_COL
    n2_poison_col = f"{LV_N2_POISON_SP_COL}_LV" if f"{LV_N2_POISON_SP_COL}_LV" in step_df.columns else LV_N2_POISON_SP_COL
    date_col = 'Date'

    # --- Add Traces --- 
    # Y1 (Left): Temp
    if temp_col in step_df.columns and pd.api.types.is_numeric_dtype(step_df[temp_col]):
        fig.add_trace(go.Scatter(x=step_df[date_col], y=step_df[temp_col], name=f'LV Temp ({temp_col})', 
                                 mode='lines+markers', marker=dict(color='red'), yaxis='y1'))
    # Y2 (Right): Pressure
    if pressure_col in step_df.columns and pd.api.types.is_numeric_dtype(step_df[pressure_col]):
        fig.add_trace(go.Scatter(x=step_df[date_col], y=step_df[pressure_col], name=f'LV Pressure ({pressure_col})', 
                                 mode='lines+markers', line=dict(dash='dash', color='aqua'), yaxis='y2'))
    # Y3 (Right, offset): Flows
    if n2_flow_col in step_df.columns and pd.api.types.is_numeric_dtype(step_df[n2_flow_col]):
        fig.add_trace(go.Scatter(x=step_df[date_col], y=step_df[n2_flow_col], name=f'LV N2 Flow ({n2_flow_col})', 
                                 mode='lines+markers', marker=dict(color='purple'), yaxis='y3'))
    if h2_flow_col in step_df.columns and pd.api.types.is_numeric_dtype(step_df[h2_flow_col]):
        fig.add_trace(go.Scatter(x=step_df[date_col], y=step_df[h2_flow_col], name=f'LV H2 Flow ({h2_flow_col})', 
                                 mode='lines+markers', marker=dict(color='orange'), yaxis='y3'))
    # Add N2 Poisoning Flow
    if n2_poison_col in step_df.columns and pd.api.types.is_numeric_dtype(step_df[n2_poison_col]):
        fig.add_trace(go.Scatter(x=step_df[date_col], y=step_df[n2_poison_col], name=f'LV N2 Poison SP ({n2_poison_col})', 
                                 mode='lines+markers', line=dict(dash='dot', color='magenta'), yaxis='y3'))

    # Y4 (Left, offset): NH3
    if nh3_col in step_df.columns and pd.api.types.is_numeric_dtype(step_df[nh3_col]):
        fig.add_trace(go.Scatter(x=step_df[date_col], y=step_df[nh3_col], name=f'GC NH3 ({nh3_col})', 
                                 mode='lines+markers', marker=dict(color='lime'), yaxis='y4'))

    # --- Update Layout with Multiple Axes & Dark Theme ---
    fig.update_layout(
        title_text=f'Step {step_number} Analysis', 
        height=600, # Adjust height for single plot area
        hovermode='x unified',
        xaxis=dict(domain=[0.1, 0.9]), # Make space for Y axes
        yaxis=dict(
            title=f"Temp ({temp_col}) (C)",
            titlefont=dict(color='red'), 
            tickfont=dict(color='red'),
            side='left',
        ),
        yaxis2=dict(
            title=f"Pressure ({pressure_col}) (bar)", 
            titlefont=dict(color='aqua'), 
            tickfont=dict(color='aqua'),
            anchor='x', 
            overlaying='y', 
            side='right'
        ),
        yaxis3=dict(
            title="Flow / SP (ml/min)", 
            titlefont=dict(color='orange'), # Use a representative color
            tickfont=dict(color='orange'),
            anchor='free', 
            overlaying='y', 
            side='right', 
            position=0.95 # Position slightly inwards
        ),
        yaxis4=dict(
            title=f"NH3 ({nh3_col}) (%)", 
            titlefont=dict(color='lime'), 
            tickfont=dict(color='lime'),
            anchor='free', 
            overlaying='y', 
            side='left', 
            position=0.05 # Position slightly inwards
        ),
        paper_bgcolor='#2c2c2c', 
        plot_bgcolor='#383838',
        font=dict(color='#e0e0e0'),
        legend=dict(
            bgcolor='#383838', 
            bordercolor='#4a4a4a',
            orientation='h',
            yanchor='bottom',
            y=1.02, 
            xanchor='right',
            x=1
        )
    )
    # Axis styles (gridlines etc.)
    axis_style = dict(
        gridcolor='rgba(0,0,0,0)', # REMOVED GRID
        linecolor='#5a5a5a',
        zerolinecolor='#5a5a5a'
    )
    fig.update_xaxes(**axis_style, title_text="Date")
    fig.update_yaxes(**axis_style) # Apply grid/line style to all y-axes

    # --- Save Plotly JSON ---
    try:
        pio.write_json(fig, plot_json_filename)
        print(f"Saved step {step_number} Plotly plot to: {plot_json_filename}")
    except Exception as e:
        print(f"Error saving step {step_number} Plotly plot JSON: {e}")
        plot_json_filename = None

    return plot_json_filename, csv_filename, json_filename

# --- Main Orchestration Function for Web App ---
def generate_reports(lv_file_path, gc_file_path, base_output_folder):
    """
    Processes LV and GC files, generates plots and data files (CSV, JSON)
    into a timestamped subfolder within base_output_folder.
    Returns paths to generated overall files and a list of dicts for step files.
    """
    timestamp_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_run_output_folder = os.path.join(base_output_folder, timestamp_prefix)
    os.makedirs(current_run_output_folder, exist_ok=True)
    print(f"Created main output folder for this run: {current_run_output_folder}")

    results = {
        'overall_plot_path': None, # Path to plot JSON
        'overall_csv_path': None,
        'step_reports': [], # Each item will have plot_path (JSON), csv_path, json_path
        'success': False,
        'message': '',
        'num_stages': 0
    }

    try:
        print(f"Processing LV file: {lv_file_path}")
        df_lv_full = process_lv_file(lv_file_path)
        if df_lv_full.empty:
            results['message'] = "LV DataFrame is empty after processing."
            return results
        
        required_lv_cols = [LV_TEMP_COL, LV_PRESSURE_COL, LV_H2_FLOW_COL, LV_N2_FLOW_COL, LV_N2_POISON_SP_COL, 'RelativeTime', 'Date']
        missing_lv_cols = [col for col in required_lv_cols if col not in df_lv_full.columns]
        if missing_lv_cols:
            results['message'] = f"Error: Required LV columns missing: {missing_lv_cols}"
            return results

        if 'Stage' not in df_lv_full.columns or df_lv_full['Stage'].empty or df_lv_full['Stage'].max() == 0:
            num_stages = 0
            print("Warning: Stage detection failed or resulted in 0 stages.")
        else:
            num_stages = df_lv_full['Stage'].max()
            print(f"Detected {num_stages} stages in LV data.")
        results['num_stages'] = num_stages

        print(f"\nProcessing GC file: {gc_file_path}")
        df_gc_full = process_gc_file(gc_file_path)
        if df_gc_full.empty:
            print("Warning: GC DataFrame is empty for overall merge.")

        print("\nPerforming overall data merge...")
        df_merged_overall = merge_overall_data(df_lv_full, df_gc_full)
        
        # Pass the specific timestamped output folder for this run
        overall_plot_json_path, overall_csv_path = plot_overall_merged_data(df_merged_overall, current_run_output_folder)
        results['overall_plot_path'] = overall_plot_json_path
        results['overall_csv_path'] = overall_csv_path

        if num_stages > 0:
            print("\nProcessing and plotting per stage...")
            for step_num in range(1, num_stages + 1):
                print(f"\n--- Processing Step {step_num} ---")
                df_lv_step = df_lv_full[df_lv_full['Stage'] == step_num].copy()
                if df_lv_step.empty:
                    print(f"No LV data for step {step_num}."); continue
                
                step_output_folder = os.path.join(current_run_output_folder, f"step_{step_num}")
                merged_step_df = merge_step_data(df_lv_step, df_gc_full)

                if not merged_step_df.empty:
                    plot_json_path, csv_path, json_path = plot_per_step_data(merged_step_df, step_num, step_output_folder)
                    results['step_reports'].append({
                        'step_number': step_num,
                        'plot_path': plot_json_path, # Path to the plot JSON file
                        'csv_path': csv_path,
                        'json_path': json_path
                    })
                else:
                    print(f"No data merged for Step {step_num}.")
        
        results['success'] = True
        results['message'] = "Processing complete."

    except Exception as e:
        print(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()
        results['message'] = f"An error occurred: {e}"
        results['success'] = False
        
    return results

# --- New Function for Generating Comparison Plot ---
def generate_comparison_plot(stage_data_json_paths, report_folder_abs):
    """
    Generates a plot comparing selected variables from multiple stages against RelativeTime.
    Args:
        stage_data_json_paths (list): List of absolute paths to stage data JSON files.
        report_folder_abs (str): Absolute path to the main report folder for this run 
                                (e.g., 'static/reports/YYYYMMDD_HHMMSS'),
                                used to save the comparison plot.
    Returns:
        str: Absolute path to the generated comparison plot JSON file, or None on error.
    """
    if not stage_data_json_paths:
        print("No stage data paths provided for comparison.")
        return None

    # Create a subfolder for comparison plots if it doesn't exist
    comparison_output_folder = os.path.join(report_folder_abs, "comparison_plots")
    os.makedirs(comparison_output_folder, exist_ok=True)
    plot_json_filename = os.path.join(comparison_output_folder, f"stages_comparison_plot_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}.json")

    fig = go.Figure()
    colors = pio.templates["plotly_dark"].layout.colorway # Get default dark theme colors

    for i, json_path in enumerate(stage_data_json_paths):
        try:
            stage_df = pd.read_json(json_path, orient='records')
            stage_num = "Unknown" # Fallback
            # Try to infer stage number from file path (might need adjustment based on actual path structure)
            try:
                 # e.g., path might be /.../step_1/step_1_data.json
                 path_parts = os.path.normpath(json_path).split(os.sep)
                 for part in reversed(path_parts):
                     if part.startswith("step_"):
                         stage_num = part.split('_')[1]
                         break
            except Exception as e_parse:
                print(f"Could not parse stage number from path {json_path}: {e_parse}")
            
            if stage_df.empty or 'RelativeTime' not in stage_df.columns:
                print(f"Data for stage {stage_num} (from {json_path}) is empty or missing RelativeTime.")
                continue

            # Convert relevant columns to numeric, coercing errors
            for col in [LV_TEMP_COL, GC_NH3_COL, LV_PRESSURE_COL, LV_H2_FLOW_COL, LV_N2_FLOW_COL, LV_N2_POISON_SP_COL]:
                col_lv = f"{col}_LV" # Check for suffixed version first
                col_gc = f"{col}_GC"
                actual_col = None
                if col_lv in stage_df.columns: actual_col = col_lv
                elif col_gc in stage_df.columns: actual_col = col_gc
                elif col in stage_df.columns: actual_col = col 
                
                if actual_col and actual_col in stage_df.columns:
                    stage_df[actual_col] = pd.to_numeric(stage_df[actual_col], errors='coerce')
                # else:
                #     print(f"Column {col} (or its variants) not found in stage {stage_num} data.")

            color_idx = i % len(colors)

            # --- Add traces for this stage (Example: Temp and NH3) ---
            # You can add more traces (Pressure, Flows) and assign them to different y-axes if needed

            if f"{LV_TEMP_COL}_LV" in stage_df.columns:
                fig.add_trace(go.Scatter(x=stage_df['RelativeTime'], y=stage_df[f"{LV_TEMP_COL}_LV"], 
                                         name=f'Stage {stage_num} - Temp ({LV_TEMP_COL})', 
                                         mode='lines+markers', yaxis='y1', line=dict(color=colors[color_idx])))
            elif LV_TEMP_COL in stage_df.columns: # Check for non-suffixed version
                 fig.add_trace(go.Scatter(x=stage_df['RelativeTime'], y=stage_df[LV_TEMP_COL], 
                                         name=f'Stage {stage_num} - Temp ({LV_TEMP_COL})', 
                                         mode='lines+markers', yaxis='y1', line=dict(color=colors[color_idx])))

            if f"{GC_NH3_COL}_GC" in stage_df.columns:
                fig.add_trace(go.Scatter(x=stage_df['RelativeTime'], y=stage_df[f"{GC_NH3_COL}_GC"], 
                                         name=f'Stage {stage_num} - NH3 ({GC_NH3_COL})', 
                                         mode='lines+markers', yaxis='y2', line=dict(color=colors[color_idx], dash='dot')))
            elif GC_NH3_COL in stage_df.columns: # Check for non-suffixed version
                 fig.add_trace(go.Scatter(x=stage_df['RelativeTime'], y=stage_df[GC_NH3_COL], 
                                         name=f'Stage {stage_num} - NH3 ({GC_NH3_COL})', 
                                         mode='lines+markers', yaxis='y2', line=dict(color=colors[color_idx], dash='dot')))
            
            # TODO: Add other traces as needed (Pressure, H2, N2, N2_poison) - they might need yaxis3, yaxis4 etc.

        except Exception as e:
            print(f"Error processing data for comparison from {json_path}: {e}")
            continue

    if not fig.data:
        print("No data added to comparison plot. Aborting plot generation.")
        return None

    fig.update_layout(
        title_text='Stage Comparison vs. Relative Time',
        height=700,
        hovermode='x unified',
        xaxis_title='Relative Time (s or min - check units)',
        yaxis=dict(title=f'Temperature ({LV_TEMP_COL}) (C)'),
        yaxis2=dict(title=f'NH3 ({GC_NH3_COL}) (%)', overlaying='y', side='right'),
        # TODO: Define yaxis3, yaxis4 etc. if more traces are added with different units/scales
        paper_bgcolor='#2c2c2c',
        plot_bgcolor='#383838',
        font=dict(color='#e0e0e0'),
        legend=dict(bgcolor='#383838', bordercolor='#4a4a4a')
    )
    axis_style = dict(gridcolor='rgba(0,0,0,0)', linecolor='#5a5a5a', zerolinecolor='#5a5a5a')
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)

    try:
        pio.write_json(fig, plot_json_filename)
        print(f"Saved stage comparison plot to: {plot_json_filename}")
        return plot_json_filename # Return absolute path
    except Exception as e:
        print(f"Error saving stage comparison plot JSON: {e}")
        return None

def generate_stage_plot_plotly(stage_df, stage_num):
    """Generates a plot for a specific stage using Plotly with multiple y-axes."""
    fig = go.Figure()

    # Handle RelativeTime for x-axis
    if pd.api.types.is_timedelta64_dtype(stage_df['RelativeTime']):
        plot_time = stage_df['RelativeTime'].dt.total_seconds() / 3600 # Hours
        time_axis_title = "Relative Time (hours from stage start)"
    else:
        plot_time = stage_df['RelativeTime']
        time_axis_title = "Relative Time"

    # Define column names, checking for _LV or _GC suffixes from merge
    temp_col = 'T Heater 1_LV' if 'T Heater 1_LV' in stage_df.columns else 'T Heater 1'
    pressure_col = 'Pressure setpoint_LV' if 'Pressure setpoint_LV' in stage_df.columns else 'Pressure setpoint'
    h2_flow_col = 'H2 Actual Flow_LV' if 'H2 Actual Flow_LV' in stage_df.columns else 'H2 Actual Flow'
    n2_flow_col = 'N2 Actual Flow_LV' if 'N2 Actual Flow_LV' in stage_df.columns else 'N2 Actual Flow'
    n2_poison_sp_col = 'N2 poisoning set-point_LV' if 'N2 poisoning set-point_LV' in stage_df.columns else 'N2 poisoning set-point'
    nh3_col = 'NH3_GC' if 'NH3_GC' in stage_df.columns else 'NH3'

    # Add Traces
    # Y-axis 1 (Left): Temperature
    if temp_col in stage_df.columns and pd.api.types.is_numeric_dtype(stage_df[temp_col]):
        fig.add_trace(go.Scatter(x=plot_time, y=stage_df[temp_col], name=f'Temp ({temp_col})', mode='lines+markers', yaxis='y1'))

    # Y-axis 2 (Right): Pressure
    if pressure_col in stage_df.columns and pd.api.types.is_numeric_dtype(stage_df[pressure_col]):
        fig.add_trace(go.Scatter(x=plot_time, y=stage_df[pressure_col], name=f'Pressure ({pressure_col})', mode='lines+markers', yaxis='y2'))

    # Y-axis 3 (Left, Offset): Flows (H2, N2, N2 Poisoning SP)
    if h2_flow_col in stage_df.columns and pd.api.types.is_numeric_dtype(stage_df[h2_flow_col]):
        fig.add_trace(go.Scatter(x=plot_time, y=stage_df[h2_flow_col], name=f'H2 Flow ({h2_flow_col})', mode='lines+markers', yaxis='y3'))
    if n2_flow_col in stage_df.columns and pd.api.types.is_numeric_dtype(stage_df[n2_flow_col]):
        fig.add_trace(go.Scatter(x=plot_time, y=stage_df[n2_flow_col], name=f'N2 Flow ({n2_flow_col})', mode='lines+markers', yaxis='y3'))
    if n2_poison_sp_col in stage_df.columns and pd.api.types.is_numeric_dtype(stage_df[n2_poison_sp_col]):
        fig.add_trace(go.Scatter(x=plot_time, y=stage_df[n2_poison_sp_col], name=f'N2 Poison SP ({n2_poison_sp_col})', mode='lines', yaxis='y3'))

    # Y-axis 4 (Right, Offset): NH3
    if nh3_col in stage_df.columns and pd.api.types.is_numeric_dtype(stage_df[nh3_col]):
        fig.add_trace(go.Scatter(x=plot_time, y=stage_df[nh3_col], name=f'NH3 ({nh3_col})', mode='lines+markers', yaxis='y4', line=dict(color='lime')))

    # Update Layout
    fig.update_layout(
        title_text=f"Stage {stage_num} Analysis",
        xaxis_title=time_axis_title,
        yaxis=dict(title='Temperature (°C)', side='left'),
        yaxis2=dict(title='Pressure (bar)', side='right', overlaying='y'),
        yaxis3=dict(title='Flows (ml/min)', side='left', overlaying='y', anchor='free', position=0.10,autoshift=True), # Shifted left
        yaxis4=dict(title='NH3 (%)', side='right', overlaying='y', anchor='free', position=0.90,autoshift=True), # Shifted right
        **dark_theme_layout_updates,
        legend=dict(y=1.1, orientation='h') # Slightly adjust legend for stage plot title space
    )
    # Adjust xaxis domain to make space for offset y-axes
    fig.update_layout(xaxis_domain=[0.15, 0.85])

    plot_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return plot_json

# --- New Function for Cross-Report Comparison Plot Generation ---
def create_cross_comparison_plot(selected_comparison_json_file_paths, current_report_timestamp, current_report_selected_stages, base_reports_folder_abs):
    """
    Generates a plot combining traces from selected existing comparison_plot JSONs 
    and specified stages from a current report.

    Args:
        selected_comparison_json_file_paths (list): List of absolute paths to pre-existing 
                                                    stages_comparison_plot_*.json files.
        current_report_timestamp (str): Timestamp of the currently loaded report 
                                       (e.g., '20250513_181058'). Can be None.
        current_report_selected_stages (list): List of stage numbers (int) selected 
                                               from the current report.
        base_reports_folder_abs (str): Absolute path to the root 'static/reports' folder.

    Returns:
        str: Absolute path to the generated cross-comparison plot JSON file, or None on error.
    """
    if not selected_comparison_json_file_paths and not (current_report_timestamp and current_report_selected_stages):
        print("Error: No data sources provided for cross-comparison.")
        return None

    cross_comp_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_subfolder_name = f"cross_comp_{cross_comp_timestamp}"
    # Output folder will be like static/reports/cross_comparisons/cross_comp_YYYYMMDD_HHMMSS/
    cross_comparison_output_dir = os.path.join(base_reports_folder_abs, "cross_comparisons", output_subfolder_name)
    os.makedirs(cross_comparison_output_dir, exist_ok=True)
    
    plot_json_filename = os.path.join(cross_comparison_output_dir, f"cross_comparison_plot_{cross_comp_timestamp}.json")

    fig = go.Figure()
    # Use a color sequence, cycling through it for different sources/stages
    # Using plotly_dark colorway as a base, can be extended if more colors needed
    color_palette = pio.templates["plotly_dark"].layout.colorway 
    color_idx = 0

    # 1. Process pre-existing comparison_plot JSONs
    for json_full_path in selected_comparison_json_file_paths:
        try:
            with open(json_full_path, 'r') as f:
                existing_plot_json = json.load(f)
            
            # Extract report folder name from path for labelling (e.g., 20250513_181058)
            # Path is like "static/reports/20250513_181058/comparison_plots/stages_comparison_plot_....json"
            path_parts = os.path.normpath(json_full_path).split(os.sep)
            report_source_label = "UnknownReport"
            if len(path_parts) > 3 and path_parts[-4] == 'reports': # Expects static/reports/REPORT_TS/...
                report_source_label = path_parts[-3]
            elif len(path_parts) > 2 and path_parts[-3] == 'reports': # Less nested, for testing if path is reports/REPORT_TS/...
                 report_source_label = path_parts[-2]

            if 'data' in existing_plot_json:
                for trace in existing_plot_json['data']:
                    original_name = trace.get('name', 'Unnamed Trace')
                    trace['name'] = f"{report_source_label} - {original_name}"
                    # Preserve original y-axis assignment if possible, or default
                    # The comparison plots seem to use 'y' and 'y2' for yaxis field directly
                    if 'yaxis' not in trace: 
                        trace['yaxis'] = 'y1' # Default to y1 if not specified
                    elif trace['yaxis'] == 'y':
                        trace['yaxis'] = 'y1' 
                    # trace['yaxis'] might already be 'y2', 'y3' etc. - keep it.
                    
                    # Cycle through colors for visual distinction between sources
                    trace_color = trace.get('line', {}).get('color')
                    if not trace_color: # If no color, assign one
                        if 'line' not in trace: trace['line'] = {}
                        trace['line']['color'] = color_palette[color_idx % len(color_palette)]
                    # Potentially make lines from different files slightly different (e.g. dash styles)
                    # trace['line']['dash'] = 'dash' # Example: make all from this file dashed
                    fig.add_trace(go.Scatter(trace))
                color_idx += 1 # Next color for the next file

        except Exception as e:
            print(f"Error processing existing comparison JSON {json_full_path}: {e}")
            # Continue to next file or stages

    # 2. Process selected stages from the current report
    if current_report_timestamp and current_report_selected_stages:
        current_report_folder_abs = os.path.join(base_reports_folder_abs, current_report_timestamp)
        for stage_num in current_report_selected_stages:
            stage_data_json_path = os.path.join(current_report_folder_abs, f"step_{stage_num}", f"step_{stage_num}_data.json")
            try:
                if not os.path.exists(stage_data_json_path):
                    print(f"Stage data JSON not found for current report stage {stage_num}: {stage_data_json_path}")
                    continue
                
                stage_df = pd.read_json(stage_data_json_path, orient='records')
                if stage_df.empty or 'RelativeTime' not in stage_df.columns:
                    print(f"Data for current report stage {stage_num} is empty or missing RelativeTime.")
                    continue
                
                # Convert relevant columns to numeric
                for col_name_base in [LV_TEMP_COL, GC_NH3_COL]: # Add more if needed
                    col_lv = f"{col_name_base}_LV"
                    col_gc = f"{col_name_base}_GC"
                    actual_col_to_convert = None
                    if col_lv in stage_df.columns: actual_col_to_convert = col_lv
                    elif col_gc in stage_df.columns: actual_col_to_convert = col_gc
                    elif col_name_base in stage_df.columns: actual_col_to_convert = col_name_base
                    
                    if actual_col_to_convert:
                         stage_df[actual_col_to_convert] = pd.to_numeric(stage_df[actual_col_to_convert], errors='coerce')

                current_stage_color = color_palette[color_idx % len(color_palette)]

                # Add Temp trace for current stage to y1
                temp_col_actual = LV_TEMP_COL + '_LV' if LV_TEMP_COL + '_LV' in stage_df.columns else LV_TEMP_COL
                if temp_col_actual in stage_df.columns and pd.api.types.is_numeric_dtype(stage_df[temp_col_actual]):
                    fig.add_trace(go.Scatter(x=stage_df['RelativeTime'], y=stage_df[temp_col_actual], 
                                             name=f'Current ({current_report_timestamp}) - Stage {stage_num} - Temp', 
                                             mode='lines+markers', yaxis='y1', line=dict(color=current_stage_color)))
                
                # Add NH3 trace for current stage to y2
                nh3_col_actual = GC_NH3_COL + '_GC' if GC_NH3_COL + '_GC' in stage_df.columns else GC_NH3_COL
                if nh3_col_actual in stage_df.columns and pd.api.types.is_numeric_dtype(stage_df[nh3_col_actual]):
                    fig.add_trace(go.Scatter(x=stage_df['RelativeTime'], y=stage_df[nh3_col_actual], 
                                             name=f'Current ({current_report_timestamp}) - Stage {stage_num} - NH3', 
                                             mode='lines+markers', yaxis='y2', line=dict(color=current_stage_color, dash='dot')))
                color_idx += 1 # Next color for next stage/source

            except Exception as e:
                print(f"Error processing current report stage {stage_num} from {stage_data_json_path}: {e}")
                # Continue to next stage
    
    if not fig.data:
        print("No data traces were added to the cross-comparison plot. Aborting generation.")
        return None

    # --- Finalize Layout ---
    fig.update_layout(
        title_text='Cross-Report Stage Comparison vs. Relative Time',
        height=750, # Slightly taller for potentially more traces
        hovermode='x unified',
        xaxis_title='Relative Time (s or min - check units from original plots)', # Emphasize to check original units
        yaxis=dict(title=f'Y1-Axis (e.g., Temperature ({LV_TEMP_COL}) (C))', side='left'),
        yaxis2=dict(title=f'Y2-Axis (e.g., NH3 ({GC_NH3_COL}) (%))', overlaying='y1', side='right'),
        # Add more yaxis definitions (yaxis3, yaxis4) if other parameters are plotted from sources
        # and need their own axes. For now, assuming most things map to y1 or y2.
        paper_bgcolor='#2c2c2c',
        plot_bgcolor='#383838',
        font=dict(color='#e0e0e0'),
        legend=dict(bgcolor='#383838', bordercolor='#4a4a4a', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    axis_style = dict(gridcolor='rgba(0,0,0,0)', linecolor='#5a5a5a', zerolinecolor='#5a5a5a')
    fig.update_xaxes(**axis_style)
    # Apply to y1 and y2 specifically, and any others if defined
    fig.update_yaxes(selector=dict(overlaying=None), **axis_style) # For y1 (the base yaxis)
    fig.update_yaxes(selector=dict(overlaying='y1'), **axis_style) # For y2, y3 etc. that overlay y1

    try:
        pio.write_json(fig, plot_json_filename)
        print(f"Saved cross-comparison plot to: {plot_json_filename}")
        return plot_json_filename # Return absolute path
    except Exception as e:
        print(f"Error saving cross-comparison plot JSON: {e}")
        return None

# Example of how to call (for testing, not used by Flask directly like this)
# if __name__ == '__main__':
#     # Create dummy files for testing if they don't exist
#     if not os.path.exists('dummy_lv.txt') or not os.path.exists('dummy_gc.txt'):
#         print("Please create dummy_lv.txt and dummy_gc.txt for testing this script directly.")
#     else:
#         test_results = generate_reports(
#             lv_file_path='dummy_lv.txt', 
#             gc_file_path='dummy_gc.txt', 
#             base_output_folder='static/reports' # Flask will serve from static
#         )
#         print("\n--- FINAL RESULTS ---")
#         import json
#         print(json.dumps(test_results, indent=2)) 