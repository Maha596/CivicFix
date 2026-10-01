/**
 * CivicFix - Main Client Application Logic
 * Integrates Leaflet Geolocation Map, Drag-and-Drop Image Preview,
 * Live Computer Vision AI Classification via REST API, and Navigation Interactions.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Mobile Navigation Toggle
    var navToggle = document.getElementById('navToggle');
    var navMenu = document.getElementById('navMenu');
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function () {
            navMenu.classList.toggle('active');
        });
    }

    // 2. User Profile Dropdown
    var userMenuBtn = document.getElementById('userMenuBtn');
    var userDropdownPanel = document.getElementById('userDropdownPanel');
    if (userMenuBtn && userDropdownPanel) {
        userMenuBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            userDropdownPanel.classList.toggle('show');
        });

        document.addEventListener('click', function (e) {
            if (!userMenuBtn.contains(e.target) && !userDropdownPanel.contains(e.target)) {
                userDropdownPanel.classList.remove('show');
            }
        });
    }
});

/* ================= REPORT ISSUE: LEAFLET MAP PICKER ================= */
var reportMap = null;
var reportMarker = null;

function initReportIssueMap() {
    var mapEl = document.getElementById('mapPicker');
    if (!mapEl) return;

    // Coimbatore Municipal Center
    var defaultLat = 11.0168;
    var defaultLon = 76.9558;

    reportMap = L.map('mapPicker').setView([defaultLat, defaultLon], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(reportMap);

    reportMarker = L.marker([defaultLat, defaultLon], { draggable: true }).addTo(reportMap);

    function updateCoordinates(lat, lon) {
        document.getElementById('latitude').value = lat.toFixed(6);
        document.getElementById('longitude').value = lon.toFixed(6);
        document.getElementById('locStatusText').innerHTML = 
            '<span style="color:#10b981; font-weight:600;"><i class="fa-solid fa-check"></i> Geotagged: ' + lat.toFixed(4) + ', ' + lon.toFixed(4) + '</span>';
    }

    // Set initial coordinates
    updateCoordinates(defaultLat, defaultLon);

    // Marker drag event
    reportMarker.on('dragend', function (e) {
        var pos = reportMarker.getLatLng();
        updateCoordinates(pos.lat, pos.lng);
    });

    // Map click event
    reportMap.on('click', function (e) {
        reportMarker.setLatLng(e.latlng);
        updateCoordinates(e.latlng.lat, e.latlng.lng);
    });

    // Detect Current Location Button
    var btnDetect = document.getElementById('btnDetectLocation');
    if (btnDetect) {
        btnDetect.addEventListener('click', function () {
            var statusEl = document.getElementById('locStatusText');
            if (!navigator.geolocation) {
                statusEl.innerHTML = '<span class="text-danger"><i class="fa-solid fa-triangle-exclamation"></i> Geolocation is not supported by your browser.</span>';
                return;
            }

            statusEl.innerHTML = '<span class="text-primary"><i class="fa-solid fa-circle-notch fa-spin"></i> Detecting current GPS coordinates...</span>';
            btnDetect.disabled = true;

            navigator.geolocation.getCurrentPosition(
                function (position) {
                    var curLat = position.coords.latitude;
                    var curLon = position.coords.longitude;
                    reportMap.setView([curLat, curLon], 16);
                    reportMarker.setLatLng([curLat, curLon]);
                    updateCoordinates(curLat, curLon);
                    btnDetect.disabled = false;
                },
                function (error) {
                    statusEl.innerHTML = '<span class="text-warning"><i class="fa-solid fa-triangle-exclamation"></i> Location access denied or unavailable. Please click on the map to set pin.</span>';
                    btnDetect.disabled = false;
                },
                { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
            );
        });
    }
}

/* ================= REPORT ISSUE: IMAGE UPLOAD & LIVE AI ================= */
function initImageUploadAI() {
    var dropZone = document.getElementById('dropZone');
    var imageInput = document.getElementById('imageInput');
    var dropContent = document.getElementById('dropContent');
    var previewContainer = document.getElementById('previewContainer');
    var imagePreview = document.getElementById('imagePreview');
    var removeImgBtn = document.getElementById('removeImgBtn');

    var aiResultCard = document.getElementById('aiResultCard');
    var aiStatusText = document.getElementById('aiStatusText');
    var aiCardBody = document.getElementById('aiCardBody');
    var predCategory = document.getElementById('predCategory');
    var predConfidence = document.getElementById('predConfidence');
    var confProgressBar = document.getElementById('confProgressBar');
    var aiExplanation = document.getElementById('aiExplanation');
    var categorySelect = document.getElementById('categorySelect');

    if (!dropZone || !imageInput) return;

    // Drag over styling
    ['dragenter', 'dragover'].forEach(function (eventName) {
        dropZone.addEventListener(eventName, function (e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(function (eventName) {
        dropZone.addEventListener(eventName, function (e) {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', function (e) {
        var dt = e.dataTransfer;
        var files = dt.files;
        if (files && files.length > 0) {
            imageInput.files = files;
            handleImageSelected(files[0]);
        }
    });

    imageInput.addEventListener('change', function () {
        if (imageInput.files && imageInput.files.length > 0) {
            handleImageSelected(imageInput.files[0]);
        }
    });

    if (removeImgBtn) {
        removeImgBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            imageInput.value = '';
            imagePreview.src = '#';
            previewContainer.style.display = 'none';
            dropContent.style.display = 'block';
            aiResultCard.style.display = 'none';
        });
    }

    function handleImageSelected(file) {
        if (!file.type.match('image.*')) {
            alert('Please select an image file (PNG, JPG, JPEG, WEBP).');
            return;
        }

        // 1. Show client preview
        var reader = new FileReader();
        reader.onload = function (e) {
            imagePreview.src = e.target.result;
            dropContent.style.display = 'none';
            previewContainer.style.display = 'block';
        };
        reader.readAsDataURL(file);

        // 2. Perform Live AI Classification Request
        aiResultCard.style.display = 'block';
        aiCardBody.style.display = 'none';
        aiStatusText.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Analyzing image features via Computer Vision...';

        var formData = new FormData();
        formData.append('image', file);

        fetch('/api/classify-image', {
            method: 'POST',
            body: formData
        })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (data.success) {
                aiStatusText.innerHTML = '<span style="color:#10b981;"><i class="fa-solid fa-circle-check"></i> Analysis Complete</span>';
                aiCardBody.style.display = 'block';

                predCategory.innerText = data.predicted_category;
                predConfidence.innerText = data.confidence + '%';
                confProgressBar.style.width = data.confidence + '%';
                aiExplanation.innerText = data.explanation;

                // Auto-select category in dropdown
                if (categorySelect) {
                    for (var i = 0; i < categorySelect.options.length; i++) {
                        if (categorySelect.options[i].value.toLowerCase() === data.predicted_category.toLowerCase()) {
                            categorySelect.selectedIndex = i;
                            break;
                        }
                    }
                }
            } else {
                aiStatusText.innerHTML = '<span class="text-warning"><i class="fa-solid fa-triangle-exclamation"></i> ' + (data.error || 'AI classification unavailable') + '</span>';
            }
        })
        .catch(function (err) {
            console.error('AI Classification API Error:', err);
            aiStatusText.innerHTML = '<span class="text-warning"><i class="fa-solid fa-circle-info"></i> Standard visual feature fallback applied.</span>';
        });
    }
}
