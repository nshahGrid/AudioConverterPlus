document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const selectButton = document.getElementById('selectButton');
    const uploadForm = document.getElementById('uploadForm');
    const fileList = document.getElementById('fileList');
    const selectedFiles = document.getElementById('selectedFiles');
    const convertButton = document.getElementById('convertButton');
    const batchProgress = document.getElementById('batchProgress');
    const totalProgressBar = document.getElementById('totalProgressBar');
    const currentProgressBar = document.getElementById('currentProgressBar');
    const currentFileName = document.getElementById('currentFileName');
    const errorContainer = document.getElementById('errorContainer');
    const errorMessage = document.getElementById('errorMessage');
    const completedFiles = document.getElementById('completedFiles');
    const downloadLinks = document.getElementById('downloadLinks');

    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

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
            const validFiles = Array.from(files).filter(file => {
                const extension = file.name.split('.').pop().toLowerCase();
                return ['m4a', 'wav', 'aac', 'wma', 'ogg', 'flac'].includes(extension);
            });

            if (validFiles.length === 0) {
                showError('Please select valid audio files (M4A, WAV, AAC, WMA, OGG, FLAC)');
                return;
            }

            // Update UI with selected files
            selectedFiles.innerHTML = '';
            validFiles.forEach(file => {
                const li = document.createElement('li');
                li.textContent = file.name;
                selectedFiles.appendChild(li);
            });

            fileList.classList.remove('d-none');
            errorContainer.classList.add('d-none');
            completedFiles.classList.add('d-none');
            
            // Update file input with valid files only
            const dt = new DataTransfer();
            validFiles.forEach(file => dt.items.add(file));
            fileInput.files = dt.files;
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorContainer.classList.remove('d-none');
        fileList.classList.add('d-none');
        completedFiles.classList.add('d-none');
    }

    // Handle batch conversion
    convertButton.addEventListener('click', async () => {
        const files = fileInput.files;
        const bitrate = document.getElementById('bitrate').value;
        const samplerate = document.getElementById('samplerate').value;
        const channels = document.getElementById('channels').value;
        
        if (files.length === 0) {
            showError('Please select files to convert');
            return;
        }

        batchProgress.classList.remove('d-none');
        downloadLinks.innerHTML = '';
        completedFiles.classList.add('d-none');
        
        let completedCount = 0;
        const totalFiles = files.length;

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append('file', file);
            formData.append('bitrate', bitrate);
            formData.append('samplerate', samplerate);
            formData.append('channels', channels);

            // Update progress indicators
            currentFileName.textContent = file.name;
            currentProgressBar.style.width = '0%';
            totalProgressBar.style.width = `${(completedCount / totalFiles) * 100}%`;

            try {
                // Simulate file conversion progress
                let progress = 0;
                const interval = setInterval(() => {
                    progress += 5;
                    if (progress <= 90) {
                        currentProgressBar.style.width = `${progress}%`;
                    }
                }, 500);

                // Submit form for current file
                const response = await fetch(uploadForm.action, {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                clearInterval(interval);

                if (!response.ok) {
                    throw new Error(data.error || 'Conversion failed');
                }

                // Update progress for completed file
                currentProgressBar.style.width = '100%';
                completedCount++;
                totalProgressBar.style.width = `${(completedCount / totalFiles) * 100}%`;

                // Add download link
                const li = document.createElement('li');
                li.innerHTML = `<a href="${data.download_url}" class="download-link" 
                               data-filename="${data.filename}">${file.name} → ${data.filename}</a>`;
                downloadLinks.appendChild(li);
                completedFiles.classList.remove('d-none');

            } catch (error) {
                console.error('Conversion error:', error);
                showError(`Error converting ${file.name}: ${error.message}`);
                break;
            }
        }

        // Reset form after all files are processed
        if (completedCount === totalFiles) {
            setTimeout(() => {
                batchProgress.classList.add('d-none');
                fileList.classList.add('d-none');
                uploadForm.reset();
            }, 1000);
        }
    });

    // Handle download links
    downloadLinks.addEventListener('click', (e) => {
        if (e.target.classList.contains('download-link')) {
            e.preventDefault();
            const link = document.createElement('a');
            link.href = e.target.href;
            link.download = e.target.dataset.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    });
});
