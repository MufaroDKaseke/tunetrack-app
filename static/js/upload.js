document.addEventListener('DOMContentLoaded', function() {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('fileElem');
    const selectedFileInfo = document.getElementById('selected-file');
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Highlight drop area when file is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.querySelector('.file-input-wrapper').classList.add('highlight');
    }
    
    function unhighlight() {
        dropArea.querySelector('.file-input-wrapper').classList.remove('highlight');
    }
    
    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            fileInput.files = files;
            updateFileInfo(files[0]);
        }
    }
    
    // Handle selected files through the file input
    fileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            updateFileInfo(this.files[0]);
        }
    });
    
    // Update file information display
    function updateFileInfo(file) {
        const fileSize = formatFileSize(file.size);
        const fileName = file.name;
        const fileType = file.type;
        
        let html = `
            <p><strong>File:</strong> ${fileName}</p>
            <p><strong>Type:</strong> ${fileType}</p>
            <p><strong>Size:</strong> ${fileSize}</p>
        `;
        
        selectedFileInfo.innerHTML = html;
    }
    
    // Format file size
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
});
