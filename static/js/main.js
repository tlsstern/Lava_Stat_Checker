// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM loaded. Setting up mode selectors and nerd toggle.");

    // --- Setup for Comparison Page Mode Selector ---
    const compareModeSelector = document.getElementById('mode-selector');
    const compareStatsContainer = document.getElementById('stats-container');

    if (compareModeSelector && compareStatsContainer) {
        console.log("Setting up compare page mode selector.");
        const compareModeButtons = compareModeSelector.querySelectorAll('.mode-button');
        const compareModeSections = compareStatsContainer.querySelectorAll('.mode-stats-section');

        compareModeButtons.forEach(button => {
            button.addEventListener('click', () => {
                const selectedMode = button.getAttribute('data-mode');
                console.log(`Compare Mode selected: ${selectedMode}`);
                compareModeButtons.forEach(btn => {
                    btn.classList.remove('active', 'bg-purple-700');
                    btn.classList.add('bg-gray-600', 'hover:bg-gray-500');
                });
                button.classList.add('active', 'bg-purple-700');
                button.classList.remove('bg-gray-600', 'hover:bg-gray-500');
                compareModeSections.forEach(section => section.classList.add('hidden'));
                const sectionToShow = compareStatsContainer.querySelector(`#mode-${selectedMode}`);
                if (sectionToShow) sectionToShow.classList.remove('hidden');
            });
        });
         const initialCompareActiveButton = compareModeSelector.querySelector('.mode-button.active');
         if (initialCompareActiveButton) {
             initialCompareActiveButton.classList.remove('bg-gray-600', 'hover:bg-gray-500');
             initialCompareActiveButton.classList.add('bg-purple-700');
         }
    } else {
        console.log("Compare page elements not found.");
    }

    // --- Setup for Single Player Stats Page Mode Selector ---
    const statsModeSelector = document.getElementById('stats-mode-selector');
    const statsSectionsContainer = document.getElementById('stats-sections-container');

    if (statsModeSelector && statsSectionsContainer) {
        console.log("Setting up single player stats page mode selector.");
        const statsModeButtons = statsModeSelector.querySelectorAll('.mode-button');
        const statsModeSections = statsSectionsContainer.querySelectorAll('.mode-stats-section'); // Includes overall + modes

        statsModeButtons.forEach(button => {
            button.addEventListener('click', () => {
                const selectedMode = button.getAttribute('data-mode');
                console.log(`Stats Mode selected: ${selectedMode}`);
                statsModeButtons.forEach(btn => {
                    btn.classList.remove('active', 'bg-purple-700');
                    btn.classList.add('bg-gray-600', 'hover:bg-gray-500');
                });
                button.classList.add('active', 'bg-purple-700');
                button.classList.remove('bg-gray-600', 'hover:bg-gray-500');
                statsModeSections.forEach(section => section.classList.add('hidden'));
                const sectionToShow = statsSectionsContainer.querySelector(`#stats-${selectedMode}`);
                if (sectionToShow) sectionToShow.classList.remove('hidden');

                // Also hide nerd stats section when changing main mode view
                const allNerdSections = statsSectionsContainer.querySelectorAll('.nerd-stats-section');
                allNerdSections.forEach(ns => ns.classList.add('hidden'));
                const nerdToggleButton = document.getElementById('nerd-mode-toggle');
                if (nerdToggleButton) nerdToggleButton.textContent = 'Show Nerd Stats'; // Reset button text
            });
        });
        const initialStatsActiveButton = statsModeSelector.querySelector('.mode-button.active');
        if (initialStatsActiveButton) {
            initialStatsActiveButton.classList.remove('bg-gray-600', 'hover:bg-gray-500');
            initialStatsActiveButton.classList.add('bg-purple-700');
        }

        // --- Setup for Nerd Mode Toggle on Stats Page ---
        const nerdToggleButton = document.getElementById('nerd-mode-toggle');
        if (nerdToggleButton) {
             console.log("Setting up nerd mode toggle button.");
             nerdToggleButton.addEventListener('click', () => {
                 // Find the currently active mode section
                 const activeModeSection = statsSectionsContainer.querySelector('.mode-stats-section:not(.hidden)');
                 if (activeModeSection) {
                     // Find the corresponding nerd stats section within the active mode section
                     const nerdSectionId = activeModeSection.id.replace('stats-', 'nerd-stats-'); // e.g., stats-overall -> nerd-stats-overall
                     const nerdSection = activeModeSection.querySelector(`#${nerdSectionId}`);

                     if (nerdSection) {
                         nerdSection.classList.toggle('hidden');
                         // Update button text
                         if (nerdSection.classList.contains('hidden')) {
                             nerdToggleButton.textContent = 'Show Nerd Stats';
                             nerdToggleButton.classList.remove('active'); // Optional: style toggle differently when active
                         } else {
                             nerdToggleButton.textContent = 'Hide Nerd Stats';
                             nerdToggleButton.classList.add('active'); // Optional: style toggle differently when active
                         }
                         console.log(`Toggled nerd stats section: #${nerdSectionId}`);
                     } else {
                         console.warn(`Nerd stats section not found for active mode section: #${activeModeSection.id}`);
                         // Optionally disable or hide the nerd toggle button if no nerd stats exist for the current mode?
                     }
                 } else {
                     console.warn("Could not find active mode section to toggle nerd stats.");
                 }
             });
        } else {
             console.log("Nerd mode toggle button not found.");
        }

    } else {
        console.log("Single player stats page elements not found.");
    }
});
