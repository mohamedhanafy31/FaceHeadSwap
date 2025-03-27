// data.js
export async function initializeImageData() {
  try {
    const response = await fetch('/api/images');
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    // Expected format: { structure: { ... }, user_tempelets_count: number }
    return data;
  } catch (error) {
    console.error('Failed to load images:', error);
    // Return a default structure in case of failure
    return { structure: {}, user_tempelets_count: 0 };
  }
}
