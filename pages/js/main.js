// main.js
import { state } from './constants.js';
import { setupEventListeners } from './event-listeners.js';
import { navigateTo, updateRemainingUploads, loadFilteredImages } from './ui.js';
import { showError, showLoading, hideLoading } from './helpers.js';
import { setupApp } from './setup.js'; // Imported setupApp

function initializeApp() {
    const elements = {
        pages: document.querySelectorAll('.page'),
        imageGrid: document.getElementById('imageGrid'),
        continueButton: document.getElementById('continueToCapture'),
        video: document.getElementById('webcamVideo'),
        canvas: document.getElementById('captureCanvas'),
        capturePreview: document.getElementById('capturePreview'),
        takeShotButton: document.getElementById('takeShot'),
        resetShotButton: document.getElementById('resetShot'),
        confirmShotButton: document.getElementById('confirmShot'),
        sourcePreview: document.getElementById('sourcePreview'),
        targetPreview: document.getElementById('targetPreview'),
        makeMagicButton: document.getElementById('makeMagic'),
        resultContainer: document.getElementById('resultContainer'),
        finalResult: document.getElementById('finalResult'),
        loadingOverlay: document.getElementById('loadingOverlay'),
        loadingText: document.getElementById('loadingText'),
        errorMessage: document.getElementById('errorMessage'),
        uploadForm: document.getElementById('uploadForm'),
        uploadFileInput: document.getElementById('fileInput'),
        filePreview: document.getElementById('filePreview'),
        qrCodePopup: document.getElementById('qrCodePopup'),
        qrCodeImage: document.getElementById('qrCodeImage'),
        remainingUploads: document.getElementById('remainingUploads'),
        timerDisplay: document.getElementById('timerDisplay')
    };

    try {
        showLoading('Loading images...', elements);
        updateRemainingUploads(elements)
            .then(() => {
                setupEventListeners(elements);
                loadFilteredImages(elements);
            });
    } catch (error) {
        showError('Failed to initialize: ' + error.message, elements);
    } finally {
        hideLoading(elements);
    }
}

function autoLogin() {
    const deviceKey = localStorage.getItem('deviceKey');
    if (deviceKey) {
        fetch('/api/autologin', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device_key: deviceKey })
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Auto login failed');
                }
                return response.json();
            })
            .then(data => {
                localStorage.setItem('token', data.token);
                localStorage.setItem('email', data.email);
                localStorage.setItem('name', data.name);
                setupApp(); // Calls the imported setupApp
            })
            .catch(error => {
                console.error('Auto login error:', error);
                window.location.href = '/static/login.html';
            });
    } else {
        const token = localStorage.getItem('token');
        if (token) {
            setupApp(); // Calls the imported setupApp
        } else {
            window.location.href = '/static/login.html';
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    autoLogin();
    initializeApp(); // Call the new initialization function
});