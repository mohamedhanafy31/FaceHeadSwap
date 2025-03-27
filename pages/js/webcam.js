import { state } from './constants.js';
import { showError } from './helpers.js';

export const initializeWebcam = async (elements) => {
    try {
        state.webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
        elements.video.srcObject = state.webcamStream;
    } catch (error) {
        showError('Failed to access webcam: ' + error.message, elements);
    }
};

export const capturePhoto = (elements) => {
    const context = elements.canvas.getContext('2d');
    elements.canvas.width = elements.video.videoWidth;
    elements.canvas.height = elements.video.videoHeight;
    context.drawImage(elements.video, 0, 0);
    elements.capturePreview.src = elements.canvas.toDataURL('image/jpeg');
    elements.capturePreview.style.display = 'block';
    elements.video.style.display = 'none';
    elements.resetShotButton.disabled = false;
    elements.confirmShotButton.disabled = false;
};

export const startCountdown = (elements) => {
    // Show the timer display and initialize the count
    elements.timerDisplay.style.display = 'block';
    let count = 5;
    elements.timerDisplay.textContent = count;

    // Start a countdown interval
    const interval = setInterval(() => {
        count--;
        elements.timerDisplay.textContent = count;

        if (count <= 0) {
            clearInterval(interval);
            // Hide the timer display once done
            elements.timerDisplay.style.display = 'none';
            // Now capture the photo
            capturePhoto(elements);
        }
    }, 1000); // 1000ms = 1 second interval
};


export const resetCapture = (elements) => {
    elements.capturePreview.src = '';
    elements.capturePreview.style.display = 'none';
    elements.video.style.display = 'block';
    elements.resetShotButton.disabled = true;
    elements.confirmShotButton.disabled = true;
};