// event-listeners.js
import { state } from './constants.js';
import { showError, createSparkleBurst, showLoading, hideLoading } from './helpers.js';
import { initializeWebcam, capturePhoto, resetCapture, startCountdown } from './webcam.js';
import { processFaceSwap, processHeadSwap, showQrCode, hideQrCode } from './face-swap.js';
import { navigateTo, setupPreviewPage, loadFilteredImages } from './ui.js';

export const setupEventListeners = (elements) => {
  // Upload form submission
  elements.uploadForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!elements.uploadFileInput.files.length) {
      showError('Please select a file.', elements);
      return;
    }
    const gender = document.querySelector('input[name="gender"]:checked').value;
    const typeCategory = document.getElementById('typeCategory').value;
    const folderName = `user_tempelets/${gender}/${typeCategory}`;

    const formData = new FormData();
    formData.append('file', elements.uploadFileInput.files[0]);
    formData.append('folder', folderName);

    try {
      showLoading("Uploading file...", elements);
      const response = await fetch('/upload', {
        method: 'POST',
        body: formData
      });
      const messageEl = document.getElementById('message');
      if (!response.ok) {
        const errorData = await response.json();
        messageEl.innerHTML = 'Error: ' + errorData.detail;
        messageEl.classList.remove('success');
        messageEl.classList.add('error');
      } else {
        const result = await response.json();
        elements.uploadForm.reset();
        elements.filePreview.innerHTML = '';
        messageEl.innerHTML = `${result.message}. <a href="${result.secure_url}" target="_blank">View Upload</a>`;
        messageEl.classList.remove('error');
        messageEl.classList.add('success');
        loadFilteredImages(elements);
        await updateRemainingUploads(elements);
      }
    } catch (error) {
      showError('Error: ' + error.message, elements);
    } finally {
      hideLoading(elements);
    }
  });

  // Category pill click events
  document.querySelectorAll('.category-pills .category-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.category-pills .category-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.selectedCategory = pill.dataset.category;
      loadFilteredImages(elements);
    });
  });

  // Gender filter click events
  document.querySelectorAll('.gender-filters .category-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.gender-filters .category-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.selectedGender = pill.dataset.gender;
      loadFilteredImages(elements);
    });
  });

  // Navigation events
  document.getElementById('backButton').addEventListener('click', () => {
    navigateTo(1, elements);
  });

  elements.continueButton.addEventListener('click', () => {
    if (!state.selectedImageSrc) {
      showError('Please select an image first.', elements);
      return;
    }
    navigateTo(2, elements);
    initializeWebcam(elements);
  });

  elements.takeShotButton.addEventListener('click', () => startCountdown(elements));
  elements.resetShotButton.addEventListener('click', () => resetCapture(elements));
  elements.confirmShotButton.addEventListener('click', () => {
    if (!elements.capturePreview.src) {
      showError('No photo captured. Please take a photo first.', elements);
      return;
    }
    state.capturedImageSrc = elements.capturePreview.src;
    navigateTo(3, elements);
    setupPreviewPage(elements);
  });

  // Magic button click for face/head swap
  elements.makeMagicButton.addEventListener('click', async () => {
    if (!state.selectedImageSrc || !state.capturedImageSrc) {
      showError('Please ensure both source and target images are selected.', elements);
      return;
    }
    const operation = document.querySelector('input[name="operation"]:checked').value;
    elements.makeMagicButton.disabled = true;
    createSparkleBurst(elements.makeMagicButton, 15);
    elements.sourcePreview.classList.add('shake');
    elements.targetPreview.classList.add('shake');
    showLoading(`Creating ${operation} swap magic...`, elements);
    
    const generatingMessage = document.getElementById('generatingMessage');
    generatingMessage.classList.add('active');
  
    try {
      let result;
      if (operation === 'face') {
        result = await processFaceSwap(elements);
      } else if (operation === 'head') {
        result = await processHeadSwap(elements);
      } else {
        throw new Error('Invalid operation selected');
      }
      const { swappedImageUrl, qrCodeUrl } = result;
      state.lastSwappedUrl = swappedImageUrl;
      state.lastQrCodeUrl = qrCodeUrl;
      
      elements.sourcePreview.classList.remove('shake');
      elements.targetPreview.classList.remove('shake');
      elements.sourcePreview.classList.add('merge');
      elements.targetPreview.classList.add('merge');
      
      await new Promise(resolve => setTimeout(resolve, 800));
      document.querySelector('.preview-container').style.display = 'none';
      
      elements.finalResult.onload = () => {
        elements.resultContainer.scrollIntoView({ behavior: 'smooth' });
        elements.finalResult.classList.add('magic-animation');
        setTimeout(() => elements.finalResult.classList.remove('magic-animation'), 1000);
      };
      elements.finalResult.src = swappedImageUrl;
      elements.resultContainer.style.display = 'block';
      elements.resultContainer.classList.add('active');
    } catch (error) {
      console.error(`${operation} swap error:`, error);
      showError(error.message || `Failed to create ${operation} swap. Please try again.`, elements);
    } finally {
      generatingMessage.classList.remove('active');
      elements.makeMagicButton.disabled = false;
      hideLoading(elements);
    }
  });

  // Print result event
  document.getElementById('printResult').addEventListener('click', () => {
    if (!elements.finalResult.src) {
      showError('No result available to print.', elements);
      return;
    }
    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    document.body.appendChild(iframe);
    const iframeDoc = iframe.contentWindow.document;
    iframeDoc.open();
    iframeDoc.write(`
      <html>
        <head>
          <style>
            @media print {
              @page { margin: 0; size: auto; }
              body { margin: 0; background: none; }
              img { width: 100vw; height: 100vh; object-fit: contain; }
            }
            html, body {
              margin: 0;
              padding: 0;
              background: none;
              width: 100%;
              height: 100%;
            }
            img {
              position: absolute;
              top: 0;
              left: 0;
              width: 100%;
              height: 100%;
              object-fit: contain;
            }
          </style>
        </head>
        <body>
          <img src="${elements.finalResult.src}">
        </body>
      </html>
    `);
    iframeDoc.close();
    iframe.contentWindow.focus();
    iframe.contentWindow.print();
    setTimeout(() => {
      document.body.removeChild(iframe);
    }, 1000);
  });

  // Redo event
  document.getElementById('redo').addEventListener('click', () => {
    navigateTo(1, elements);
    state.selectedImageId = null;
    state.selectedImageSrc = null;
    state.capturedImageSrc = null;
    elements.continueButton.disabled = true;
    elements.resultContainer.style.display = 'none';
    document.querySelector('.preview-container').style.display = 'flex';
    elements.sourcePreview.classList.remove('merge');
    elements.targetPreview.classList.remove('merge');
    document.querySelectorAll('.image-item').forEach(item => {
      item.classList.remove('selected');
    });
    elements.makeMagicButton.disabled = false;
  });

  // Download result event
  document.getElementById('downloadResult').addEventListener('click', () => {
    if (!elements.finalResult.src) {
      showError('No image available to download.', elements);
      return;
    }
    const link = document.createElement('a');
    link.href = elements.finalResult.src;
    link.download = 'face-swap-result.jpg';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  });

  // QR Code events
  document.getElementById('showQRCodeButton').addEventListener('click', () => showQrCode(elements));
  document.querySelector('#qrCodePopup .close').addEventListener('click', () => hideQrCode(elements));
  window.addEventListener('click', (event) => {
    if (event.target === elements.qrCodePopup) {
      hideQrCode(elements);
    }
  });
};
