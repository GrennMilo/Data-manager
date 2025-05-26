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
    const themeSwitcherButton = document.getElementById('theme-switcher');
    
    // Only try to access these elements if they exist on the current page
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

    // Report Management Elements
    const manageReportSelect = document.getElementById('manage-report-select');
    const renameReportButton = document.getElementById('rename-report-button');
    const deleteReportButton = document.getElementById('delete-report-button');
    const renameReportModal = document.getElementById('rename-report-modal');
    const newReportNameInput = document.getElementById('new-report-name');
    const confirmRenameButton = document.getElementById('confirm-rename-button');
    const closeModalSpan = document.querySelector('.close-modal');
    const manageStatusMessage = document.getElementById('manage-status-message');

    // Report Contents Elements
    const viewReportContentsButton = document.getElementById('view-report-contents-button');
    const reportContentsModal = document.getElementById('report-contents-modal');
    const reportContentsTree = document.getElementById('report-contents-tree');
    const refreshContentsButton = document.getElementById('refresh-contents-button');
    const closeContentsButton = document.getElementById('close-contents-button');

    // Comparison Elements
    const compareStagesButton = document.getElementById('compare-stages-button');
    const comparisonReportDiv = document.getElementById('comparison-report');
    const comparisonPlotDiv = document.getElementById('comparison-plot-div');

    // Cross-Report Comparison Elements
    const allComparisonPlotsContainer = document.getElementById('all-comparison-plots-container');
    const addSelectedCrossJsonButton = document.getElementById('add-selected-cross-json-button');
    const selectedCrossJsonListUl = document.getElementById('selected-cross-json-list');
    const generateCrossComparisonButton = document.getElementById('generate-cross-comparison-button');
    const crossComparisonStatusMessage = document.getElementById('cross-comparison-status-message');
    const crossComparisonPlotDiv = document.getElementById('cross-comparison-plot-div');
    const downloadCrossComparisonCSVButton = document.getElementById('download-cross-comparison-csv-button');

    // --- Global Variables for Cross-Report Comparison ---
    let selectedCrossReportJsonPaths = []; // Stores full paths for backend

    // --- Global variables for report contents ---
    let currentReportName = null;

    // --- Initial Setup ---
    applyInitialTheme(); // Apply theme on load

    // Only initialize these if the elements exist on the current page
    if (reportSelect) fetchAndPopulateReportList();
    if (manageReportSelect) fetchAndPopulateManageReportList();
    if (allComparisonPlotsContainer) fetchAndPopulateAllComparisonPlots();

    // --- Event Listeners ---
    // Always add theme switch listener
    if (themeSwitcherButton) {
        themeSwitcherButton.addEventListener('click', handleThemeSwitch);
    }
    
    // Only add these listeners if the elements exist on this page
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleUploadSubmit);
    }
    
    if (loadReportButton) {
        loadReportButton.addEventListener('click', handleLoadReportClick);
    }
    
    if (downloadSelectedButton) {
        downloadSelectedButton.addEventListener('click', handleDownloadSelectedClick);
    }
    
    if (compareStagesButton) {
        compareStagesButton.addEventListener('click', handleCompareStagesClick);
    }
    
    if (addSelectedCrossJsonButton) {
        addSelectedCrossJsonButton.addEventListener('click', handleAddSelectedCrossJson);
    }
    
    if (generateCrossComparisonButton) {
        generateCrossComparisonButton.addEventListener('click', handleGenerateCrossComparison);
    }
    
    if (downloadCrossComparisonCSVButton) {
        downloadCrossComparisonCSVButton.addEventListener('click', handleDownloadCrossComparisonCSV);
    }

    if (renameReportButton) {
        renameReportButton.addEventListener('click', handleRenameReportClick);
    }

    if (deleteReportButton) {
        deleteReportButton.addEventListener('click', handleDeleteReportClick);
    }

    if (confirmRenameButton) {
        confirmRenameButton.addEventListener('click', handleConfirmRenameClick);
    }

    if (closeModalSpan) {
        closeModalSpan.addEventListener('click', () => {
            renameReportModal.style.display = 'none';
        });
    }

    if (viewReportContentsButton) {
        viewReportContentsButton.addEventListener('click', handleViewReportContentsClick);
    }

    if (refreshContentsButton) {
        refreshContentsButton.addEventListener('click', () => {
            if (currentReportName) {
                loadReportContents(currentReportName);
            }
        });
    }

    if (closeContentsButton) {
        closeContentsButton.addEventListener('click', () => {
            reportContentsModal.style.display = 'none';
        });
    }

    // Close modals when clicking on X or outside
    document.querySelectorAll('.close-modal').forEach(span => {
        span.addEventListener('click', event => {
            const modal = event.target.closest('.modal');
            if (modal) {
                modal.style.display = 'none';
            }
        });
    });

    window.addEventListener('click', event => {
        if (event.target.classList.contains('modal')) {
            event.target.style.display = 'none';
        }
    });

    // --- Function Definitions ---

    // --- Theme Management Functions ---
    function applyInitialTheme() {
        const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        if (savedTheme === 'light') {
            document.body.classList.add('light-theme');
            if (themeSwitcherButton) themeSwitcherButton.textContent = '☀️';
        } else {
            document.body.classList.remove('light-theme');
            if (themeSwitcherButton) themeSwitcherButton.textContent = '🌙';
        }
        // Re-render visible plots with the new theme
        updateVisiblePlotsTheme();
    }

    function handleThemeSwitch() {
        document.body.classList.toggle('light-theme');
        if (document.body.classList.contains('light-theme')) {
            localStorage.setItem('theme', 'light');
            themeSwitcherButton.textContent = '☀️';
        } else {
            localStorage.setItem('theme', 'dark');
            themeSwitcherButton.textContent = '🌙';
        }
        // Re-render visible plots with the new theme
        updateVisiblePlotsTheme();
    }

    function getCurrentThemeColors() {
        const isLightTheme = document.body.classList.contains('light-theme');
        if (isLightTheme) {
            return {
                paper_bgcolor: '#f4f6f8',
                plot_bgcolor: '#ffffff',
                font_color: '#212529',
                gridcolor: '#dee2e6',
                linecolor: '#ced4da',
                zerolinecolor: '#ced4da',
                legend_bgcolor: '#ffffff',
                legend_bordercolor: '#ced4da',
                legend_font_color: '#212529'
            };
        } else {
            // Dark theme (current defaults from script.js)
            return {
                paper_bgcolor: '#2c2c2c',
                plot_bgcolor: '#383838',
                font_color: '#e0e0e0',
                gridcolor: 'rgba(0,0,0,0)', // Was transparent
                linecolor: '#5a5a5a',
                zerolinecolor: '#5a5a5a',
                legend_bgcolor: '#383838',
                legend_bordercolor: '#4a4a4a',
                legend_font_color: '#e0e0e0'
            };
        }
    }

    function updateVisiblePlotsTheme() {
        // Overall plot
        if (overallPlotDiv && overallPlotDiv._fullData) { // Check if plot exists
             fetchAndRenderPlotly(currentRunData.overall_plot_path, overallPlotDiv);
        }
        // Step plots
        const stepPlotContainers = document.querySelectorAll('.step-plot-container');
        stepPlotContainers.forEach(container => {
            if (container._fullData) { // Check if plot exists in this container
                const plotPath = container.dataset.plotPath; // Assuming we can get path if needed, or re-fetch from button
                const stepNum = container.id.split('-').pop();
                const stepReport = currentRunData.step_reports.find(sr => sr.step_number == stepNum);
                if(stepReport && stepReport.plot_path){
                     fetchAndRenderPlotly(stepReport.plot_path, container);
                }
            }
        });
        // Comparison plot
        if (comparisonPlotDiv && comparisonPlotDiv._fullData) {
             // Need to get the path for the comparison plot if it was dynamically generated
             // This might require storing the path or finding a way to re-trigger its generation info
             // For now, let's assume it re-fetches from a known path if available
             const comparisonPlotPath = comparisonPlotDiv.dataset.currentPlotPath; // We'll need to set this attribute when plot is loaded
             if(comparisonPlotPath) {
                fetchAndRenderPlotly(comparisonPlotPath, comparisonPlotDiv);
             }
        }
        // Cross-comparison plot
        if (crossComparisonPlotDiv && crossComparisonPlotDiv._fullData) {
            const crossComparisonPlotPath = crossComparisonPlotDiv.dataset.currentPlotPath; // We'll need to set this attribute
            if(crossComparisonPlotPath) {
                fetchAndRenderPlotly(crossComparisonPlotPath, crossComparisonPlotDiv);
            }
        }
    }

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
        const reportPrefixText = document.getElementById('report_prefix_text_input').value.trim();

        // Append the prefix text if it's not empty
        // The backend expects it as 'report_prefix_text'
        if (reportPrefixText) {
            formData.append('report_prefix_text', reportPrefixText);
        }
        
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
                const themeColors = getCurrentThemeColors();

                if (!plotData.layout) plotData.layout = {};
                plotData.layout.paper_bgcolor = themeColors.paper_bgcolor;
                plotData.layout.plot_bgcolor = themeColors.plot_bgcolor;
                plotData.layout.font = { color: themeColors.font_color }; 
                
                for (const key in plotData.layout) {
                     if (key.startsWith('xaxis') || key.startsWith('yaxis')) {
                         if(!plotData.layout[key]) plotData.layout[key] = {};
                         plotData.layout[key].gridcolor = themeColors.gridcolor;
                         plotData.layout[key].linecolor = themeColors.linecolor; 
                         plotData.layout[key].zerolinecolor = themeColors.zerolinecolor;
                         // Preserve title and tick font colors for specific axes if they were intentionally set (e.g. red for Temp)
                         // This requires checking if the specific axis font color was set in the original plot JSON
                         // For now, we apply the global theme font color to axis titles and ticks unless it's yaxis5
                         if (plotData.layout[key].title && plotData.layout[key].title.font) {
                            // Dont override if specific color was set, unless it is yaxis5 (stage)
                            if (!plotData.layout[key].title.font.color || key === 'yaxis5') {
                                plotData.layout[key].title.font.color = themeColors.font_color;
                            }
                         } else if (plotData.layout[key].title) {
                            plotData.layout[key].title.font = { color: themeColors.font_color };
                         }
                         if (plotData.layout[key].tickfont) {
                            if (!plotData.layout[key].tickfont.color || key === 'yaxis5') {
                                plotData.layout[key].tickfont.color = themeColors.font_color;
                            }
                         } else {
                            plotData.layout[key].tickfont = { color: themeColors.font_color };
                         }
                     }
                }
                if (plotData.layout.legend) {
                    if(!plotData.layout.legend) plotData.layout.legend = {};
                    plotData.layout.legend.bgcolor = themeColors.legend_bgcolor;
                    plotData.layout.legend.bordercolor = themeColors.legend_bordercolor;
                    plotData.layout.legend.font = { color: themeColors.legend_font_color };
                }

                Plotly.newPlot(targetDivElement, plotData.data, plotData.layout, {responsive: true});
                targetDivElement.dataset.currentPlotPath = plotJsonPath; // Store path for re-rendering on theme change
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
        const comparisonPrefixInput = document.getElementById('comparison-prefix-input');
        const comparisonPrefix = comparisonPrefixInput ? comparisonPrefixInput.value.trim() : '';
        
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
                stages: selectedStageNumbers,
                comparison_prefix: comparisonPrefix // Add the prefix to the payload
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

    // Function to fetch and populate all comparison plots from all reports
    function fetchAndPopulateAllComparisonPlots() {
        fetch('/list_all_comparison_plots')
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch comparison plots');
                return response.json();
            })
            .then(data => {
                if (data.success && data.comparison_plots && data.comparison_plots.length > 0) {
                    allComparisonPlotsContainer.innerHTML = ''; // Clear loading message
                    
                    // Group comparison plots by report folder for better organization
                    const plotsByReport = {};
                    data.comparison_plots.forEach(plot => {
                        if (!plotsByReport[plot.report_folder]) {
                            plotsByReport[plot.report_folder] = [];
                        }
                        plotsByReport[plot.report_folder].push(plot);
                    });
                    
                    // Create a section for each report folder
                    Object.keys(plotsByReport).forEach(reportFolder => {
                        const reportSection = document.createElement('div');
                        reportSection.classList.add('report-comparison-section');
                        reportSection.style.marginBottom = '15px';
                        
                        const reportHeader = document.createElement('h4');
                        reportHeader.textContent = reportFolder;
                        reportHeader.style.marginBottom = '5px';
                        reportHeader.style.borderBottom = '1px solid #555';
                        reportSection.appendChild(reportHeader);
                        
                        // Add plots for this report
                        plotsByReport[reportFolder].forEach(plot => {
                            const checkboxId = `cross-plot-${plot.report_folder}-${plot.name.replace(/\.|\s/g, '-')}`;
                            
                            const div = document.createElement('div');
                            div.style.marginLeft = '10px';
                            
                            const checkbox = document.createElement('input');
                            checkbox.type = 'checkbox';
                            checkbox.id = checkboxId;
                            checkbox.value = plot.path;
                            checkbox.name = 'crossReportJsonFile';
                            
                            const label = document.createElement('label');
                            label.htmlFor = checkboxId;
                            label.textContent = plot.name;
                            
                            div.appendChild(checkbox);
                            div.appendChild(label);
                            reportSection.appendChild(div);
                        });
                        
                        allComparisonPlotsContainer.appendChild(reportSection);
                    });
                } else {
                    allComparisonPlotsContainer.innerHTML = '<p>No comparison plots found across any reports.</p>';
                    if (!data.success) throw new Error(data.message || 'Failed to load comparison plots');
                }
            })
            .catch(error => {
                console.error('Error fetching all comparison plots:', error);
                allComparisonPlotsContainer.innerHTML = `<p class="status-error">Error loading comparison plots: ${error.message}</p>`;
            });
    }

    // Handler for "Add Selected Plot(s) to Analysis" button
    function handleAddSelectedCrossJson() {
        const selectedCheckboxes = document.querySelectorAll('input[name="crossReportJsonFile"]:checked');
        let newFilesAdded = false;
        
        selectedCheckboxes.forEach(checkbox => {
            if (!selectedCrossReportJsonPaths.includes(checkbox.value)) {
                selectedCrossReportJsonPaths.push(checkbox.value); // Add full path
                
                const listItem = document.createElement('li');
                
                // Extract report folder and filename for display
                const pathParts = checkbox.value.split('/');
                const reportFolder = pathParts[2]; // Assuming path is like "static/reports/REPORT_FOLDER/..."
                const fileName = pathParts[pathParts.length - 1];
                
                listItem.innerHTML = `<strong>${reportFolder}</strong>: ${fileName}`;
                listItem.dataset.path = checkbox.value; // Store full path for potential removal
                
                // Add remove button
                const removeButton = document.createElement('button');
                removeButton.textContent = 'Remove';
                removeButton.className = 'small-button';
                removeButton.style.marginLeft = '10px';
                removeButton.addEventListener('click', function() {
                    const index = selectedCrossReportJsonPaths.indexOf(checkbox.value);
                    if (index > -1) {
                        selectedCrossReportJsonPaths.splice(index, 1);
                    }
                    listItem.remove();
                });
                
                listItem.appendChild(removeButton);
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
                downloadCrossComparisonCSVButton.style.display = 'inline-block'; // Show download button
            } else {
                downloadCrossComparisonCSVButton.style.display = 'none'; // Hide on error
                throw new Error(data.message || 'Failed to generate cross-comparison plot.');
            }
        })
        .catch(error => {
            console.error('Error during cross-comparison generation:', error);
            crossComparisonStatusMessage.textContent = `Error: ${error.message}`;
            crossComparisonStatusMessage.className = 'status-error';
            downloadCrossComparisonCSVButton.style.display = 'none'; // Hide on error
        });
    }

    // --- New Functions to Parse Trace Names from Cross-Comparison Plot ---
    function parseCrossComparisonTraceName(traceName) {
        let source = "Unknown_Source";
        let stage = "Unknown_Stage";
        let parameter = traceName; // Default if parsing fails

        const parts = traceName.split(' - ');

        if (parts.length >= 3) {
            source = parts[0].trim();
            stage = parts[1].trim();
            parameter = parts.slice(2).join(' - ').trim(); // The rest is the parameter
        } else if (parts.length === 2) {
            // If only two parts, it's ambiguous. Could be (Source, Param) or (Stage, Param).
            // For now, let's assume the first part might be a combined source/stage or just source.
            source = parts[0].trim();
            parameter = parts[1].trim();
            // stage remains "Unknown_Stage"
        }
        // No specific cleanup for "Current (...)" needed here, the full source string is fine.
        return { source, stage, parameter };
    }

    // --- New Event Handler for Downloading Cross-Comparison CSV ---
    function handleDownloadCrossComparisonCSV() {
        const plotDataToUse = crossComparisonPlotDiv._fullData || crossComparisonPlotDiv.data;

        if (!crossComparisonPlotDiv || !plotDataToUse || !crossComparisonPlotDiv.layout || !crossComparisonPlotDiv.layout.xaxis) {
            alert('No cross-comparison plot data or x-axis layout available to download.');
            return;
        }

        const xrangeRaw = crossComparisonPlotDiv.layout.xaxis.range;
        console.log('[CSV Export] Plotly x-axis range (raw):', xrangeRaw);

        if (!xrangeRaw || xrangeRaw.length !== 2) {
            alert('Could not determine the visible data range from plot.xaxis.range. Please ensure the plot is fully rendered.');
            return;
        }

        const xMin = Number(xrangeRaw[0]);
        const xMax = Number(xrangeRaw[1]);
        console.log('[CSV Export] Parsed xMin, xMax:', xMin, xMax);

        if (isNaN(xMin) || isNaN(xMax)) {
            alert('Visible x-axis range values are not valid numbers. Cannot filter data.');
            return;
        }

        // Intermediate structure: { "Source//Stage": { "RelativeTime": { Temperature: val, NH3: val } } }
        const processedData = {}; 

        plotDataToUse.forEach((trace, traceIndex) => {
            // console.log(`[CSV Export] Processing trace ${traceIndex}: ${trace.name}`);
            const { source, stage, parameter: parameterNameOriginal } = parseCrossComparisonTraceName(trace.name);
            
            let standardizedParameter = 'Other';
            if (parameterNameOriginal.includes('Temp') || parameterNameOriginal.includes('T Heater')) {
                standardizedParameter = 'Temperature';
            } else if (parameterNameOriginal.toUpperCase().includes('NH3')) {
                standardizedParameter = 'NH3';
            }

            if (standardizedParameter === 'Other') {
                // console.log(`[CSV Export] Skipping trace ${trace.name} as it's not Temperature or NH3.`);
                return; // Effectively a 'continue' in forEach
            }

            if (trace.x && typeof trace.x.length === 'number' &&
                trace.y && typeof trace.y.length === 'number') {
                
                const groupKey = `${source}//${stage}`;
                if (!processedData[groupKey]) {
                    processedData[groupKey] = {};
                }

                for (let i = 0; i < trace.x.length; i++) {
                    const xValRaw = trace.x[i];
                    const yValRaw = trace.y[i];
                    const numXVal = Number(xValRaw);

                    if (!isNaN(numXVal) && numXVal >= xMin && numXVal <= xMax) {
                        const timeKey = numXVal.toString(); // Use string for time key to avoid float precision issues with object keys
                        if (!processedData[groupKey][timeKey]) {
                            processedData[groupKey][timeKey] = {};
                        }
                        processedData[groupKey][timeKey][standardizedParameter] = yValRaw;
                    }
                }
            } else {
                console.warn(`[CSV Export] Skipping trace ${traceIndex} (${trace.name}) due to missing or non-array-like x/y data.`);
            }
        });

        const csvDataRows = [];
        for (const groupKey in processedData) {
            const [source, stage] = groupKey.split('//');
            for (const timeKey in processedData[groupKey]) {
                const relativeTime = parseFloat(timeKey);
                const timeData = processedData[groupKey][timeKey];
                csvDataRows.push({
                    Source: source,
                    Stage: stage,
                    RelativeTime: relativeTime,
                    Temperature: timeData.Temperature !== undefined ? timeData.Temperature : null,
                    NH3: timeData.NH3 !== undefined ? timeData.NH3 : null
                });
            }
        }

        // Sort the data
        csvDataRows.sort((a, b) => {
            if (a.Source < b.Source) return -1;
            if (a.Source > b.Source) return 1;
            if (a.Stage < b.Stage) return -1;
            if (a.Stage > b.Stage) return 1;
            return a.RelativeTime - b.RelativeTime;
        });
        
        console.log('[CSV Export] Total data rows for CSV (restructured):', csvDataRows.length);
        if (csvDataRows.length === 0) {
            alert('No Temperature or NH3 data points found in the current visible range of the plot. If data is visible, please check the browser console for potential issues or try adjusting the plot view.');
            return;
        }

        crossComparisonStatusMessage.textContent = 'Preparing CSV data...';
        crossComparisonStatusMessage.className = '';

        fetch('/download_cross_comparison_csv', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(csvDataRows) // Send the array of row objects
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); })
                               .catch(() => { throw new Error(`Server error preparing CSV: ${response.status}`); });
            }
            const disposition = response.headers.get('Content-Disposition');
            let filename = `cross_comparison_export_${new Date().toISOString().slice(0,19).replace(/[:T]/g, '-')}.csv`;
            if (disposition && disposition.includes('attachment')) {
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
            crossComparisonStatusMessage.textContent = 'CSV download initiated.';
            crossComparisonStatusMessage.className = 'status-success';
        })
        .catch(error => {
            crossComparisonStatusMessage.textContent = 'Error preparing CSV: ' + error.message;
            crossComparisonStatusMessage.className = 'status-error';
            console.error('Error during fetch /download_cross_comparison_csv:', error);
        });
    }

    // Function to fetch and populate the report management dropdown
    function fetchAndPopulateManageReportList() {
        fetch('/list_reports')
            .then(response => {
                if (!response.ok) throw new Error('Failed to fetch report list');
                return response.json();
            })
            .then(data => {
                if (data.success && data.reports && data.reports.length > 0) {
                    manageReportSelect.innerHTML = '<option value="">Select a report...</option>'; // Clear loading message
                    data.reports.forEach(timestamp => {
                        const option = document.createElement('option');
                        option.value = timestamp;
                        option.textContent = timestamp;
                        manageReportSelect.appendChild(option);
                    });
                } else {
                    manageReportSelect.innerHTML = '<option value="">No reports found</option>';
                    if (!data.success) throw new Error(data.message || 'Failed to load reports');
                }
            })
            .catch(error => {
                console.error('Error fetching report list for management:', error);
                manageReportSelect.innerHTML = '<option value="">Error loading reports</option>';
                manageStatusMessage.textContent = `Error: ${error.message}`;
                manageStatusMessage.className = 'status-error';
            });
    }

    // Handler for "Rename" button click
    function handleRenameReportClick() {
        const selectedReportName = manageReportSelect.value;
        if (!selectedReportName) {
            manageStatusMessage.textContent = 'Please select a report to rename.';
            manageStatusMessage.className = 'status-error';
            return;
        }
        
        // Populate the new name input with the current name as a starting point
        newReportNameInput.value = selectedReportName;
        
        // Show the rename modal
        renameReportModal.style.display = 'flex';
    }

    // Handler for "Confirm Rename" button click
    function handleConfirmRenameClick() {
        const oldName = manageReportSelect.value;
        const newName = newReportNameInput.value.trim();
        
        if (!newName) {
            alert('Please enter a new name for the report.');
            return;
        }
        
        // Clear status and close modal
        manageStatusMessage.textContent = 'Renaming report...';
        manageStatusMessage.className = '';
        renameReportModal.style.display = 'none';
        
        fetch('/rename_report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_name: oldName, new_name: newName })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                manageStatusMessage.textContent = data.message || 'Report renamed successfully.';
                manageStatusMessage.className = 'status-success';
                
                // Refresh both report select dropdowns
                fetchAndPopulateReportList();
                fetchAndPopulateManageReportList();
                
                // Refresh comparison plots list if it exists
                if (allComparisonPlotsContainer) {
                    fetchAndPopulateAllComparisonPlots();
                }
            } else {
                throw new Error(data.message || 'Failed to rename report.');
            }
        })
        .catch(error => {
            manageStatusMessage.textContent = `Error: ${error.message}`;
            manageStatusMessage.className = 'status-error';
            console.error('Error renaming report:', error);
        });
    }

    // Handler for "Delete" button click
    function handleDeleteReportClick() {
        const selectedReportName = manageReportSelect.value;
        if (!selectedReportName) {
            manageStatusMessage.textContent = 'Please select a report to delete.';
            manageStatusMessage.className = 'status-error';
            return;
        }
        
        // Create a confirmation dialog
        const confirmDialog = document.createElement('div');
        confirmDialog.className = 'modal';
        confirmDialog.style.display = 'flex';
        
        confirmDialog.innerHTML = `
            <div class="modal-content confirm-dialog">
                <span class="close-modal">&times;</span>
                <h3>Delete Report</h3>
                <p>Are you sure you want to delete the report "${selectedReportName}"?<br>This action cannot be undone.</p>
                <button class="confirm-delete">Yes, Delete</button>
                <button class="cancel-delete">Cancel</button>
            </div>
        `;
        
        document.body.appendChild(confirmDialog);
        
        // Event listeners for the confirmation dialog
        const closeBtn = confirmDialog.querySelector('.close-modal');
        const confirmBtn = confirmDialog.querySelector('.confirm-delete');
        const cancelBtn = confirmDialog.querySelector('.cancel-delete');
        
        closeBtn.addEventListener('click', () => {
            document.body.removeChild(confirmDialog);
        });
        
        cancelBtn.addEventListener('click', () => {
            document.body.removeChild(confirmDialog);
        });
        
        confirmBtn.addEventListener('click', () => {
            document.body.removeChild(confirmDialog);
            
            // Proceed with deletion
            manageStatusMessage.textContent = 'Deleting report...';
            manageStatusMessage.className = '';
            
            fetch('/delete_report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ report_name: selectedReportName })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    manageStatusMessage.textContent = data.message || 'Report deleted successfully.';
                    manageStatusMessage.className = 'status-success';
                    
                    // Refresh both report select dropdowns
                    fetchAndPopulateReportList();
                    fetchAndPopulateManageReportList();
                    
                    // Refresh comparison plots list if it exists
                    if (allComparisonPlotsContainer) {
                        fetchAndPopulateAllComparisonPlots();
                    }
                } else {
                    throw new Error(data.message || 'Failed to delete report.');
                }
            })
            .catch(error => {
                manageStatusMessage.textContent = `Error: ${error.message}`;
                manageStatusMessage.className = 'status-error';
                console.error('Error deleting report:', error);
            });
        });
        
        // Close modal when clicking outside of it
        confirmDialog.addEventListener('click', event => {
            if (event.target === confirmDialog) {
                document.body.removeChild(confirmDialog);
            }
        });
    }

    // Handler for "View Contents" button click
    function handleViewReportContentsClick() {
        const selectedReportName = manageReportSelect.value;
        if (!selectedReportName) {
            manageStatusMessage.textContent = 'Please select a report to view contents.';
            manageStatusMessage.className = 'status-error';
            return;
        }
        
        currentReportName = selectedReportName;
        reportContentsModal.style.display = 'flex';
        loadReportContents(selectedReportName);
    }

    // Function to load report contents
    function loadReportContents(reportName) {
        reportContentsTree.innerHTML = '<p>Loading report contents...</p>';
        
        fetch(`/list_report_contents/${reportName}`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Create the folder tree
                    reportContentsTree.innerHTML = '';
                    const folderTree = document.createElement('ul');
                    folderTree.className = 'folder-tree';
                    
                    // Build tree from contents data
                    buildFolderTree(folderTree, data.contents, reportName);
                    
                    reportContentsTree.appendChild(folderTree);
                } else {
                    throw new Error(data.message || 'Failed to load report contents.');
                }
            })
            .catch(error => {
                reportContentsTree.innerHTML = `<p class="status-error">Error: ${error.message}</p>`;
                console.error('Error loading report contents:', error);
            });
    }

    // Function to build the folder tree UI
    function buildFolderTree(parentElement, items, reportName) {
        items.forEach(item => {
            const li = document.createElement('li');
            
            if (item.type === 'folder') {
                // Create folder element
                const folderDiv = document.createElement('div');
                folderDiv.className = 'folder';
                folderDiv.textContent = item.name;
                folderDiv.addEventListener('click', function(e) {
                    e.stopPropagation();
                    this.classList.toggle('open');
                    const childrenUl = this.nextElementSibling;
                    if (childrenUl) {
                        childrenUl.style.display = childrenUl.style.display === 'none' ? 'block' : 'none';
                    }
                });
                
                li.appendChild(folderDiv);
                
                // Create children container if there are children
                if (item.children && item.children.length > 0) {
                    const childrenUl = document.createElement('ul');
                    childrenUl.style.display = 'none'; // Initially collapsed
                    buildFolderTree(childrenUl, item.children, reportName);
                    li.appendChild(childrenUl);
                }
            } else {
                // Create file element
                const fileDiv = document.createElement('div');
                fileDiv.className = 'file';
                fileDiv.innerHTML = `${item.name} <span style="color: var(--text-secondary); margin-left: 5px;">(${item.size})</span>`;
                
                // Add file actions
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'file-actions';
                
                // View button
                const viewBtn = document.createElement('button');
                viewBtn.textContent = 'View';
                viewBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    viewFileContent(reportName, item.path);
                });
                actionsDiv.appendChild(viewBtn);
                
                // Download button
                const downloadBtn = document.createElement('button');
                downloadBtn.textContent = 'Download';
                downloadBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    downloadFile(reportName, item.path, item.name);
                });
                actionsDiv.appendChild(downloadBtn);
                
                // Delete button
                const deleteBtn = document.createElement('button');
                deleteBtn.textContent = 'Delete';
                deleteBtn.className = 'delete-file';
                deleteBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    confirmDeleteFile(reportName, item.path);
                });
                actionsDiv.appendChild(deleteBtn);
                
                fileDiv.appendChild(actionsDiv);
                li.appendChild(fileDiv);
            }
            
            parentElement.appendChild(li);
        });
    }

    // Function to view file content
    function viewFileContent(reportName, filePath) {
        fetch('/get_file_content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ report_name: reportName, file_path: filePath })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Create a modal to display the file content
                const viewModal = document.createElement('div');
                viewModal.className = 'modal';
                viewModal.style.display = 'flex';
                
                let modalContent;
                if (data.is_binary) {
                    // For binary files
                    modalContent = `
                        <div class="modal-content" style="width: 500px;">
                            <span class="close-modal">&times;</span>
                            <h3>File: ${filePath}</h3>
                            <p>${data.message}</p>
                            <p>You can download this file to view its contents.</p>
                            <div style="text-align: center; margin-top: 15px;">
                                <button id="download-binary-file">Download File</button>
                            </div>
                        </div>
                    `;
                } else {
                    // For text files
                    modalContent = `
                        <div class="modal-content" style="width: 800px; max-width: 90%;">
                            <span class="close-modal">&times;</span>
                            <h3>File: ${filePath}</h3>
                            <div style="max-height: 60vh; overflow-y: auto; background: var(--bg-dark-tertiary); padding: 15px; border-radius: 5px; white-space: pre-wrap; font-family: monospace;">${data.content}</div>
                            <div style="text-align: right; margin-top: 15px;">
                                <button id="close-view-modal">Close</button>
                            </div>
                        </div>
                    `;
                }
                
                viewModal.innerHTML = modalContent;
                document.body.appendChild(viewModal);
                
                // Add event listeners
                const closeBtn = viewModal.querySelector('.close-modal');
                const closeViewBtn = viewModal.querySelector('#close-view-modal');
                const downloadBinaryBtn = viewModal.querySelector('#download-binary-file');
                
                if (closeBtn) {
                    closeBtn.addEventListener('click', () => {
                        document.body.removeChild(viewModal);
                    });
                }
                
                if (closeViewBtn) {
                    closeViewBtn.addEventListener('click', () => {
                        document.body.removeChild(viewModal);
                    });
                }
                
                if (downloadBinaryBtn) {
                    downloadBinaryBtn.addEventListener('click', () => {
                        downloadFile(reportName, filePath, filePath.split('/').pop());
                        document.body.removeChild(viewModal);
                    });
                }
                
                // Close modal when clicking outside
                viewModal.addEventListener('click', event => {
                    if (event.target === viewModal) {
                        document.body.removeChild(viewModal);
                    }
                });
            } else {
                throw new Error(data.message || 'Failed to get file content.');
            }
        })
        .catch(error => {
            alert(`Error viewing file: ${error.message}`);
            console.error('Error viewing file:', error);
        });
    }

    // Function to download a file
    function downloadFile(reportName, filePath, fileName) {
        // Construct download URL
        const downloadUrl = `/static/reports/${reportName}/${filePath}`;
        
        // Create a temporary link and trigger the download
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    // Function to confirm and delete a file
    function confirmDeleteFile(reportName, filePath) {
        const fileName = filePath.split('/').pop();
        
        if (confirm(`Are you sure you want to delete the file "${fileName}"? This action cannot be undone.`)) {
            fetch('/delete_report_file', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ report_name: reportName, file_path: filePath })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.message || `Server error: ${response.status}`); });
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Refresh the contents
                    loadReportContents(reportName);
                } else {
                    throw new Error(data.message || 'Failed to delete file.');
                }
            })
            .catch(error => {
                alert(`Error deleting file: ${error.message}`);
                console.error('Error deleting file:', error);
            });
        }
    }

}); // Close the DOMContentLoaded listener 