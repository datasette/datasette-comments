/*
 * USER SWITCHING DEBUG WIDGET
 * 
 * ORIGINAL PROMPT:
 * Create a single-file JavaScript solution (no dependencies) that adds a debugging 
 * "user switching" widget. Requirements:
 * - Widget positioned at bottom right of screen, always on top
 * - Shows current user and provides dropdown to change users
 * - Six users across two newsrooms:
 *   - Daily Planet: clark, lois, jimmy
 *   - Gotham Gazette: bruce, alfred, selina
 * - When user is selected, set cookie named "actor" to the selected user's name
 * - Include small SVG icons to distinguish between the two newsrooms
 * - Default user is clark
 * - Provide basic test index.html showing current "logged in" user
 *
 * IMPLEMENTATION DETAILS:
 * 
 * Data Structure:
 * - users array contains objects with { name, newsroom } properties
 * - Two newsrooms: 'daily-planet' and 'gotham-gazette'
 * 
 * Cookie Management:
 * - setCookie(name, value, days) - stores cookie with 365 day expiration by default
 * - getCookie(name) - retrieves cookie value
 * - Cookie name is "actor", value is the user's name (e.g., "clark")
 * 
 * Widget Components:
 * - Fixed position div at bottom: 20px, right: 20px
 * - z-index: 999999 to ensure always on top
 * - Displays: debug label, current user icon, current user name, newsroom, and dropdown
 * - Dropdown (<select>) lists all 6 users with their newsroom in parentheses
 * 
 * SVG Icons:
 * - daily-planet: Blue circle with white center (planet-like)
 * - gotham-gazette: Dark square with white X (edgier/darker theme)
 * - Icons are 16x16px, stored in icons object keyed by newsroom name
 * 
 * Functionality:
 * - getCurrentUser() reads "actor" cookie and returns matching user object (defaults to clark)
 * - createWidget() builds and injects the widget HTML into document.body
 * - Change event on dropdown updates cookie and refreshes both widget and page displays
 * - updatePageDisplay() updates elements with IDs 'current-user' and 'current-newsroom' if present
 * - Widget initializes on DOMContentLoaded event
 * 
 * Styling:
 * - Widget: white background, rounded corners, shadow, bordered
 * - Dropdown: full width, styled with padding and border radius
 * - Demo page: centered content card with user info display
 * 
 * Usage:
 * - Drop the <script> section into any HTML page
 * - Widget will appear automatically on page load
 * - User selection persists across page refreshes via cookie
 * - No external dependencies required
 */

// User data
const users = [
    { name: 'clark', newsroom: 'daily-planet' },
    { name: 'lois', newsroom: 'daily-planet' },
    { name: 'jimmy', newsroom: 'daily-planet' },
    { name: 'bruce', newsroom: 'gotham-gazette' },
    { name: 'alfred', newsroom: 'gotham-gazette' },
    { name: 'selina', newsroom: 'gotham-gazette' }
];

// Cookie utilities
function setCookie(name, value, days = 365) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    document.cookie = `${name}=${value};expires=${date.toUTCString()};path=/`;
    // refresh page
    location.reload();
}

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

// Get current user
function getCurrentUser() {
    let actorName = getCookie('actor');
    if (!actorName) {
        // No actor cookie found, set clark as default
        actorName = 'clark';
        setCookie('actor', actorName);
    }
    return users.find(u => u.name === actorName) || users[0];
}

// SVG icons for newsrooms
const icons = {
    'daily-planet': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="8" cy="8" r="6" fill="#0066cc" stroke="#004499" stroke-width="1.5"/>
        <circle cx="8" cy="8" r="2" fill="white"/>
    </svg>`,
    'gotham-gazette': `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="2" width="12" height="12" fill="#333" stroke="#000" stroke-width="1.5"/>
        <path d="M5 5 L11 11 M11 5 L5 11" stroke="#fff" stroke-width="2"/>
    </svg>`
};

// Create widget
function createWidget() {
    const widget = document.createElement('div');
    widget.id = 'user-switch-widget';
    widget.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: white;
        border: 2px solid #ddd;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 999999;
        font-family: Arial, sans-serif;
        font-size: 14px;
        min-width: 200px;
    `;

    const currentUser = getCurrentUser();

    widget.innerHTML = `
        <div style="margin-bottom: 8px; font-weight: bold; color: #666; font-size: 11px; text-transform: uppercase;">
            Debug: User Switch
        </div>
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <span id="current-icon">${icons[currentUser.newsroom]}</span>
            <span id="current-actor" style="font-weight: bold; color: #333;">${currentUser.name}</span>
            <span style="color: #999; font-size: 12px;">(${currentUser.newsroom})</span>
        </div>
        <select id="user-selector" style="
            width: 100%;
            padding: 6px 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
            background: white;
        ">
            ${users.map(user => `
                <option value="${user.name}" ${user.name === currentUser.name ? 'selected' : ''}>
                    ${user.name} (${user.newsroom})
                </option>
            `).join('')}
        </select>
    `;

    document.body.appendChild(widget);

    // Add change listener
    document.getElementById('user-selector').addEventListener('change', function(e) {
        const selectedUser = users.find(u => u.name === e.target.value);
        setCookie('actor', selectedUser.name);
        
        // Update widget display
        document.getElementById('current-icon').innerHTML = icons[selectedUser.newsroom];
        document.getElementById('current-actor').textContent = selectedUser.name;
        
        // Update main page display if elements exist
        updatePageDisplay(selectedUser);
    });
}

// Update page display
function updatePageDisplay(user) {
    const userEl = document.getElementById('current-user');
    const newsroomEl = document.getElementById('current-newsroom');
    if (userEl) userEl.textContent = user.name;
    if (newsroomEl) newsroomEl.textContent = user.newsroom;
}

// Initialize
window.addEventListener('DOMContentLoaded', function() {
    const currentUser = getCurrentUser();
    updatePageDisplay(currentUser);
    createWidget();
});