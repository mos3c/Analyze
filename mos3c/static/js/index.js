// Ensure the script runs after the DOM is fully loaded
document.addEventListener("DOMContentLoaded", () => {
    // Get DOM elements
    const fileNameDisplay = document.getElementById("fileName");
    const fileInput = document.getElementById("fileInput");
    const dropArea = document.getElementById("uploadBox");
    const uploadedIcon = document.getElementById("uploadedIcon");
    const uploadIcon = document.getElementById("uploadIcon");
    const uploadBtn = document.getElementById("uploadBtn");
    const cancelBtn = document.getElementById("cancelBtn");
    const uploadForm = document.getElementById("uploadForm");

    // Check if all elements exist to prevent null errors
    if (!fileNameDisplay || !fileInput || !dropArea || !uploadedIcon || !uploadIcon || !uploadBtn || !cancelBtn || !uploadForm) {
        console.error("One or more DOM elements not found. Please check your HTML.");
        return;
    }

    // Handle file selection and validation
    function handleFiles(files) {
        const file = files[0];
        if (file) {
            fileNameDisplay.textContent = `${file.name}`;
            if (file.type === "text/plain") {
                uploadedIcon.classList.remove("hidden");
                uploadIcon.classList.add("hidden");
                // Create a DataTransfer object to assign files to the input
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files; // Assign the file to the input
            } else {
                fileNameDisplay.textContent = "Please select a valid .txt file!";
                uploadedIcon.classList.add("hidden");
                uploadIcon.classList.remove("hidden");
            }
        } else {
            fileNameDisplay.textContent = "";
        }
    }

    // Handle file input change
    fileInput.addEventListener("change", (e) => {
        handleFiles(e.target.files);
    });

    // Prevent default drag-and-drop behavior
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight drop area on drag
    ["dragenter", "dragover"].forEach((eventName) => {
        dropArea.addEventListener(eventName, () => dropArea.classList.add("highlight"), false);
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropArea.addEventListener(eventName, () => dropArea.classList.remove("highlight"), false);
    });

    // Handle drop event
    dropArea.addEventListener("drop", (event) => {
        const files = event.dataTransfer.files;
        handleFiles(files);
    });

    // Handle upload button click
    uploadBtn.addEventListener("click", (e) => {
        e.preventDefault(); // Prevent default button behavior
        if (fileInput.files.length > 0 && fileInput.files[0].type === "text/plain") {
            uploadForm.submit(); // Submit the form to Django view
        } else {
            fileNameDisplay.textContent = "Please select a valid .txt file!";
        }
    });

    // Handle cancel button click
    cancelBtn.addEventListener("click", () => {
        fileInput.value = "";
        fileNameDisplay.textContent = "";
        uploadedIcon.classList.add("hidden");
        uploadIcon.classList.remove("hidden");
    });
});