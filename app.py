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

# --- Context Processors ---
@app.context_processor
def inject_current_year():
    """Injects the current year into all templates."""
    return {'current_year': datetime.utcnow().year}

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
def root_redirect():
    """Redirects the base URL to the new home page."""
    from flask import redirect, url_for
    return redirect(url_for('home'))

@app.route('/home')
def home():
    """Serves the new home page for selecting a process."""
    return render_template('home.html')

@app.route('/nh3-synthesis')
def nh3_synthesis_processor():
    """ Serves the main HTML page for NH3 Synthesis data processing. """
    return render_template('nh3_snthesis_data_processing/nh3_synthesis.html')

@app.route('/meoh-synthesis')
def meoh_synthesis_processor():
    """ Placeholder for Methanol Synthesis data processing page. """
    # For now, just indicate it's coming soon. Can create a simple coming_soon.html or similar.
    return render_template('meoh_synthesis.html') # Will create this simple page

@app.route('/nh3-cracking')
def nh3_cracking_processor():
    """ Placeholder for NH3 Cracking data processing page. """
    return render_template('nh3_cracking.html') # Will create this simple page

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

# --- New Routes for Report Management --- 
@app.route('/list_report_stages/<timestamp>', methods=['GET'])
def list_report_stages(timestamp):
    """Lists all available stages for a specific report."""
    try:
        report_folder_abs = os.path.join(app.static_folder, 'reports', timestamp)
        
        if not os.path.isdir(report_folder_abs):
            return jsonify({'success': False, 'message': f'Report folder not found: {timestamp}'}), 404
        
        # Find step folders
        step_folders = glob.glob(os.path.join(report_folder_abs, 'step_*'))
        if not step_folders:
            return jsonify({'success': True, 'stages': []})
        
        # Extract stage numbers from folder names
        stage_numbers = []
        for folder in step_folders:
            try:
                stage_num = int(os.path.basename(folder).split('_')[1])
                stage_numbers.append(stage_num)
            except (IndexError, ValueError):
                print(f"Warning: Could not parse stage number from folder: {folder}")
        
        # Sort stage numbers
        stage_numbers.sort()
        
        return jsonify({'success': True, 'stages': stage_numbers})
    
    except Exception as e:
        print(f"Error listing stages for report {timestamp}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error listing stages: {e}'}), 500

@app.route('/delete_report', methods=['POST'])
def delete_report():
    """Deletes an entire report folder."""
    try:
        data = request.get_json()
        report_timestamp = data.get('report_timestamp')
        
        if not report_timestamp:
            return jsonify({'success': False, 'message': 'Missing report timestamp.'}), 400
        
        report_folder_abs = os.path.join(app.static_folder, 'reports', report_timestamp)
        
        if not os.path.isdir(report_folder_abs):
            return jsonify({'success': False, 'message': f'Report folder not found: {report_timestamp}'}), 404
        
        # Security check - ensure the path is within the reports directory
        if not os.path.normpath(report_folder_abs).startswith(os.path.normpath(app.config['REPORTS_FOLDER'])):
            return jsonify({'success': False, 'message': 'Security error: Invalid path.'}), 403
        
        # Recursively delete the folder
        import shutil
        shutil.rmtree(report_folder_abs)
        
        return jsonify({
            'success': True, 
            'message': f'Report {report_timestamp} has been deleted.'
        })
    
    except Exception as e:
        print(f"Error deleting report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error deleting report: {e}'}), 500

@app.route('/delete_stages', methods=['POST'])
def delete_stages():
    """Deletes specific stages from a report and regenerates the overall files."""
    try:
        data = request.get_json()
        report_timestamp = data.get('report_timestamp')
        stage_numbers = data.get('stage_numbers')
        
        if not report_timestamp or not stage_numbers:
            return jsonify({'success': False, 'message': 'Missing report timestamp or stage numbers.'}), 400
        
        # Convert stage numbers to integers if they're strings
        stage_numbers = [int(s) for s in stage_numbers]
        
        report_folder_abs = os.path.join(app.static_folder, 'reports', report_timestamp)
        
        if not os.path.isdir(report_folder_abs):
            return jsonify({'success': False, 'message': f'Report folder not found: {report_timestamp}'}), 404
        
        # Delete each stage folder
        deleted_stages = []
        for stage_num in stage_numbers:
            stage_folder = os.path.join(report_folder_abs, f'step_{stage_num}')
            if os.path.isdir(stage_folder):
                # Security check - ensure the path is within the reports directory
                if not os.path.normpath(stage_folder).startswith(os.path.normpath(app.config['REPORTS_FOLDER'])):
                    return jsonify({'success': False, 'message': f'Security error: Invalid path for stage {stage_num}.'}), 403
                
                # Delete the stage folder
                import shutil
                shutil.rmtree(stage_folder)
                deleted_stages.append(stage_num)
            else:
                print(f"Warning: Stage folder not found: {stage_folder}")
        
        if not deleted_stages:
            return jsonify({'success': False, 'message': 'No stages were deleted.'}), 404
        
        # TODO: Regenerate overall files if needed
        # This would involve reading remaining stage data and creating a new overall plot
        # For now, we'll leave the overall files as they are
        
        return jsonify({
            'success': True, 
            'message': f'Deleted {len(deleted_stages)} stages from report {report_timestamp}.',
            'deleted_stages': deleted_stages
        })
    
    except Exception as e:
        print(f"Error deleting stages: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error deleting stages: {e}'}), 500

@app.route('/add_data_to_report', methods=['POST'])
def add_data_to_report():
    """Adds new data to an existing report, either as a new stage or adding points to an existing stage."""
    try:
        # Get form data
        report_timestamp = request.form.get('report_timestamp')
        add_data_type = request.form.get('add_data_type')
        
        if not report_timestamp or not add_data_type:
            return jsonify({'success': False, 'message': 'Missing report timestamp or data type.'}), 400
        
        report_folder_abs = os.path.join(app.static_folder, 'reports', report_timestamp)
        
        if not os.path.isdir(report_folder_abs):
            return jsonify({'success': False, 'message': f'Report folder not found: {report_timestamp}'}), 404
        
        # Handle file uploads
        if add_data_type == 'new_stage':
            # Check if files are provided
            if 'new_stage_lv_file' not in request.files or 'new_stage_gc_file' not in request.files:
                return jsonify({'success': False, 'message': 'Missing LV or GC file in request.'}), 400
            
            lv_file = request.files['new_stage_lv_file']
            gc_file = request.files['new_stage_gc_file']
            
            if lv_file.filename == '' or gc_file.filename == '':
                return jsonify({'success': False, 'message': 'No selected file(s).'}), 400
            
            if not (allowed_file(lv_file.filename) and allowed_file(gc_file.filename)):
                return jsonify({'success': False, 'message': 'Invalid file type.'}), 400
            
            # Determine new stage number
            requested_stage_num = request.form.get('new_stage_number')
            new_stage_num = None
            
            if requested_stage_num:
                try:
                    new_stage_num = int(requested_stage_num)
                    # Check if stage already exists
                    if os.path.exists(os.path.join(report_folder_abs, f'step_{new_stage_num}')):
                        return jsonify({'success': False, 'message': f'Stage {new_stage_num} already exists in this report.'}), 400
                except ValueError:
                    return jsonify({'success': False, 'message': 'Invalid stage number.'}), 400
            else:
                # Find max existing stage number and increment
                existing_stages = glob.glob(os.path.join(report_folder_abs, 'step_*'))
                stage_nums = []
                for stage_folder in existing_stages:
                    try:
                        stage_nums.append(int(os.path.basename(stage_folder).split('_')[1]))
                    except (IndexError, ValueError):
                        pass
                
                new_stage_num = max(stage_nums) + 1 if stage_nums else 1
            
            # Save uploaded files temporarily
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
            
            # Process LV and GC files for the new stage
            # This would involve calling functions from main_web_processor
            # For now, we'll create a placeholder
            try:
                # Create new stage folder
                new_stage_dir = os.path.join(report_folder_abs, f'step_{new_stage_num}')
                os.makedirs(new_stage_dir, exist_ok=True)
                
                # TODO: Process the data and create the plot
                # For a real implementation, you would:
                # 1. Process the LV and GC files
                # 2. Merge the data
                # 3. Create the plot and save as JSON
                # 4. Save the CSV and JSON data
                
                # For now, let's just create placeholder files to demonstrate
                with open(os.path.join(new_stage_dir, f'step_{new_stage_num}_data.csv'), 'w') as f:
                    f.write(f"Placeholder for stage {new_stage_num} CSV data")
                
                with open(os.path.join(new_stage_dir, f'step_{new_stage_num}_data.json'), 'w') as f:
                    f.write(f"{{\"placeholder\": \"stage {new_stage_num} JSON data\"}}")
                
                with open(os.path.join(new_stage_dir, f'step_{new_stage_num}_plot.json'), 'w') as f:
                    f.write(f"{{\"placeholder\": \"stage {new_stage_num} plot data\"}}")
                
                return jsonify({
                    'success': True,
                    'message': f'Added new stage {new_stage_num} to report {report_timestamp}.',
                    'stage_number': new_stage_num
                })
                
            except Exception as e:
                print(f"Error processing files for new stage: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'message': f'Error processing files: {e}'}), 500
                
            finally:
                # Clean up temporary files
                try:
                    os.remove(lv_filepath)
                    os.remove(gc_filepath)
                except:
                    pass
                
        elif add_data_type == 'new_points':
            # Check if files and stage are provided
            if 'add_points_lv_file' not in request.files or 'add_points_gc_file' not in request.files:
                return jsonify({'success': False, 'message': 'Missing LV or GC file in request.'}), 400
            
            existing_stage = request.form.get('existing_stage')
            if not existing_stage:
                return jsonify({'success': False, 'message': 'Missing existing stage number.'}), 400
            
            try:
                existing_stage_num = int(existing_stage)
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid stage number.'}), 400
            
            stage_dir = os.path.join(report_folder_abs, f'step_{existing_stage_num}')
            if not os.path.isdir(stage_dir):
                return jsonify({'success': False, 'message': f'Stage {existing_stage_num} not found in report {report_timestamp}.'}), 404
            
            lv_file = request.files['add_points_lv_file']
            gc_file = request.files['add_points_gc_file']
            
            if lv_file.filename == '' or gc_file.filename == '':
                return jsonify({'success': False, 'message': 'No selected file(s).'}), 400
            
            if not (allowed_file(lv_file.filename) and allowed_file(gc_file.filename)):
                return jsonify({'success': False, 'message': 'Invalid file type.'}), 400
            
            # Save uploaded files temporarily
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
            
            # Process the files and add data to existing stage
            try:
                # TODO: Process the data and update the existing files
                # For a real implementation, you would:
                # 1. Read the existing stage data
                # 2. Process the new LV and GC files
                # 3. Merge all data
                # 4. Create updated plot and save as JSON
                # 5. Save the updated CSV and JSON data
                
                # For now, let's just modify the existing files to demonstrate
                csv_file = os.path.join(stage_dir, f'step_{existing_stage_num}_data.csv')
                if os.path.exists(csv_file):
                    with open(csv_file, 'a') as f:
                        f.write("\n# New data points added")
                
                json_file = os.path.join(stage_dir, f'step_{existing_stage_num}_data.json')
                if os.path.exists(json_file):
                    with open(json_file, 'r+') as f:
                        content = f.read().rstrip('\n}')
                        f.seek(0)
                        f.truncate()
                        f.write(content + ', "new_points_added": true}')
                
                plot_file = os.path.join(stage_dir, f'step_{existing_stage_num}_plot.json')
                if os.path.exists(plot_file):
                    with open(plot_file, 'r+') as f:
                        content = f.read().rstrip('\n}')
                        f.seek(0)
                        f.truncate()
                        f.write(content + ', "new_points_added": true}')
                
                return jsonify({
                    'success': True,
                    'message': f'Added new data points to stage {existing_stage_num} in report {report_timestamp}.',
                    'stage_number': existing_stage_num
                })
                
            except Exception as e:
                print(f"Error processing files for adding points: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({'success': False, 'message': f'Error processing files: {e}'}), 500
                
            finally:
                # Clean up temporary files
                try:
                    os.remove(lv_filepath)
                    os.remove(gc_filepath)
                except:
                    pass
        
        else:
            return jsonify({'success': False, 'message': f'Unknown data type: {add_data_type}'}), 400
    
    except Exception as e:
        print(f"Error adding data to report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error adding data to report: {e}'}), 500

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
        selected_json_rel_paths = data.get('selected_comparison_json_paths') # e.g. ["static/reports/TS1/comp_plots/file.json", ...]
        current_report_ts = data.get('current_report_timestamp')
        current_selected_stages = data.get('current_report_selected_stages')

        if not selected_json_rel_paths and not (current_report_ts and current_selected_stages):
            return jsonify({'success': False, 'message': 'No data sources provided for cross-comparison.'}), 400

        base_dir = os.path.dirname(os.path.abspath(__file__)) # Project root
        static_reports_folder_abs = os.path.join(base_dir, app.static_folder, 'reports') # Absolute path to static/reports

        absolute_selected_json_paths = []
        if selected_json_rel_paths:
            for rel_path in selected_json_rel_paths:
                # rel_path is like "static/reports/TIMESTAMP/comparison_plots/FILENAME.json"
                # We need path from project root. os.path.join will handle this if base_dir is project root.
                abs_path = os.path.normpath(os.path.join(base_dir, rel_path))
                # Security check: ensure it's within the static_reports_folder_abs
                if not abs_path.startswith(static_reports_folder_abs):
                    print(f"Security Warning: Attempt to access path outside allowed reports directory: {rel_path}")
                    # Optionally skip or return an error
                    continue 
                if os.path.exists(abs_path):
                    absolute_selected_json_paths.append(abs_path)
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

# --- New Route for Updating Existing Reports ---
@app.route('/update_report', methods=['POST'])
def update_report():
    """Updates an existing report by completely reprocessing the LV and GC files while preserving the folder."""
    try:
        # Get form data
        report_timestamp = request.form.get('report_timestamp')
        
        if not report_timestamp:
            return jsonify({'success': False, 'message': 'Missing report timestamp.'}), 400
        
        report_folder_abs = os.path.join(app.static_folder, 'reports', report_timestamp)
        
        if not os.path.isdir(report_folder_abs):
            return jsonify({'success': False, 'message': f'Report folder not found: {report_timestamp}'}), 404
        
        # Check if files are provided
        if 'lv_file' not in request.files or 'gc_file' not in request.files:
            return jsonify({'success': False, 'message': 'Missing LV or GC file in request.'}), 400
        
        lv_file = request.files['lv_file']
        gc_file = request.files['gc_file']
        
        if lv_file.filename == '' or gc_file.filename == '':
            return jsonify({'success': False, 'message': 'No selected file(s).'}), 400
        
        if not (allowed_file(lv_file.filename) and allowed_file(gc_file.filename)):
            return jsonify({'success': False, 'message': 'Invalid file type.'}), 400
        
        # Save uploaded files temporarily
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
        
        try:
            # First, backup the existing report folder in case of processing failure
            backup_folder = os.path.join(app.config['UPLOAD_FOLDER'], f"{report_timestamp}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            import shutil
            shutil.copytree(report_folder_abs, backup_folder)
            print(f"Created backup of report folder at: {backup_folder}")
            
            # Clear out the existing report folder contents
            for item in os.listdir(report_folder_abs):
                item_path = os.path.join(report_folder_abs, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            
            # Process the files using the same function as for new reports
            # The base output directory should be the parent of the report folder
            results = main_web_processor.generate_reports(
                lv_filepath,
                gc_filepath,
                os.path.dirname(report_folder_abs),  # parent directory of the report folder
                report_prefix_text=report_timestamp  # use the existing timestamp as prefix to ensure same folder
            )
            
            if not results.get('success'):
                # If processing failed, restore from backup
                shutil.rmtree(report_folder_abs)
                shutil.move(backup_folder, report_folder_abs)
                print(f"Processing failed, restored from backup: {backup_folder}")
                return jsonify({'success': False, 'message': f'Error processing files: {results.get("message", "Unknown error")}'}), 500
            
            # Cleanup backup if successful
            shutil.rmtree(backup_folder)
            print(f"Processing successful, removed backup: {backup_folder}")
            
            return jsonify({
                'success': True,
                'message': f'Report {report_timestamp} has been updated successfully.',
                'num_stages': results.get('num_stages', 0)
            })
            
        except Exception as e:
            print(f"Error processing files for report update: {e}")
            import traceback
            traceback.print_exc()
            
            # Attempt to restore from backup if it exists
            if os.path.exists(backup_folder):
                try:
                    shutil.rmtree(report_folder_abs)
                    shutil.move(backup_folder, report_folder_abs)
                    print(f"Restored from backup after error: {backup_folder}")
                except Exception as restore_error:
                    print(f"Error restoring from backup: {restore_error}")
            
            return jsonify({'success': False, 'message': f'Error updating report: {e}'}), 500
            
        finally:
            # Clean up temporary files
            try:
                os.remove(lv_filepath)
                os.remove(gc_filepath)
            except:
                pass
    
    except Exception as e:
        print(f"Error updating report: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error updating report: {e}'}), 500

# --- Main Execution ---
if __name__ == '__main__':
    # Run the Flask development server
    # Debug=True allows for automatic reloading on code changes and provides detailed error pages
    # Use host='0.0.0.0' to make it accessible on your local network
    app.run(debug=True, host='0.0.0.0', port=5001) 