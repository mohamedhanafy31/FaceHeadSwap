// face-swap.js
import { state } from './constants.js';
import { showError, dataURLtoFile } from './helpers.js';

// Process Face Swap
export const processFaceSwap = async (elements) => {
  try {
    const formData = new FormData();
    const selectedImageFile = await fetchSelectedImage(state.selectedImageSrc);
    formData.append('target', selectedImageFile);
    const capturedImageFile = dataURLtoFile(state.capturedImageSrc, 'capture.jpg');
    formData.append('source', capturedImageFile);

    const mode = document.getElementById('imageMode').value;
    const token = localStorage.getItem('token');
    const response = await fetch(`${state.apiBaseUrl}/api/swap-face-qr/?mode=${mode}&token=${token}`, {
        method: 'POST',
        body: formData
    });
    
    
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }
    const resultJson = await response.json();
    const swappedImageUrl = resultJson.swapped_image_url;
    const qrCodeUrl = resultJson.qr_code;
    if (!swappedImageUrl || !qrCodeUrl) {
      throw new Error('No image URL or QR code received from server');
    }
    return { swappedImageUrl, qrCodeUrl };
  } catch (error) {
    showError(error.message, elements);
    throw error;
  }
};

// Process Head Swap
export const processHeadSwap = async (elements) => {
    try {
      if (!state.selectedImageSrc || !state.capturedImageSrc) {
        throw new Error('Please select both a source image and capture a photo');
      }
      const formData = new FormData();
      const selectedImageFile = await fetchSelectedImage(state.selectedImageSrc);
      formData.append('target', selectedImageFile);
      const capturedImageFile = dataURLtoFile(state.capturedImageSrc, 'capture.jpg');
      formData.append('source', capturedImageFile);
  
      const mode = document.getElementById('imageMode').value;
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found. Please register or log in.');
      }
  
      const response = await fetch(`${state.apiBaseUrl}/api/headswap-qr/?mode=${mode}&token=${token}`, {
        method: 'POST',
        body: formData
      });
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error: ${response.status} - ${errorText}`);
      }
      const resultJson = await response.json();
      const swappedImageUrl = resultJson.swapped_image_url;
      const qrCodeUrl = resultJson.qr_code;
      if (!swappedImageUrl || !qrCodeUrl) {
        throw new Error('No image URL or QR code received from server');
      }
      return { swappedImageUrl, qrCodeUrl };
    } catch (error) {
      showError(error.message, elements);
      throw error;
    }
  };

// Helper function to fetch the selected image as a blob and return as a File
async function fetchSelectedImage(url) {
  if (!url) {
    throw new Error('Selected image URL is undefined');
  }
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch image: ${response.statusText}`);
  }
  const blob = await response.blob();
  return new File([blob], 'selected.jpg', { type: blob.type });
}

export const showQrCode = (elements) => {
  if (!state.lastQrCodeUrl) {
    showError('No QR code available', elements);
    return;
  }
  elements.qrCodeImage.src = state.lastQrCodeUrl;
  elements.qrCodeImage.style.display = 'block';
  elements.qrCodePopup.style.display = 'block';
};

export const hideQrCode = (elements) => {
  elements.qrCodePopup.style.display = 'none';
};
