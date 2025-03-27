// setup.js
export function setupApp() {
    console.log("App setup initiated");
    // Check if 'content' element exists, if not, it will cause an error
    const contentElement = document.getElementById('content');
    if (contentElement) {
        contentElement.innerHTML = `
            <p>Welcome, ${localStorage.getItem('name') || 'User'}!</p>
            <button onclick="window.location.href='/static/login.html'">Logout</button>
        `;
    } else {
        console.error("Element with id 'content' not found");
    }
}