// ui.js
import { state } from './constants.js';
import { showError, showLoading, hideLoading } from './helpers.js';
import { initializeImageData } from './data.js';

export const navigateTo = (pageNumber, elements) => {
  if (pageNumber === 1 && state.webcamStream) {
    state.webcamStream.getTracks().forEach(track => track.stop());
    state.webcamStream = null;
  }
  state.currentPage = pageNumber;
  elements.pages.forEach((page, index) => {
    page.classList.toggle('active', index === pageNumber - 1);
  });
  if (pageNumber !== 3) {
    elements.resultContainer.style.display = 'none';
  }
};

export const setupPreviewPage = (elements) => {
  elements.sourcePreview.src = state.selectedImageSrc;
  elements.targetPreview.src = state.capturedImageSrc;
};

export const loadFilteredImages = (elements) => {
  elements.imageGrid.innerHTML = '';
  const genderImages = state.categoryImages[state.selectedGender] || {};
  const images = genderImages[state.selectedCategory] || [];

  if (!images.length) {
    elements.imageGrid.innerHTML = '<p>No images found for current filters</p>';
    return;
  }

  images.forEach((image, index) => {
    const card = document.createElement('div');
    card.className = 'image-item';
    card.innerHTML = `
      <div class="image-card" style="position: relative;">
        <img src="${image}" alt="${state.selectedGender} ${state.selectedCategory} ${index + 1}" loading="lazy">
        <button class="delete-btn">Delete</button>
      </div>
    `;

    card.addEventListener('click', () => {
      document.querySelectorAll('.image-item').forEach(i => i.classList.remove('selected'));
      card.classList.add('selected');
      state.selectedImageId = `${state.selectedGender}-${state.selectedCategory}-${index}`;
      state.selectedImageSrc = image;
      elements.continueButton.disabled = false;
    });

    const deleteBtn = card.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', async (event) => {
      event.stopPropagation();
      const confirmed = confirm("Are you sure you want to delete this image?");
      if (!confirmed) return;

      // Use the extractPublicId from helpers if available, or the local implementation
      const publicId = extractPublicId(image);
      if (!publicId) {
        showError('Failed to extract public ID.', elements);
        return;
      }
      try {
        showLoading("Deleting image...", elements);
        const deleteResponse = await fetch(`/delete?public_id=${encodeURIComponent(publicId)}`, {
          method: 'DELETE'
        });
        const deleteResult = await deleteResponse.json();
        if (deleteResponse.ok) {
          card.remove();
          await updateRemainingUploads(elements);
        } else {
          showError(deleteResult.detail || "Delete failed.", elements);
        }
      } catch (err) {
        showError('Error deleting image: ' + err.message, elements);
      } finally {
        hideLoading(elements);
      }
    });

    elements.imageGrid.appendChild(card);
  });
};

export async function updateRemainingUploads(elements) {
  try {
    const data = await initializeImageData();
    state.categoryImages = data.structure;
    const totalCount = data.user_tempelets_count;
    const remaining = Math.max(30 - totalCount, 0);
    elements.remainingUploads.textContent = `Remaining uploads: ${remaining}`;
  } catch (error) {
    console.error('Error updating remaining uploads:', error);
    elements.remainingUploads.textContent = 'Remaining uploads: N/A';
  }
}

// Local implementation of extractPublicId in case it's not imported from helpers.js
function extractPublicId(url) {
  const parts = url.split('/');
  const uploadIndex = parts.indexOf('upload');
  if (uploadIndex === -1) return null;
  const path = parts.slice(uploadIndex + 2).join('/');
  return path;
}
