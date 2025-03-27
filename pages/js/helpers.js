// helpers.js
import { state } from './constants.js';

export const extractPublicId = (url) => {
  const uploadIndex = url.indexOf('/upload/');
  if (uploadIndex === -1) return null;
  let subStr = url.substring(uploadIndex + 8);
  if (subStr.startsWith('v')) {
    const slashIndex = subStr.indexOf('/');
    if (slashIndex !== -1) {
      subStr = subStr.substring(slashIndex + 1);
    }
  }
  const dotIndex = subStr.lastIndexOf('.');
  if (dotIndex !== -1) {
    subStr = subStr.substring(0, dotIndex);
  }
  return subStr;
};

export const dataURLtoFile = (dataurl, filename) => {
  const arr = dataurl.split(',');
  const mimeMatch = arr[0].match(/:(.*?);/);
  if (!mimeMatch) throw new Error('Invalid MIME type');
  const mime = mimeMatch[1];
  const bstr = atob(arr[1]);
  const u8arr = new Uint8Array(bstr.length);
  for (let i = 0; i < bstr.length; i++) {
    u8arr[i] = bstr.charCodeAt(i);
  }
  return new File([u8arr], filename, { type: mime });
};

export const showLoading = (message, elements) => {
  elements.loadingText.textContent = message || 'Loading...';
  elements.loadingOverlay.style.display = 'flex';
};

export const hideLoading = (elements) => {
  elements.loadingOverlay.style.display = 'none';
};

export const showError = (message, elements) => {
  elements.errorMessage.textContent = message;
  elements.errorMessage.style.display = 'block';
  setTimeout(() => { elements.errorMessage.style.display = 'none'; }, 5000);
};

export const createSparkleBurst = (element, count = 10) => {
  for (let i = 0; i < count; i++) createSparkle(element);
};

// Implementation of a basic sparkle effect
const createSparkle = (element) => {
  const sparkle = document.createElement('div');
  sparkle.className = 'sparkle';
  sparkle.style.position = 'absolute';
  sparkle.style.width = '5px';
  sparkle.style.height = '5px';
  sparkle.style.background = 'yellow';
  sparkle.style.borderRadius = '50%';
  const rect = element.getBoundingClientRect();
  sparkle.style.left = `${rect.left + Math.random() * rect.width}px`;
  sparkle.style.top = `${rect.top + Math.random() * rect.height}px`;
  document.body.appendChild(sparkle);
  setTimeout(() => sparkle.remove(), 500);
};

export const showConfirmationDialog = (message) => {
  return new Promise((resolve) => {
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.backgroundColor = 'rgba(0,0,0,0.5)';
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';
    overlay.style.zIndex = '10000';

    const modalBox = document.createElement('div');
    modalBox.style.background = '#fff';
    modalBox.style.padding = '20px';
    modalBox.style.borderRadius = '8px';
    modalBox.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
    modalBox.style.maxWidth = '400px';
    modalBox.style.width = '80%';
    modalBox.style.textAlign = 'center';

    const messageEl = document.createElement('p');
    messageEl.textContent = message;
    messageEl.style.marginBottom = '20px';
    messageEl.style.fontSize = '16px';

    const buttonsContainer = document.createElement('div');
    buttonsContainer.style.display = 'flex';
    buttonsContainer.style.justifyContent = 'space-around';

    const cancelButton = document.createElement('button');
    cancelButton.textContent = 'Cancel';
    cancelButton.style.padding = '10px 20px';
    cancelButton.style.background = '#ccc';
    cancelButton.style.border = 'none';
    cancelButton.style.borderRadius = '4px';
    cancelButton.style.cursor = 'pointer';

    const confirmButton = document.createElement('button');
    confirmButton.textContent = 'Delete';
    confirmButton.style.padding = '10px 20px';
    confirmButton.style.background = '#e74c3c';
    confirmButton.style.color = '#fff';
    confirmButton.style.border = 'none';
    confirmButton.style.borderRadius = '4px';
    confirmButton.style.cursor = 'pointer';

    buttonsContainer.appendChild(cancelButton);
    buttonsContainer.appendChild(confirmButton);
    modalBox.appendChild(messageEl);
    modalBox.appendChild(buttonsContainer);
    overlay.appendChild(modalBox);
    document.body.appendChild(overlay);

    cancelButton.addEventListener('click', () => {
      document.body.removeChild(overlay);
      resolve(false);
    });
    confirmButton.addEventListener('click', () => {
      document.body.removeChild(overlay);
      resolve(true);
    });
  });
};
