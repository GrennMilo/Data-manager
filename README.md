# LV & GC Data Processing Web Interface

This project provides a web interface for processing and visualizing data from LabVIEW (LV) and Gas Chromatography (GC) text files.

## Features

*   Upload LV and GC data files (`.txt` format).
*   Processes data, merges based on timestamps, and detects experimental stages based on `RelativeTime` in the LV file.
*   Generates an overall analysis plot and CSV file combining data from both sources.
*   Generates individual plots, CSV, and JSON data files for each detected stage.
*   Provides download links for all generated plots and data files through the web interface.
*   Allows selecting specific stages to download a combined CSV of their data.
*   Interactive plots in the browser using Plotly.js.
*   **Load Previous Reports:** Users can select and reload previously processed reports from a dropdown list, restoring all plots and data links.
*   **Stage Comparison:** Within a loaded report, users can select multiple stages and generate a comparative plot showing their Temperature and NH3 data against Relative Time.
*   **Cross-Report Comparison:** 
    *   Users can select `stages_comparison_plot_*.json` files from different previously generated reports.
    *   Users can also select individual stages from the *currently loaded* report.
    *   A new combined plot is generated, overlaying traces from all selected sources (previous comparison plots and current stages).
    *   Trace names in the cross-comparison plot are prefixed with their report source (e.g., "ReportTimestamp - Stage X - Parameter" or "Current (ReportTimestamp) - Stage Y - Parameter").
    *   Cross-comparison plots are saved in a dedicated `static/reports/cross_comparisons/` subfolder.
*   Outputs are organized into timestamped folders within `static/reports/`.

## Project Structure

```
.
├── app.py                  # Flask web application
├── main_web_processor.py   # Core data processing and plotting logic
├── requirements.txt        # Python dependencies
├── uploads/                # Temporary storage for uploaded files
├── static/
│   ├── css/
│   │   └── style.css       # CSS styles
│   ├── js/
│   │   └── script.js       # Frontend JavaScript
│   └── reports/            # Output directory for generated reports (timestamped subfolders)
│       ├── <YYYYMMDD_HHMMSS>/ # Individual report run
│       │   ├── comparison_plots/ # Plots comparing stages within this run
│       │   │   └── stages_comparison_plot_<timestamp>.json
│       │   ├── step_<N>/        # Data and plot for individual stage N
│       │   │   ├── step_<N>_data.csv
│       │   │   ├── step_<N>_data.json
│       │   │   └── step_<N>_plot.json
│       │   ├── overall_merged_data.csv
│       │   └── overall_plot.json
│       └── cross_comparisons/  # Directory for cross-report comparison plots
│           └── cross_comp_<timestamp>/ # Individual cross-comparison run
│               └── cross_comparison_plot_<timestamp>.json 
├── templates/
│   └── index.html          # Main HTML template
└── README.md               # This file
```

## Setup

1.  **Install Python:**
    *   Download and install Python (version 3.8 or higher is recommended) from [python.org](https://www.python.org/downloads/).
    *   **Important:** During installation on Windows, make sure to check the box that says "Add Python to PATH". For macOS and Linux, Python is usually added to the PATH automatically, or you can do it manually if needed.

2.  **Clone the repository:**
    ```bash
    git clone https://github.com/GrennMilo/Data-manager.git
    cd Data-manager
    ```

3.  **Create a Python virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## IDE Setup (Recommended)

### Installing Cursor IDE

[Cursor](https://cursor.sh/) is a recommended IDE for this project as it provides excellent AI-assisted coding features for customizing the project in order to let them fit the User's expectations.

1. **Download Cursor:**
   * Visit [cursor.sh](https://cursor.sh/) and download the appropriate version for your operating system.
   * Install Cursor following the installation wizard instructions.

2. **Open the project in Cursor:**
   * Launch Cursor
   * Select "Open Folder" and navigate to the cloned `Data-manager` directory

### Configuring Cursor with the Virtual Environment

1. **Automatic Virtual Environment Detection:**
   * Open any Python file in the project
   * Look at the bottom right corner of the Cursor window
   * Click on the Python version indicator
   * Select the virtual environment you created (typically shows as `./venv` or similar)

2. **Terminal Integration:**
   * Open a terminal in Cursor by clicking on "Terminal" in the bottom panel or using the keyboard shortcut `` Ctrl+` `` (backtick)
   * The terminal should automatically activate the virtual environment if correctly configured
   * If not activated automatically, manually activate using the appropriate command for your OS (as mentioned in the Setup section)

3. **Using Cursor's Edit Features:**
   * Cursor provides AI-assisted editing features (Cmd+K or Ctrl+K to access the command palette)
   * Code navigation, syntax highlighting, and intelligent auto-completion are automatically enabled
   * Use the integrated terminal to run the Flask application as described in the next section

## About Virtual Environments

### Why Use a Virtual Environment?

Virtual environments are isolated Python environments that allow you to:

* **Isolate dependencies**: Each project can have its own dependencies, regardless of what other projects require
* **Version control**: Ensure consistent package versions across different development environments
* **Avoid conflicts**: Prevent package version conflicts between different projects
* **Clean deployment**: Make it easier to recreate the exact environment on different machines

The `venv` module is the standard tool for creating virtual environments in Python. When you activate the virtual environment, Python will use the packages and dependencies installed within that environment rather than those in the global Python installation.

## Running the Application

1.  **Ensure you are in the project's root directory.**
2.  **Make sure your virtual environment is activated.**
3.  **Run the Flask application:**
    ```bash
    python app.py
    ```
4.  **Open your web browser** and navigate to `http://127.0.0.1:5000` (or the address provided in the terminal, possibly using your machine's IP address if accessing from another device).

## Usage

1.  **Open the web interface** in your browser.
2.  **Process New Files:**
    *   Use the form to upload your LV data file (`.txt`) and your GC data file (`.txt`).
    *   *Note:* Ensure the files follow the expected format (tab-separated, specific header rows as handled by `main_web_processor.py`).
    *   Click "Process Files".
    *   Wait for processing to complete.
    *   View the results: Overall plot, overall CSV download, and stage-specific plots/data.
3.  **Load Previous Report:**
    *   Select a report timestamp from the "Load Previous Report" dropdown.
    *   Click "Load Selected Report".
    *   The interface will populate with the data from the selected report.
4.  **Stage-Specific Actions (after loading or processing a report):**
    *   Click stage buttons in the scrollable bar to view individual stage plots.
    *   Download individual stage CSV or JSON data using links below each stage plot.
    *   **Download Combined Stage Data:**
        *   Click stage buttons to mark them as 'selected' (they will highlight).
        *   Click the "Download Selected Stages CSV" button.
    *   **Compare Stages within Current Report:**
        *   Click multiple stage buttons to select them.
        *   Click the "Compare Selected Stages" button.
        *   A comparison plot will be displayed below the stage action buttons.
5.  **Cross-Report Comparison:**
    *   In the "Cross-Report Comparison" section, select a report folder from the first dropdown.
    *   Checkboxes for available `stages_comparison_plot_*.json` files from that folder will appear.
    *   Select desired JSON files and click "Add Selected Plot(s) to Analysis". They will be listed.
    *   Repeat for other report folders if you want to include comparison plots from multiple previous runs.
    *   Optionally, from the *currently loaded report* (if one is loaded), select individual stages by clicking their buttons in the main stage selector bar.
    *   Click "Generate Cross-Comparison Plot".
    *   A new plot combining all selected sources will appear in the "Cross-Report Comparison" section.

## File Formats

*   **LV File:** Expected to be tab-delimited (`\t`). Metadata on the first 2 lines, headers on the 3rd line, units on the 4th line. Requires `DateTime` (format `dd/mm/yy HH:MM:SS`), `RelativeTime`, `T Heater 1`, `Pressure setpoint`, `H2 Actual Flow`, `N2 Actual Flow`, `N2 poisoning set-point` columns.
*   **GC File:** Expected to be tab-delimited (`\t`) with the header on the first line. Requires `Date` (format `dd.mm.yyyy HH:MM:SS`) and `NH3` columns, plus others used in processing/plotting.

*Modify `main_web_processor.py` if your file structures or required columns differ.* 

ine 121, in _default
    raise TypeError(f"Object of type {type(o).__name__} is not JSON serializable")
TypeError: Object of type int64 is not JSON serializable
To fix this, we need to explicitly convert the num_stages to a standard Python int before it's returned to Flask.
I will modify main_web_processor.py to cast num_stages to a standard Python integer.