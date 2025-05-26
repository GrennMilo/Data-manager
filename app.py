from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, make_response
import os
import main_web_processor  # Import the refactored processing logic
from werkzeug.utils import secure_filename
import pandas as pd # Needed for combining dataframes
import io # Needed for sending file data from memory
import glob # Import glob
from main_web_processor import generate_reports, generate_comparison_plot, create_cross_comparison_plot # Import new function
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static') # Create Flask application instance

# --- Configuration ---
# Define the path for uploaded files. Create the directory if it doesn't exist.
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define the base directory for reports within the static folder
REPORTS_FOLDER = os.path.join(app.static_folder, 'reports') # Use app.static_folder
if not os.path.exists(REPORTS_FOLDER):
    os.makedirs(REPORTS_FOLDER)
# Explicitly add the path to the app config dictionary
app.config['REPORTS_FOLDER'] = REPORTS_FOLDER 

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Routes ---
@app.route('/')
def index():
    """ Serves the main HTML page. """
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_files():
    """ 
    Handles file uploads, triggers processing, and returns results as JSON.
    """
    # --- File Upload Handling ---
    if 'lv_file' not in request.files or 'gc_file' not in request.files:
        return jsonify({'success': False, 'message': 'Missing LV or GC file in request.'}), 400

    lv_file = request.files['lv_file']
    gc_file = request.files['gc_file']

    if lv_file.filename == '' or gc_file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file(s).'}), 400

    if lv_file and allowed_file(lv_file.filename) and gc_file and allowed_file(gc_file.filename):
        # Secure filenames and save uploaded files temporarily
        lv_filename = secure_filename(lv_file.filename)
        gc_filename = secure_filename(gc_file.filename)
        lv_filepath = os.path.join(app.config['UPLOAD_FOLDER'], lv_filename)
        gc_filepath = os.path.join(app.config['UPLOAD_FOLDER'], gc_filename)

        try:
            lv_file.save(lv_filepath)
            gc_file.save(gc_filepath)
            print(f"Files saved: {lv_filepath}, {gc_filepath}")
        except Exception as e:
            print(f"Error saving files: {e}")
            return jsonify({'success': False, 'message': f'Error saving uploaded files: {e}'}), 500

        # --- Data Processing ---
        try:
            # Get the custom report prefix text from the form
            report_prefix_text = request.form.get('report_prefix_text', '').strip()

            # Call the main processing function from the refactored module
            # Pass the static reports folder as the base output directory and the prefix
            results = main_web_processor.generate_reports(
                lv_filepath,
                gc_filepath,
                REPORTS_FOLDER,
                report_prefix_text=report_prefix_text
            )
            
            # --- Cleanup Uploaded Files (Optional) ---
            # You might want to keep these for debugging or remove them
            # try:
            #     os.remove(lv_filepath)
            #     os.remove(gc_filepath)
            #     print(f"Cleaned up uploaded files: {lv_filepath}, {gc_filepath}")
            # except OSError as e:
            #     print(f"Error removing uploaded files: {e}")
            
            # Adjust paths in results to be relative to static folder root
            # Ensure the paths start with 'static/' for web access
            static_folder_name = os.path.basename(app.static_folder) # Usually 'static'

            # Determine the actual folder name used (prefix + timestamp or just timestamp)
            # This is a bit more complex now, need to get it from one of the paths if available
            # or reconstruct it if no paths were generated but processing was considered successful for the folder creation part.
            actual_report_folder_name = None
            if results.get('overall_plot_path'):
                # Path is like: static/reports/PREFIX_TIMESTAMP/overall_plot.json
                actual_report_folder_name = os.path.basename(os.path.dirname(results['overall_plot_path']))
            elif results.get('overall_csv_path'):
                actual_report_folder_name = os.path.basename(os.path.dirname(results['overall_csv_path']))
            elif results.get('step_reports') and results['step_reports'][0].get('plot_path'):
                 actual_report_folder_name = os.path.basename(os.path.dirname(os.path.dirname(results['step_reports'][0]['plot_path'])))
            # Fallback if no files generated but folder might exist (e.g. empty data)
            # This part relies on the fact that generate_reports would have created the folder already
            # We need to be careful here; the results structure should ideally always give us the folder name
            # For now, let's assume one of the above conditions will hit if a folder was made for results.

            if results.get('overall_plot_path'):
                relative_path = os.path.relpath(results['overall_plot_path'], app.static_folder)
                results['overall_plot_path'] = os.path.join(static_folder_name, relative_path).replace('\\', '/')
            if results.get('overall_csv_path'):
                relative_path = os.path.relpath(results['overall_csv_path'], app.static_folder)
                results['overall_csv_path'] = os.path.join(static_folder_name, relative_path).replace('\\', '/')
            
            for step_report in results.get('step_reports', []):
                if step_report.get('plot_path'):
                    relative_path = os.path.relpath(step_report['plot_path'], app.static_folder)
                    step_report['plot_path'] = os.path.join(static_folder_name, relative_path).replace('\\', '/')
                if step_report.get('csv_path'):
                    relative_path = os.path.relpath(step_report['csv_path'], app.static_folder)
                    step_report['csv_path'] = os.path.join(static_folder_name, relative_path).replace('\\', '/')
                if step_report.get('json_path'):
                    relative_path = os.path.relpath(step_report['json_path'], app.static_folder)
                    step_report['json_path'] = os.path.join(static_folder_name, relative_path).replace('\\', '/')

            # Add the timestamp prefix to the response
            if results.get('success'):
                # The timestamp_prefix in results should now be the actual folder name (prefix_timestamp or just timestamp)
                if actual_report_folder_name and actual_report_folder_name != 'reports': 
                    results['timestamp_prefix'] = actual_report_folder_name
                elif report_prefix_text: # if processing made the folder but no files, try to construct it
                    # This is a less ideal fallback, assumes current time if files were not made
                    current_timestamp_for_fallback = datetime.now().strftime("%Y%m%d_%H%M%S")
                    results['timestamp_prefix'] = f"{report_prefix_text}_{current_timestamp_for_fallback}"
                # else: # if no prefix and no files, the original logic for timestamp_prefix might need to be re-evaluated
                    # For now, if actual_report_folder_name is None, timestamp_prefix might remain None or an old value

            return jsonify(results)

        except Exception as e:
            print(f"Error during main processing: {e}")
            import traceback
            traceback.print_exc() # Print detailed error to Flask console
            return jsonify({'success': False, 'message': f'Processing failed: {e}'}), 500
    else:
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400

# --- New Route for Downloading Selected Stages --- 
@app.route('/download_selected_stages', methods=['POST'])
def download_selected_stages():
    """ 
    Receives a list of JSON file paths for selected stages, 
    reads them, combines the data, and sends back a combined CSV file.
    """
    try:
        data = request.get_json()
        json_paths_relative = data.get('json_paths')

        if not json_paths_relative or not isinstance(json_paths_relative, list):
            return jsonify({'success': False, 'message': 'Invalid or missing list of JSON paths.'}), 400
        
        combined_df = pd.DataFrame()
        dfs_to_combine = []

        # Base directory is the project root where app.py is
        base_dir = os.path.dirname(os.path.abspath(__file__))

        for rel_path in json_paths_relative:
            # Construct absolute path and sanitize it
            # Ensure the path stays within the intended static/reports directory
            abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
            allowed_dir = os.path.abspath(os.path.join(base_dir, 'static', 'reports'))
            
            if not abs_path.startswith(allowed_dir):
                 print(f"Warning: Access denied for path outside allowed directory: {rel_path}")
                 continue # Skip potentially malicious paths
            
            if os.path.exists(abs_path):
                try:
                    # Read JSON into DataFrame
                    # orient='records' matches how we saved it in main_web_processor
                    df_step = pd.read_json(abs_path, orient='records') 
                    dfs_to_combine.append(df_step)
                except Exception as e:
                    print(f"Error reading or processing JSON file {abs_path}: {e}")
                    # Optionally inform the user about specific file errors
            else:
                print(f"Warning: JSON file not found: {abs_path}")

        if not dfs_to_combine:
            return jsonify({'success': False, 'message': 'No valid stage data found for selected paths.'}), 404

        # Combine all valid dataframes
        combined_df = pd.concat(dfs_to_combine, ignore_index=True)
        # Optional: Sort by date if needed after combining
        if 'Date' in combined_df.columns:
             try:
                 # Convert Date back to datetime if it was stringified in JSON
                 combined_df['Date'] = pd.to_datetime(combined_df['Date'])
                 combined_df = combined_df.sort_values(by='Date')
             except Exception as e:
                 print(f"Warning: Could not sort combined data by Date: {e}")

        # Convert combined DataFrame to CSV in memory
        csv_buffer = io.StringIO()
        combined_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        # Send the CSV data as a file download
        response = make_response(csv_buffer.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=selected_stages_data.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error creating combined CSV: {e}'}), 500

# --- Route to serve generated static files (reports) ---
# This is handled implicitly by Flask if files are in the 'static' folder.
# If your reports were outside 'static', you'd need a route like this:
# @app.route('/reports/<path:filename>')
# def serve_report(filename):
#     return send_from_directory(REPORTS_FOLDER_ABSOLUTE, filename)

# --- New Routes for Loading Previous Reports ---

@app.route('/list_reports', methods=['GET'])
def list_reports():
    """Lists the available timestamped report folders."""
    try:
        reports_base = app.config['REPORTS_FOLDER']
        # List only directories directly under the reports folder
        all_items = os.listdir(reports_base)
        report_folders = [d for d in all_items if os.path.isdir(os.path.join(reports_base, d))]
        # Simple sorting, assumes YYYYMMDD_HHMMSS format
        report_folders.sort(reverse=True) 
        return jsonify({'success': True, 'reports': report_folders})
    except Exception as e:
        print(f"Error listing reports: {e}")
        return jsonify({'success': False, 'message': f'Error listing reports: {e}'}), 500

@app.route('/load_report/<timestamp>', methods=['GET'])
def load_report(timestamp):
    """Loads data structure for a specific report timestamp."""
    try:
        report_folder_rel = os.path.join('reports', timestamp)
        report_folder_abs = os.path.join(app.static_folder, report_folder_rel)

        if not os.path.isdir(report_folder_abs):
            return jsonify({'success': False, 'message': f'Report folder not found: {timestamp}'}), 404

        results = {
            'success': True,
            'timestamp_prefix': timestamp,
            'overall_plot_path': None,
            'overall_csv_path': None,
            'step_reports': [],
            'num_stages': 0
        }

        # Find overall files
        # Paths should start with 'static/' for web access
        static_folder_name = os.path.basename(app.static_folder) # Usually 'static'

        overall_plot_file_rel_to_static = os.path.join(report_folder_rel, 'overall_plot.json')
        overall_csv_file_rel_to_static = os.path.join(report_folder_rel, 'overall_merged_data.csv')
        
        if os.path.exists(os.path.join(app.static_folder, overall_plot_file_rel_to_static)):
            results['overall_plot_path'] = os.path.join(static_folder_name, overall_plot_file_rel_to_static).replace('\\', '/')
        if os.path.exists(os.path.join(app.static_folder, overall_csv_file_rel_to_static)):
            results['overall_csv_path'] = os.path.join(static_folder_name, overall_csv_file_rel_to_static).replace('\\', '/')

        # Find step folders and files
        step_folders = sorted(
            glob.glob(os.path.join(report_folder_abs, 'step_*')),
            key=lambda x: int(os.path.basename(x).split('_')[1]) # Sort by step number
        )
        
        for step_folder_abs in step_folders:
            step_name = os.path.basename(step_folder_abs)
            try:
                step_num = int(step_name.split('_')[1])
            except (IndexError, ValueError):
                print(f"Warning: Could not parse step number from folder: {step_name}")
                continue
                
            step_folder_rel = os.path.join(report_folder_rel, step_name)
            step_report = {
                'step_number': step_num,
                'plot_path': None,
                'csv_path': None,
                'json_path': None
            }

            plot_file_rel_to_static = os.path.join(step_folder_rel, f'step_{step_num}_plot.json')
            csv_file_rel_to_static = os.path.join(step_folder_rel, f'step_{step_num}_data.csv')
            json_file_rel_to_static = os.path.join(step_folder_rel, f'step_{step_num}_data.json')
            
            if os.path.exists(os.path.join(app.static_folder, plot_file_rel_to_static)):
                step_report['plot_path'] = os.path.join(static_folder_name, plot_file_rel_to_static).replace('\\', '/')
            if os.path.exists(os.path.join(app.static_folder, csv_file_rel_to_static)):
                step_report['csv_path'] = os.path.join(static_folder_name, csv_file_rel_to_static).replace('\\', '/')
            if os.path.exists(os.path.join(app.static_folder, json_file_rel_to_static)):
                step_report['json_path'] = os.path.join(static_folder_name, json_file_rel_to_static).replace('\\', '/')
                
            results['step_reports'].append(step_report)

        results['num_stages'] = len(results['step_reports'])
        results['message'] = f"Loaded report data for {timestamp}."

        return jsonify(results)

    except Exception as e:
        print(f"Error loading report {timestamp}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error loading report {timestamp}: {e}'}), 500

# --- New Route for Stage Comparison ---
@app.route('/compare_stages', methods=['POST'])
def compare_stages():
    """Generates a comparison plot for selected stages."""
    try:
        data = request.get_json()
        timestamp = data.get('timestamp')
        stage_numbers = data.get('stages')
        comparison_prefix = data.get('comparison_prefix', '').strip() # Get the prefix

        if not timestamp or not stage_numbers or not isinstance(stage_numbers, list) or len(stage_numbers) < 1:
            return jsonify({'success': False, 'message': 'Missing or invalid timestamp or stage numbers.'}), 400

        # Construct the base path for the report
        report_folder_abs = os.path.join(app.static_folder, 'reports', timestamp)
        if not os.path.isdir(report_folder_abs):
             return jsonify({'success': False, 'message': f'Report folder not found: {timestamp}'}), 404

        # Find the JSON data files for the selected stages
        stage_data_paths = []
        for stage_num in stage_numbers:
            json_file = os.path.join(report_folder_abs, f'step_{stage_num}', f'step_{stage_num}_data.json')
            if os.path.exists(json_file):
                stage_data_paths.append(json_file)
            else:
                print(f"Warning: Data file not found for stage {stage_num} in report {timestamp}: {json_file}")
                # Decide if you want to fail or just proceed with available data
                # return jsonify({'success': False, 'message': f'Data file missing for stage {stage_num}'}), 404
        
        if not stage_data_paths:
             return jsonify({'success': False, 'message': 'No data files found for selected stages.'}), 404

        # Call the new function to generate the comparison plot
        # It needs the base output folder to save the plot
        comparison_plot_path = generate_comparison_plot(stage_data_paths, report_folder_abs, comparison_prefix) # Pass the prefix

        if comparison_plot_path:
            # Convert the absolute path to a web-accessible path (relative to static)
            static_folder_name = os.path.basename(app.static_folder)
            relative_path = os.path.relpath(comparison_plot_path, app.static_folder)
            web_path = os.path.join(static_folder_name, relative_path).replace('\\', '/')
            return jsonify({'success': True, 'comparison_plot_path': web_path})
        else:
            return jsonify({'success': False, 'message': 'Failed to generate comparison plot.'}), 500

    except Exception as e:
        print(f"Error comparing stages: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error comparing stages: {e}'}), 500

# --- New Endpoint to List Comparison Plots in a Report Folder ---
@app.route('/list_comparison_plots/<timestamp>', methods=['GET'])
def list_comparison_plots_in_folder(timestamp):
    """Lists available *_stages_comparison_plot_*.json files within a specific report's comparison_plots directory."""
    try:
        report_folder_rel = os.path.join('reports', timestamp, 'comparison_plots')
        report_folder_abs = os.path.join(app.static_folder, report_folder_rel)

        if not os.path.isdir(report_folder_abs):
            return jsonify({'success': False, 'message': f'Comparison plots folder not found for report: {timestamp}'}), 404

        comparison_plot_files = []
        for filename in os.listdir(report_folder_abs):
            # Updated condition to correctly identify comparison plots with optional prefixes
            if '_stages_comparison_plot_' in filename and filename.endswith('.json'):
                # Store path relative to the specific timestamp's folder for easier reconstruction later
                # e.g., comparison_plots/stages_comparison_plot_XYZ.json
                relative_path_in_timestamp_folder = os.path.join('comparison_plots', filename)
                comparison_plot_files.append({
                    'name': filename, 
                    'path': relative_path_in_timestamp_folder.replace('\\', '/')
                })
        
        return jsonify({'success': True, 'comparison_plots': comparison_plot_files})
    except Exception as e:
        print(f"Error listing comparison plots for {timestamp}: {e}")
        return jsonify({'success': False, 'message': f'Error listing comparison plots: {e}'}), 500

# --- New Endpoint for Generating Cross-Report Comparison Plot ---
@app.route('/generate_cross_comparison', methods=['POST'])
def generate_cross_report_comparison():
    """Generates a cross-report comparison plot from selected sources."""
    try:
        data = request.get_json()
        selected_json_rel_paths = data.get('selected_comparison_json_paths', []) # e.g. ["static/reports/TS1/comp_plots/file.json", ...]
        current_report_ts = data.get('current_report_timestamp')
        current_selected_stages = data.get('current_report_selected_stages', [])

        if not selected_json_rel_paths and not (current_report_ts and current_selected_stages):
            return jsonify({'success': False, 'message': 'No data sources provided for cross-comparison.'}), 400

        base_dir = os.path.dirname(os.path.abspath(__file__)) # Project root
        static_reports_folder_abs = os.path.join(base_dir, app.static_folder, 'reports') # Absolute path to static/reports

        absolute_selected_json_paths = []
        if selected_json_rel_paths:
            for rel_path in selected_json_rel_paths:
                # Clean up any URL artifacts in the rel_path
                rel_path = rel_path.replace('%20', ' ').replace('\\', '/')
                
                # rel_path is like "static/reports/TIMESTAMP/comparison_plots/FILENAME.json"
                # We need path from project root. os.path.join will handle this if base_dir is project root.
                abs_path = os.path.normpath(os.path.join(base_dir, rel_path))
                
                # Security check: ensure it's within the static_reports_folder_abs
                if not abs_path.startswith(static_reports_folder_abs):
                    print(f"Security Warning: Attempt to access path outside allowed reports directory: {rel_path}")
                    continue 
                
                if os.path.exists(abs_path):
                    absolute_selected_json_paths.append(abs_path)
                    print(f"Added JSON file for cross-comparison: {abs_path}")
                else:
                    print(f"Warning: Selected comparison JSON not found at {abs_path} (from relative {rel_path})")

        # Call the processing function from main_web_processor
        cross_plot_abs_path = create_cross_comparison_plot(
            selected_comparison_json_file_paths=absolute_selected_json_paths,
            current_report_timestamp=current_report_ts,
            current_report_selected_stages=current_selected_stages,
            base_reports_folder_abs=static_reports_folder_abs 
        )

        if cross_plot_abs_path:
            # Convert the absolute path of the new plot to a web-accessible relative path (from project root)
            # e.g., static/reports/cross_comparisons/cross_comp_TIMESTAMP/plot.json
            web_path = os.path.relpath(cross_plot_abs_path, base_dir).replace('\\', '/')
            return jsonify({'success': True, 'cross_comparison_plot_path': web_path})
        else:
            return jsonify({'success': False, 'message': 'Failed to generate cross-comparison plot.'}), 500

    except Exception as e:
        print(f"Error generating cross-comparison plot: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error generating cross-comparison plot: {e}'}), 500

# --- New Endpoint for Downloading Processed Cross-Comparison Data as CSV ---
@app.route('/download_cross_comparison_csv', methods=['POST'])
def download_cross_comparison_csv_data():
    """
    Receives processed and filtered data from the frontend (visible points in the cross-comparison plot)
    and sends back a combined CSV file.
    """
    try:
        data_rows = request.get_json() # Expects a list of objects

        if not data_rows or not isinstance(data_rows, list) or len(data_rows) == 0:
            return jsonify({'success': False, 'message': 'No data provided for CSV export.'}), 400
        
        # Convert list of dicts to DataFrame
        df = pd.DataFrame(data_rows)

        if df.empty:
            return jsonify({'success': False, 'message': 'No data to export after processing.'}), 404

        # Convert DataFrame to CSV in memory
        csv_buffer = io.StringIO()
        # Define a specific order for columns if desired, otherwise it will be alphabetical or insertion order based on dict keys
        # For example: columns = ['Source', 'Stage', 'Parameter', 'RelativeTime', 'Value']
        # df.to_csv(csv_buffer, index=False, columns=columns) 
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        # Send the CSV data as a file download
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response = make_response(csv_buffer.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename=cross_comparison_visible_data_{timestamp}.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error creating cross-comparison CSV: {e}'}), 500

# --- New Endpoint to List All Comparison Plots ---
@app.route('/list_all_comparison_plots', methods=['GET'])
def list_all_comparison_plots():
    """Lists all available comparison plots from all report folders for cross-comparison."""
    try:
        reports_folder_abs = app.config['REPORTS_FOLDER']
        if not os.path.isdir(reports_folder_abs):
            return jsonify({'success': False, 'message': 'Reports folder not found.'}), 404

        all_comparison_plots = []
        
        # Get all report folders
        report_folders = [d for d in os.listdir(reports_folder_abs) 
                         if os.path.isdir(os.path.join(reports_folder_abs, d)) and d != 'cross_comparisons']
        
        # Check each report folder for comparison_plots
        for report_folder in report_folders:
            comparison_plots_dir = os.path.join(reports_folder_abs, report_folder, 'comparison_plots')
            if os.path.isdir(comparison_plots_dir):
                for filename in os.listdir(comparison_plots_dir):
                    if '_stages_comparison_plot_' in filename and filename.endswith('.json'):
                        # Store relative path from static folder for frontend use
                        static_folder_name = os.path.basename(app.static_folder)
                        rel_path = os.path.join(static_folder_name, 'reports', report_folder, 'comparison_plots', filename)
                        rel_path = rel_path.replace('\\', '/')
                        
                        all_comparison_plots.append({
                            'name': filename,
                            'report_folder': report_folder,
                            'path': rel_path,
                            'display_name': f"{report_folder} - {filename}"
                        })
        
        return jsonify({'success': True, 'comparison_plots': all_comparison_plots})
    except Exception as e:
        print(f"Error listing all comparison plots: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error listing all comparison plots: {e}'}), 500

# --- Routes for Report Management ---
@app.route('/rename_report', methods=['POST'])
def rename_report():
    """Renames a report folder."""
    try:
        data = request.get_json()
        old_name = data.get('old_name')
        new_name = data.get('new_name')
        
        if not old_name or not new_name:
            return jsonify({'success': False, 'message': 'Missing old or new report name.'}), 400
        
        # Sanitize input to prevent directory traversal attacks
        old_name = secure_filename(old_name)
        new_name = secure_filename(new_name)
        
        old_path = os.path.join(app.config['REPORTS_FOLDER'], old_name)
        new_path = os.path.join(app.config['REPORTS_FOLDER'], new_name)
        
        # Check if old folder exists
        if not os.path.isdir(old_path):
            return jsonify({'success': False, 'message': f'Report folder not found: {old_name}'}), 404
        
        # Check if new folder name already exists
        if os.path.exists(new_path):
            return jsonify({'success': False, 'message': f'A report with the name {new_name} already exists.'}), 409
        
        # Rename the folder
        os.rename(old_path, new_path)
        
        return jsonify({'success': True, 'message': f'Report renamed from {old_name} to {new_name}'})
    
    except Exception as e:
        print(f"Error renaming report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error renaming report: {e}'}), 500

@app.route('/delete_report', methods=['POST'])
def delete_report():
    """Deletes a report folder and all its contents."""
    try:
        data = request.get_json()
        report_name = data.get('report_name')
        
        if not report_name:
            return jsonify({'success': False, 'message': 'Missing report name.'}), 400
        
        # Sanitize input to prevent directory traversal attacks
        report_name = secure_filename(report_name)
        
        report_path = os.path.join(app.config['REPORTS_FOLDER'], report_name)
        
        # Check if folder exists
        if not os.path.isdir(report_path):
            return jsonify({'success': False, 'message': f'Report folder not found: {report_name}'}), 404
        
        # Use shutil.rmtree to remove the directory and all its contents
        import shutil
        shutil.rmtree(report_path)
        
        return jsonify({'success': True, 'message': f'Report {report_name} deleted successfully'})
    
    except Exception as e:
        print(f"Error deleting report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error deleting report: {e}'}), 500

@app.route('/list_report_contents/<report_name>', methods=['GET'])
def list_report_contents(report_name):
    """Lists the contents of a report folder."""
    try:
        # Sanitize input to prevent directory traversal attacks
        report_name = secure_filename(report_name)
        
        report_path = os.path.join(app.config['REPORTS_FOLDER'], report_name)
        
        # Check if folder exists
        if not os.path.isdir(report_path):
            return jsonify({'success': False, 'message': f'Report folder not found: {report_name}'}), 404
        
        # Function to recursively get directory structure
        def get_directory_structure(dir_path, base_path):
            items = []
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                # Get relative path for frontend use
                rel_path = os.path.relpath(item_path, base_path)
                
                if os.path.isdir(item_path):
                    # If it's a directory, recurse
                    children = get_directory_structure(item_path, base_path)
                    items.append({
                        'name': item,
                        'type': 'folder',
                        'path': rel_path.replace('\\', '/'),
                        'children': children
                    })
                else:
                    # If it's a file, add its info
                    file_size = os.path.getsize(item_path)
                    size_display = f"{file_size} bytes"
                    if file_size > 1024:
                        size_display = f"{file_size / 1024:.2f} KB"
                    if file_size > 1024 * 1024:
                        size_display = f"{file_size / (1024 * 1024):.2f} MB"
                    
                    items.append({
                        'name': item,
                        'type': 'file',
                        'path': rel_path.replace('\\', '/'),
                        'size': size_display
                    })
            
            # Sort folders first, then files
            return sorted(items, key=lambda x: (0 if x['type'] == 'folder' else 1, x['name']))
        
        # Get the directory structure
        contents = get_directory_structure(report_path, os.path.dirname(report_path))
        
        return jsonify({
            'success': True, 
            'report_name': report_name,
            'contents': contents
        })
    
    except Exception as e:
        print(f"Error listing report contents: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error listing report contents: {e}'}), 500

@app.route('/get_file_content', methods=['POST'])
def get_file_content():
    """Gets the content of a file in a report folder."""
    try:
        data = request.get_json()
        report_name = data.get('report_name')
        file_path = data.get('file_path')
        
        if not report_name or not file_path:
            return jsonify({'success': False, 'message': 'Missing report name or file path.'}), 400
        
        # Sanitize input to prevent directory traversal attacks
        report_name = secure_filename(report_name)
        
        # Construct the full path
        report_folder = os.path.join(app.config['REPORTS_FOLDER'], report_name)
        full_path = os.path.join(report_folder, file_path)
        
        # Verify the path is within the report folder
        if not os.path.abspath(full_path).startswith(os.path.abspath(report_folder)):
            return jsonify({'success': False, 'message': 'Invalid file path.'}), 403
        
        # Check if file exists
        if not os.path.isfile(full_path):
            return jsonify({'success': False, 'message': f'File not found: {file_path}'}), 404
        
        # Determine file type
        file_extension = os.path.splitext(file_path)[1].lower()
        
        # Check if it's a binary file
        binary_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.pdf']
        if file_extension in binary_extensions:
            return jsonify({
                'success': True,
                'is_binary': True,
                'file_path': file_path,
                'message': 'Binary file cannot be displayed directly.'
            })
        
        # For text-based files (JSON, CSV, TXT, etc.), read the content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return jsonify({
                'success': True,
                'is_binary': False,
                'file_path': file_path,
                'content': content
            })
        except UnicodeDecodeError:
            # If we get a unicode error, it might be a binary file
            return jsonify({
                'success': True,
                'is_binary': True,
                'file_path': file_path,
                'message': 'Binary file cannot be displayed directly.'
            })
    
    except Exception as e:
        print(f"Error getting file content: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error getting file content: {e}'}), 500

@app.route('/delete_report_file', methods=['POST'])
def delete_report_file():
    """Deletes a file from a report folder."""
    try:
        data = request.get_json()
        report_name = data.get('report_name')
        file_path = data.get('file_path')
        
        if not report_name or not file_path:
            return jsonify({'success': False, 'message': 'Missing report name or file path.'}), 400
        
        # Sanitize input to prevent directory traversal attacks
        report_name = secure_filename(report_name)
        
        # Construct the full path
        report_folder = os.path.join(app.config['REPORTS_FOLDER'], report_name)
        full_path = os.path.join(report_folder, file_path)
        
        # Verify the path is within the report folder
        if not os.path.abspath(full_path).startswith(os.path.abspath(report_folder)):
            return jsonify({'success': False, 'message': 'Invalid file path.'}), 403
        
        # Check if file exists
        if not os.path.isfile(full_path):
            return jsonify({'success': False, 'message': f'File not found: {file_path}'}), 404
        
        # Delete the file
        os.remove(full_path)
        
        return jsonify({
            'success': True,
            'message': f'File {file_path} deleted successfully.'
        })
    
    except Exception as e:
        print(f"Error deleting file: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error deleting file: {e}'}), 500

# --- Main Execution ---
if __name__ == '__main__':
    # Run the Flask development server
    # Debug=True allows for automatic reloading on code changes and provides detailed error pages
    # Use host='0.0.0.0' to make it accessible on your local network
    app.run(debug=True, host='0.0.0.0', port=5001) 