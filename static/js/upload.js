document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const selectButton = document.getElementById('selectButton');
    const uploadForm = document.getElementById('uploadForm');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const convertButton = document.getElementById('convertButton');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const errorContainer = document.getElementById('errorContainer');
    const errorMessage = document.getElementById('errorMessage');
    const downloadContainer = document.getElementById('downloadContainer');
    const downloadLink = document.getElementById('downloadLink');

    // Handle drag and drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        });
    });

    // Handle file drop
    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        handleFiles(files);
    });

    // Handle file selection via button
    selectButton.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const file = files[0];
            if (file.name.toLowerCase().endsWith('.m4a')) {
                fileInput.files = files;
                showFileInfo(file.name);
            } else {
                showError('Please select a valid M4A file');
            }
        }
    }

    function showFileInfo(name) {
        fileName.textContent = name;
        fileInfo.classList.remove('d-none');
        errorContainer.classList.add('d-none');
        downloadContainer.classList.add('d-none');
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorContainer.classList.remove('d-none');
        fileInfo.classList.add('d-none');
        downloadContainer.classList.add('d-none');
    }

    // Handle conversion
    convertButton.addEventListener('click', () => {
        const formData = new FormData(uploadForm);
        
        progressContainer.classList.remove('d-none');
        progressBar.style.width = '0%';
        downloadContainer.classList.add('d-none');
        
        // Simulate progress while converting
        let progress = 0;
        const interval = setInterval(() => {
            progress += 5;
            if (progress <= 90) {
                progressBar.style.width = progress + '%';
            }
        }, 500);

        // Submit form via AJAX
        fetch(uploadForm.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            clearInterval(interval);
            progressBar.style.width = '100%';
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Log download URL for debugging
            console.log('Download URL:', data.download_url);
            
            // Setup download link with target="_blank"
            downloadLink.href = data.download_url;
            downloadLink.setAttribute('target', '_blank');
            downloadLink.download = data.filename;
            
            // Add click handler for download link
            downloadLink.onclick = function(e) {
                e.preventDefault();
                try {
                    console.log('Initiating download for:', data.filename);
                    window.open(data.download_url, '_blank');
                } catch (err) {
                    console.error('Download error:', err);
                    showError('Error initiating download. Please try again.');
                }
            };
            
            downloadContainer.classList.remove('d-none');
            
            // Reset form
            fileInfo.classList.add('d-none');
            setTimeout(() => {
                progressContainer.classList.add('d-none');
                progressBar.style.width = '0%';
                uploadForm.reset();
            }, 1000);
        })
        .catch(error => {
            console.error('Conversion error:', error);
            clearInterval(interval);
            progressContainer.classList.add('d-none');
            showError(error.message || 'An error occurred during conversion');
        });
    });
});
