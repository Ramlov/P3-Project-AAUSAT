// JavaScript code to handle conditional display of input fields
const trackingModeSelect = document.getElementById("tracking-mode");
const autotrackingControls = document.getElementById("autotracking-controls");
const manualControls = document.getElementById("manual-controls");

const autoinputControls = document.getElementById("autoinput-controls");

trackingModeSelect.addEventListener("change", function () {
    const selectedMode = trackingModeSelect.value;

    // Hide all control groups
    autotrackingControls.style.display = "none";
    manualControls.style.display = "none";
    autoinputControls.style.display = "none";

    // Display control group based on the selected mode
    if (selectedMode === "AUTOTRACKING") {
        autotrackingControls.style.display = "block";
    } else if (selectedMode === "MANUAL") {
        manualControls.style.display = "block";
    } else if (selectedMode === "AUTOINPUT") {
        autoinputControls.style.display = "block";
    }
});



