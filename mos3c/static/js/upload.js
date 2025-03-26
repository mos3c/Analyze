// // upload.js

// // Wait for the DOM to be fully loaded
// document.addEventListener('DOMContentLoaded', () => {
//     // Get DOM elements
//     const uploadBox = document.getElementById('uploadBox');
//     const fileInput = document.getElementById('fileInput');
//     const preview = document.getElementById('preview');
//     const uploadedIcon = document.getElementById('uploadedIcon');
//     const uploadIcon = document.getElementById('uploadIcon');
//     const fileName = document.getElementById('fileName');
//     const cancelBtn = document.getElementById('cancelBtn');
//     const uploadForm = document.getElementById('uploadForm');
//     const loadingOverlay = document.getElementById('upload-loading-overlay');
//     const errorMessage = document.getElementById('error-message');

//     // Drag and Drop Functionality
//     uploadBox.addEventListener('dragover', (e) => {
//         e.preventDefault();
//         uploadBox.classList.add('highlight');
//     });

//     uploadBox.addEventListener('dragleave', () => {
//         uploadBox.classList.remove('highlight');
//     });

//     uploadBox.addEventListener('drop', (e) => {
//         e.preventDefault();
//         uploadBox.classList.remove('highlight');
//         const files = e.dataTransfer.files;
//         if (files.length > 0) {
//             fileInput.files = files;
//             previewFile(files[0]);
//         }
//     });

//     // File Input Change
//     fileInput.addEventListener('change', () => {
//         if (fileInput.files.length > 0) {
//             previewFile(fileInput.files[0]);
//         }
//     });

//     // Preview File Function
//     function previewFile(file) {
//         uploadIcon.classList.add('hidden');
//         uploadedIcon.classList.remove('hidden');
//         fileName.textContent = file.name;
//     }

//     // Cancel Button
//     cancelBtn.addEventListener('click', () => {
//         fileInput.value = '';
//         uploadIcon.classList.remove('hidden');
//         uploadedIcon.classList.add('hidden');
//         fileName.textContent = '';
//     });

//     // Form Submission with Loading Feature
//     uploadForm.addEventListener('submit', function(event) {
//         event.preventDefault();

//         // Show the loading overlay
//         loadingOverlay.style.display = 'flex';

//         // Disable the buttons to prevent multiple submissions
//         cancelBtn.disabled = true;
//         document.getElementById('uploadBtn').disabled = true;

//         // Clear any previous error messages
//         errorMessage.textContent = '';

//         // Create a FormData object to send the form data
//         const formData = new FormData(this);

//         // Get the CSRF token from the form
//         const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;

//         // Make an AJAX request to the server
//         fetch(uploadForm.action, {
//             method: 'POST',
//             body: formData,
//             headers: {
//                 'X-CSRFToken': csrfToken
//             }
//         })
//         .then(response => {
//             if (response.redirected) {
//                 // If the server redirects to the results page, follow the redirect
//                 window.location.href = response.url;
//             } else {
//                 // If there's an error, parse the JSON response
//                 return response.json().then(data => {
//                     loadingOverlay.style.display = 'none';
//                     cancelBtn.disabled = false;
//                     document.getElementById('uploadBtn').disabled = false;
//                     if (data.error) {
//                         errorMessage.textContent = data.error;
//                     }
//                 });
//             }
//         })
//         .catch(error => {
//             console.error('Error:', error);
//             loadingOverlay.style.display = 'none';
//             cancelBtn.disabled = false;
//             document.getElementById('uploadBtn').disabled = false;
//             errorMessage.textContent = 'An error occurred while processing the file.';
//         });
//     });
// });