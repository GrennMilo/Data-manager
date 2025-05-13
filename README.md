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
*   **Dark Theme UI** with plots styled to match.
*   **Removed background grids** from all plots for a cleaner look.
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