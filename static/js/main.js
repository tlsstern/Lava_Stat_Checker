// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM loaded. Setting up mode selectors.");

    // --- Setup for Comparison Page ---
    const compareModeSelector = document.getElementById('mode-selector');
    const compareStatsContainer = document.getElementById('stats-container'); // Container for compare page rows

    if (compareModeSelector && compareStatsContainer) {
        console.log("Setting up compare page mode selector.");
        const compareModeButtons = compareModeSelector.querySelectorAll('.mode-button');
        const compareModeSections = compareStatsContainer.querySelectorAll('.mode-stats-section'); // These are the divs containing rows for each mode

        compareModeButtons.forEach(button => {
            button.addEventListener('click', () => {
                const selectedMode = button.getAttribute('data-mode');
                console.log(`Compare Mode selected: ${selectedMode}`);

                // Update button active states
                compareModeButtons.forEach(btn => {
                    btn.classList.remove('active', 'bg-purple-700');
                    btn.classList.add('bg-gray-600', 'hover:bg-gray-500');
                });
                button.classList.add('active', 'bg-purple-700');
                button.classList.remove('bg-gray-600', 'hover:bg-gray-500');

                // Hide all mode sections (groups of rows)
                compareModeSections.forEach(section => {
                    section.classList.add('hidden');
                });

                // Show the selected mode section
                const sectionToShow = compareStatsContainer.querySelector(`#mode-${selectedMode}`);
                if (sectionToShow) {
                    sectionToShow.classList.remove('hidden');
                    console.log(`Showing compare section: #mode-${selectedMode}`);
                } else {
                    console.error(`Compare section not found for mode: ${selectedMode}`);
                }
            });
        });

         // Ensure the default 'Overall' button is styled correctly on load for compare page
         const initialCompareActiveButton = compareModeSelector.querySelector('.mode-button.active');
         if (initialCompareActiveButton) {
             initialCompareActiveButton.classList.remove('bg-gray-600', 'hover:bg-gray-500');
             initialCompareActiveButton.classList.add('bg-purple-700');
         }

    } else {
        console.log("Compare page mode selector or stats container not found (this is normal if not on compare page).");
    }

    // --- Setup for Single Player Stats Page ---
    const statsModeSelector = document.getElementById('stats-mode-selector');
    const statsSectionsContainer = document.getElementById('stats-sections-container'); // Container for stats page sections

    if (statsModeSelector && statsSectionsContainer) {
        console.log("Setting up single player stats page mode selector.");
        const statsModeButtons = statsModeSelector.querySelectorAll('.mode-button');
        const statsModeSections = statsSectionsContainer.querySelectorAll('.mode-stats-section'); // These are the divs containing grids for each mode

        statsModeButtons.forEach(button => {
            button.addEventListener('click', () => {
                const selectedMode = button.getAttribute('data-mode');
                console.log(`Stats Mode selected: ${selectedMode}`);

                // Update button active states
                statsModeButtons.forEach(btn => {
                    btn.classList.remove('active', 'bg-purple-700');
                    btn.classList.add('bg-gray-600', 'hover:bg-gray-500');
                });
                button.classList.add('active', 'bg-purple-700');
                button.classList.remove('bg-gray-600', 'hover:bg-gray-500');

                // Hide all mode sections
                statsModeSections.forEach(section => {
                    section.classList.add('hidden');
                });

                // Show the selected mode section
                // Note: The ID on stats.html is slightly different (e.g., #stats-overall)
                const sectionToShow = statsSectionsContainer.querySelector(`#stats-${selectedMode}`);
                if (sectionToShow) {
                    sectionToShow.classList.remove('hidden');
                    console.log(`Showing stats section: #stats-${selectedMode}`);
                } else {
                    console.error(`Stats section not found for mode: ${selectedMode}`);
                }
            });
        });

        // Ensure the default 'Overall' button is styled correctly on load for stats page
        const initialStatsActiveButton = statsModeSelector.querySelector('.mode-button.active');
        if (initialStatsActiveButton) {
            initialStatsActiveButton.classList.remove('bg-gray-600', 'hover:bg-gray-500');
            initialStatsActiveButton.classList.add('bg-purple-700');
        }

    } else {
        console.log("Single player stats mode selector or sections container not found (this is normal if not on stats page).");
    }
});
