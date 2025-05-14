// Wrap the main logic in a DOMContentLoaded listener to ensure the HTML is ready
document.addEventListener('DOMContentLoaded', () => {

    // --- Global Variables ---
    let currentRunData = { // Stores data for the currently displayed report
        overall_plot_path: null,
        overall_csv_path: null,
        step_reports: [], // [{step_number, plot_path, csv_path, json_path}, ...]
        num_stages: 0,
        timestamp_prefix: null 
    };

    // --- Element References ---
    const uploadForm = document.getElementById('upload-form');
    const uploadStatusMessage = document.getElementById('upload-status-message');
    const loadingIndicator = document.getElementById('loading-indicator');
    const resultsDiv = document.getElementById('results');
    const resultsTimestampSpan = document.getElementById('results-timestamp');
    const overallPlotDiv = document.getElementById('overall-plot-div');
    const overallDataContainer = document.getElementById('overall-data-container');
    const stageSelectorScrollContainer = document.getElementById('stage-selector-scroll-container');
    const stageSelectorItems = document.getElementById('stage-selector-items');
    const stageProcessingSection = document.getElementById('stage-processing-section');
    const downloadSelectedButton = document.getElementById('download-selected-stages-button');
    const stepReportsContainer = document.getElementById('step-reports');

    // Previous Report Loading Elements
    const reportSelect = document.getElementById('report-select');
    const loadReportButton = document.getElementById('load-report-button');
    const loadStatusMessage = document.getElementById('load-status-message');

    // Comparison Elements
    const compareStagesButton = document.getElementById('compare-stages-button');
    const comparisonReportDiv = document.getElementById('comparison-report');
    const comparisonPlotDiv = document.getElementById('comparison-plot-div');

    // --- Cross-Report Comparison Elements ---
    const crossReportFolderSelect = document.getElementById('cross-report-folder-select');
    const crossReportJsonOptionsDiv = document.getElementById('cross-report-json-options');
    const addSelectedCrossJsonButton = document.getElementById('add-selected-cross-json-button');
    const selectedCrossJsonListUl = document.getElementById('selected-cross-json-list');
    const generateCrossComparisonButton = document.getElementById('generate-cross-comparison-button');
    const crossComparisonStatusMessage = document.getElementById('cross-comparison-status-message');
    const crossComparisonPlotDiv = document.getElementById('cross-comparison-plot-div');

    // --- Global Variables for Cross-Report Comparison ---
    let selectedCrossReportJsonPaths = []; // Stores full paths for backend

    // --- Initial Setup ---
    fetchAndPopulateReportList();
    fetchAndPopulateCrossReportFolderList(); // New function to populate the cross-report folder selector

    // --- Event Listeners ---
    uploadForm.addEventListener('submit', handleUploadSubmit);
    loadReportButton.addEventListener('click', handleLoadReportClick);
    downloadSelectedButton.addEventListener('click', handleDownloadSelectedClick);
    compareStagesButton.addEventListener('click', handleCompareStagesClick); 

    // New Event Listeners for Cross-Report Comparison
    crossReportFolderSelect.addEventListener('change', handleCrossReportFolderSelectChange);
    addSelectedCrossJsonButton.addEventListener('click', handleAddSelectedCrossJson);
    generateCrossComparisonButton.addEventListener('click', handleGenerateCrossComparison);

    // --- Function Definitions ---

    // Function to fetch the list of reports and populate the dropdown
    function fetchAndPopulateReportList() {
        fetch('/list_reports')
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch report list');
                return response.json();
            })
            .then(data => {
                if (data.success && data.reports && data.reports.length > 0) {
                    reportSelect.innerHTML = '<option value="">Select a report...</option>'; // Clear loading message
                    data.reports.forEach(timestamp => {
                        const option = document.createElement('option');
                        option.value = timestamp;
                        option.textContent = timestamp; // Display timestamp (can format later if needed)
                        reportSelect.appendChild(option);
                    });
                } else {
                    reportSelect.innerHTML = '<option value="">No reports found</option>';
                    if (!data.success) throw new Error(data.message || 'Failed to load reports');
                }
            })
            .catch(error => {
                console.error('Error fetching report list:', error);
                reportSelect.innerHTML = '<option value="">Error loading reports</option>';
                loadStatusMessage.textContent = `Error: ${error.message}`;
                loadStatusMessage.className = 'status-error';
            });
    }

    // Handler for the "Load Selected Report" button click
    function handleLoadReportClick() {
        const selectedTimestamp = reportSelect.value;
        if (!selectedTimestamp) {
            loadStatusMessage.textContent = 'Please select a report to load.';
            loadStatusMessage.className = 'status-error';
            return;
        }

        // Reset UI elements before loading
        resetResultsUI();
        loadStatusMessage.textContent = `Loading report ${selectedTimestamp}...`;
        loadStatusMessage.className = '';
        loadingIndicator.style.display = 'block'; // Show loading indicator

        fetch(`/load_report/${selectedTimestamp}`)
            .then(response => {
                if (!response.ok) {
                     return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); })
                           .catch(() => { throw new Error(`Server error loading report: ${response.status}`); });
                }
                return response.json();
            })
            .then(data => {
                loadingIndicator.style.display = 'none';
                if (data.success) {
                    loadStatusMessage.textContent = data.message || `Report ${selectedTimestamp} loaded successfully.`;
                    loadStatusMessage.className = 'status-success';
                    displayResults(data); // Call the common function to display results
                } else {
                    throw new Error(data.message || 'Failed to load report data.');
                }
            })
            .catch(error => {
                loadingIndicator.style.display = 'none';
                console.error(`Error loading report ${selectedTimestamp}:`, error);
                loadStatusMessage.textContent = `Error loading report: ${error.message}`;
                loadStatusMessage.className = 'status-error';
                resetResultsUI(); // Clear results area on error
            });
    }

    // Handler for the file upload form submission
    function handleUploadSubmit(event) {
        event.preventDefault(); 
        const formData = new FormData(event.target);
        
        // Reset UI elements before processing
        resetResultsUI();
        uploadStatusMessage.textContent = '';
        uploadStatusMessage.className = '';
        loadingIndicator.style.display = 'block';

        fetch('/process', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); })
                               .catch(() => { throw new Error(`Server error: ${response.status}`); });
            }
            return response.json();
        })
        .then(data => {
            loadingIndicator.style.display = 'none';
            if (data.success) {
                uploadStatusMessage.textContent = data.message || 'Processing successful!';
                uploadStatusMessage.className = 'status-success';
                displayResults(data); // Call the common display function
                fetchAndPopulateReportList(); // Refresh report list after successful upload
            } else {
                 throw new Error(data.message || 'Processing failed.');
            }
        })
        .catch(error => {
            loadingIndicator.style.display = 'none';
            uploadStatusMessage.textContent = 'Error: ' + error.message;
            uploadStatusMessage.className = 'status-error';
            console.error('Error during fetch /process:', error);
            resetResultsUI();
        });
    }

    // Common function to reset the results display area
    function resetResultsUI() {
        resultsDiv.style.display = 'none';
        resultsTimestampSpan.textContent = '';
        overallPlotDiv.innerHTML = ''; 
        overallDataContainer.innerHTML = '';
        stageSelectorScrollContainer.style.display = 'none'; 
        stageSelectorItems.innerHTML = ''; 
        stageProcessingSection.style.display = 'none';
        stepReportsContainer.innerHTML = '<p>Click a stage button in the scroll bar above to load its plot here.</p>'; 
        currentRunData = { step_reports: [], num_stages: 0 }; // Reset global data
    }

    // Common function to display results (used by both upload and load)
    function displayResults(data) {
        // Store data globally
        currentRunData = data;

        resultsDiv.style.display = 'block';
        resultsTimestampSpan.textContent = data.timestamp_prefix ? `(${data.timestamp_prefix})` : '';

        // Render overall Plotly plot
        if (data.overall_plot_path) {
            fetchAndRenderPlotly(data.overall_plot_path, overallPlotDiv);
        } else {
             overallPlotDiv.innerHTML = '<p>Overall plot not available.</p>';
        }

        // Link to overall CSV
        overallDataContainer.innerHTML = ''; // Clear previous link
        if (data.overall_csv_path) {
            const link = document.createElement('a');
            link.href = '/' + data.overall_csv_path; // Path is already relative to static
            link.textContent = 'Download Overall Data (CSV)';
            link.target = '_blank';
            overallDataContainer.appendChild(link);
        }

        // Populate stage selection scroll bar if stages exist
        stageSelectorItems.innerHTML = ''; // Clear previous buttons
        if (data.num_stages && data.num_stages > 0 && data.step_reports.length > 0) {
            stageSelectorScrollContainer.style.display = 'block';
            stageProcessingSection.style.display = 'block';
            
            data.step_reports.forEach(step => {
                const button = document.createElement('button');
                button.type = 'button'; 
                button.className = 'stage-selector-button';
                button.textContent = `Stage ${step.step_number}`;
                button.value = step.step_number;
                button.dataset.plotPath = step.plot_path || 'None';
                button.dataset.csvPath = step.csv_path || 'None';
                button.dataset.jsonPath = step.json_path || 'None';
                button.addEventListener('click', handleStageButtonClick); 
                stageSelectorItems.appendChild(button);
            });
        } else {
            stageSelectorScrollContainer.style.display = 'none';
            stageProcessingSection.style.display = 'none';
        }
        // Ensure the step report area is reset
        stepReportsContainer.innerHTML = '<p>Click a stage button in the scroll bar above to load its plot here.</p>';
    }


    // --- Handler for Stage Button Clicks ---
    function handleStageButtonClick(event) {
        const button = event.target;
        const stepNum = button.value;
        const plotPath = button.dataset.plotPath;
        
        // Toggle 'selected' class for download/comparison functionality
        button.classList.toggle('selected');

        // Clear previous step plot and show the clicked one
        stepReportsContainer.innerHTML = ''; // Clear previous content

        if (plotPath && plotPath !== 'None') {
            const stepReportDiv = document.createElement('div');
            stepReportDiv.className = 'step-report';

            const title = document.createElement('h4');
            title.textContent = `Stage ${stepNum} Analysis`;
            stepReportDiv.appendChild(title);

            const plotDiv = document.createElement('div');
            plotDiv.id = `step-plot-div-${stepNum}`;
            plotDiv.className = 'plotly-plot-container step-plot-container';
            stepReportDiv.appendChild(plotDiv);

            fetchAndRenderPlotly(plotPath, plotDiv);

            // Add individual download links
            addIndividualStageDownloadLinks(stepReportDiv, button.dataset.csvPath, button.dataset.jsonPath);

            stepReportsContainer.appendChild(stepReportDiv);
        } else {
            stepReportsContainer.innerHTML = `<p>Plot not available for Stage ${stepNum}.</p>`;
        }
    }

    // Helper to add individual download links below a stage plot
    function addIndividualStageDownloadLinks(container, csvPath, jsonPath) {
         const linksContainer = document.createElement('div');
         linksContainer.className = 'step-links'; 
         linksContainer.style.marginTop = '10px';

         if (csvPath && csvPath !== 'None') {
             const csvLink = document.createElement('a');
             csvLink.href = '/' + csvPath;
             csvLink.textContent = 'Download Stage Data (CSV)';
             csvLink.target = '_blank';
             linksContainer.appendChild(csvLink);
             if (jsonPath && jsonPath !== 'None') linksContainer.appendChild(document.createTextNode(' | '));
         }
         if (jsonPath && jsonPath !== 'None') {
             const jsonLink = document.createElement('a');
             jsonLink.href = '/' + jsonPath;
             jsonLink.textContent = 'Download Stage Data (JSON)';
             jsonLink.target = '_blank';
             linksContainer.appendChild(jsonLink);
         }
         if (linksContainer.hasChildNodes()) {
             container.appendChild(linksContainer);
         }
    }

    // Helper function to fetch and render Plotly JSON
    function fetchAndRenderPlotly(plotJsonPath, targetDivElement) {
        targetDivElement.innerHTML = 'Loading plot...'; 
        fetch('/' + plotJsonPath)
            .then(response => {
                if (!response.ok) throw new Error(`Failed to fetch plot data: ${response.status} ${response.statusText} for ${plotJsonPath}`);
                return response.json();
            })
            .then(plotData => {
                // Apply dark theme dynamically
                if (!plotData.layout) plotData.layout = {};
                plotData.layout.paper_bgcolor = '#2c2c2c'; 
                plotData.layout.plot_bgcolor = '#383838';  
                plotData.layout.font = { color: '#e0e0e0' }; 
                
                for (const key in plotData.layout) {
                     if (key.startsWith('xaxis') || key.startsWith('yaxis')) {
                         if(!plotData.layout[key]) plotData.layout[key] = {}; // Ensure axis object exists
                         plotData.layout[key].gridcolor = 'rgba(0,0,0,0)';
                         plotData.layout[key].linecolor = '#5a5a5a'; 
                         plotData.layout[key].zerolinecolor = '#5a5a5a'; 
                     }
                }
                if (plotData.layout.legend) {
                    if(!plotData.layout.legend) plotData.layout.legend = {}; // Ensure legend object exists
                    plotData.layout.legend.bgcolor = '#383838';
                    plotData.layout.legend.bordercolor = '#4a4a4a';
                    plotData.layout.legend.font = { color: '#e0e0e0' };
                }

                Plotly.newPlot(targetDivElement, plotData.data, plotData.layout, {responsive: true});
            })
            .catch(error => {
                console.error(`Error fetching/plotting for ${plotJsonPath}:`, error);
                targetDivElement.textContent = `Error loading plot: ${error.message}`;
                targetDivElement.style.color = '#f8d7da';
            });
    }

    // --- Event Listener for "Download Selected Stages CSV" Button ---
    function handleDownloadSelectedClick() {
        // Find buttons with 'selected' class (now only one should be selected for viewing, but keep logic flexible)
        const selectedButtons = document.querySelectorAll('.stage-selector-button.selected');
        const selectedJsonFilePaths = []; 

        selectedButtons.forEach(button => {
            if (button.dataset.jsonPath && button.dataset.jsonPath !== 'None') {
                selectedJsonFilePaths.push(button.dataset.jsonPath);
            }
        });

        if (selectedJsonFilePaths.length === 0) {
            // Use the appropriate status message area depending on context if needed
            // For now, use the main one or alert
            alert('Please select at least one stage (click its button in the scroll bar) to include in the download.');
            return;
        }

        // Use upload status message area for feedback for now
        uploadStatusMessage.textContent = 'Preparing selected stages CSV...';
        uploadStatusMessage.className = ''; 

        fetch('/download_selected_stages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ json_paths: selectedJsonFilePaths }) 
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); })
                               .catch(() => { throw new Error(`Server error preparing download: ${response.status}`); });
            }
            const disposition = response.headers.get('Content-Disposition');
            let filename = `selected_stages_data_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
            if (disposition && disposition.indexOf('attachment') !== -1) {
                const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                const matches = filenameRegex.exec(disposition);
                if (matches != null && matches[1]) { 
                  filename = matches[1].replace(/['"]/g, '');
                }
            }
            return response.blob().then(blob => ({ blob, filename })); 
        })
        .then(({ blob, filename }) => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename; 
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            uploadStatusMessage.textContent = 'Selected stages CSV downloaded.';
            uploadStatusMessage.className = 'status-success';
        })
        .catch(error => {
            uploadStatusMessage.textContent = 'Error preparing download: ' + error.message;
            uploadStatusMessage.className = 'status-error';
            console.error('Error during fetch /download_selected_stages:', error);
        });
    } 

    // --- Event Listener for "Compare Selected Stages" Button ---
    function handleCompareStagesClick() {
        const selectedButtons = stageSelectorItems.querySelectorAll('.stage-selector-button.selected');
        const selectedStageNumbers = [];
        
        selectedButtons.forEach(button => {
            selectedStageNumbers.push(parseInt(button.value, 10)); // Get stage numbers
        });

        if (selectedStageNumbers.length < 2) {
            alert('Please select at least two stages to compare.');
            return;
        }

        if (!currentRunData.timestamp_prefix) {
             alert('Could not determine the report timestamp. Please load a report first.');
             return;
        }

        // Show loading state for comparison
        comparisonReportDiv.style.display = 'block';
        comparisonPlotDiv.innerHTML = 'Generating comparison plot...';
        // Optionally use main loading indicator or a specific one
        // loadingIndicator.style.display = 'block'; 

        fetch('/compare_stages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                timestamp: currentRunData.timestamp_prefix, 
                stages: selectedStageNumbers 
            })
        })
        .then(response => {
            // loadingIndicator.style.display = 'none';
            if (!response.ok) {
                 return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); })
                               .catch(() => { throw new Error(`Server error comparing stages: ${response.status}`); });
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.comparison_plot_path) {
                comparisonPlotDiv.innerHTML = ''; // Clear loading message
                fetchAndRenderPlotly(data.comparison_plot_path, comparisonPlotDiv);
                 // Optionally display a success message somewhere
            } else {
                throw new Error(data.message || 'Failed to generate comparison plot.');
            }
        })
        .catch(error => {
            // loadingIndicator.style.display = 'none';
            console.error('Error during stage comparison:', error);
            comparisonPlotDiv.innerHTML = `<p class="status-error">Error generating comparison plot: ${error.message}</p>`;
        });
    }

    // --- New Functions for Cross-Report Comparison ---

    // Function to populate the cross-report folder selector
    function fetchAndPopulateCrossReportFolderList() {
        fetch('/list_reports') // Reuse existing endpoint
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch report list for cross-comparison');
                return response.json();
            })
            .then(data => {
                if (data.success && data.reports && data.reports.length > 0) {
                    crossReportFolderSelect.innerHTML = '<option value="">Select a report folder...</option>';
                    data.reports.forEach(timestamp => {
                        const option = document.createElement('option');
                        option.value = timestamp;
                        option.textContent = timestamp;
                        crossReportFolderSelect.appendChild(option);
                    });
                } else {
                    crossReportFolderSelect.innerHTML = '<option value="">No report folders found</option>';
                    if (!data.success) throw new Error(data.message || 'Failed to load report folders');
                }
            })
            .catch(error => {
                console.error('Error fetching report list for cross-comparison:', error);
                crossReportFolderSelect.innerHTML = '<option value="">Error loading report folders</option>';
                // Optionally display error in crossComparisonStatusMessage
            });
    }

    // Handler for when a report folder is selected in the cross-report section
    function handleCrossReportFolderSelectChange() {
        const selectedTimestamp = crossReportFolderSelect.value;
        crossReportJsonOptionsDiv.innerHTML = ''; // Clear previous options
        if (!selectedTimestamp) {
            return;
        }

        fetch(`/list_comparison_plots/${selectedTimestamp}`)
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch comparison plots for the selected folder.');
                return response.json();
            })
            .then(data => {
                if (data.success && data.comparison_plots && data.comparison_plots.length > 0) {
                    data.comparison_plots.forEach(plotFile => {
                        // plotFile is expected to be like "comparison_plots/stages_comparison_plot_XXXX.json"
                        // We need the full path relative to static/reports/<timestamp>/ for display and selection
                        const fullPlotPath = `static/reports/${selectedTimestamp}/${plotFile.path}`; 
                        const checkboxId = `cross-plot-${selectedTimestamp}-${plotFile.name.replace(/\.|\s/g, '-')}`; // Create unique ID

                        const div = document.createElement('div');
                        const checkbox = document.createElement('input');
                        checkbox.type = 'checkbox';
                        checkbox.id = checkboxId;
                        checkbox.value = fullPlotPath; // Store the full path for backend
                        checkbox.name = 'crossReportJsonFile';

                        const label = document.createElement('label');
                        label.htmlFor = checkboxId;
                        label.textContent = plotFile.name; // Display just the filename

                        div.appendChild(checkbox);
                        div.appendChild(label);
                        crossReportJsonOptionsDiv.appendChild(div);
                    });
                } else {
                    crossReportJsonOptionsDiv.innerHTML = '<p>No comparison plots found in this folder.</p>';
                    if (!data.success && data.message) throw new Error(data.message);
                }
            })
            .catch(error => {
                console.error('Error fetching comparison plots:', error);
                crossReportJsonOptionsDiv.innerHTML = `<p class="status-error">Error: ${error.message}</p>`;
            });
    }

    // Handler for "Add Selected Plot(s) to Analysis" button
    function handleAddSelectedCrossJson() {
        const selectedCheckboxes = crossReportJsonOptionsDiv.querySelectorAll('input[name="crossReportJsonFile"]:checked');
        let newFilesAdded = false;
        selectedCheckboxes.forEach(checkbox => {
            if (!selectedCrossReportJsonPaths.includes(checkbox.value)) {
                selectedCrossReportJsonPaths.push(checkbox.value); // Add full path
                
                const listItem = document.createElement('li');
                // Display a more user-friendly name, e.g., "Report_Timestamp / filename.json"
                // checkbox.value is like "static/reports/TIMESTAMP/comparison_plots/FILENAME.json"
                const pathParts = checkbox.value.split('/');
                const displayName = pathParts.slice(2).join('/'); // e.g., TIMESTAMP/comparison_plots/FILENAME.json

                listItem.textContent = displayName;
                listItem.dataset.path = checkbox.value; // Store full path for potential removal
                selectedCrossJsonListUl.appendChild(listItem);
                newFilesAdded = true;
            }
            checkbox.checked = false; // Uncheck after adding
        });

        if (!newFilesAdded && selectedCheckboxes.length > 0) {
            alert("The selected plot(s) are already in the list for cross-comparison.");
        } else if (selectedCheckboxes.length === 0) {
            alert("Please select one or more comparison plots to add.");
        }
    }

    // Handler for "Generate Cross-Comparison Plot" button
    function handleGenerateCrossComparison() {
        const selectedStageButtons = stageSelectorItems.querySelectorAll('.stage-selector-button.selected');
        const currentReportSelectedStages = [];
        selectedStageButtons.forEach(button => {
            currentReportSelectedStages.push(parseInt(button.value, 10));
        });

        if (selectedCrossReportJsonPaths.length === 0 && currentReportSelectedStages.length === 0) {
            alert('Please add at least one comparison plot from a previous report OR select stages from the current report to compare.');
            return;
        }
        
        crossComparisonStatusMessage.textContent = 'Generating cross-comparison plot...';
        crossComparisonStatusMessage.className = '';
        crossComparisonPlotDiv.style.display = 'none';
        crossComparisonPlotDiv.innerHTML = ''; // Clear previous plot

        const payload = {
            selected_comparison_json_paths: selectedCrossReportJsonPaths, // These are full paths like "static/reports/..."
            current_report_timestamp: currentRunData.timestamp_prefix || null, // Timestamp of the *currently loaded* report
            current_report_selected_stages: currentReportSelectedStages
        };

        fetch('/generate_cross_comparison', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); });
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.cross_comparison_plot_path) {
                crossComparisonStatusMessage.textContent = 'Cross-comparison plot generated successfully.';
                crossComparisonStatusMessage.className = 'status-success';
                crossComparisonPlotDiv.style.display = 'block';
                crossComparisonPlotDiv.innerHTML = ''; // Explicitly clear before rendering new plot
                fetchAndRenderPlotly(data.cross_comparison_plot_path, crossComparisonPlotDiv);
            } else {
                throw new Error(data.message || 'Failed to generate cross-comparison plot.');
            }
        })
        .catch(error => {
            console.error('Error during cross-comparison generation:', error);
            crossComparisonStatusMessage.textContent = `Error: ${error.message}`;
            crossComparisonStatusMessage.className = 'status-error';
        });
    }

}); // Close the DOMContentLoaded listener 