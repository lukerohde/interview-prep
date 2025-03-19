/**
 * Helper function to make POST requests with CSRF token
 * @param {string} url - URL to post to
 * @param {Object} data - Data to send
 * @param {string} csrfToken - CSRF token
 * @param {string} method - HTTP method (default: 'POST')
 * @returns {Promise} - Fetch promise
 */
export async function postWithToken(url, data, csrfToken, method = 'POST') {
    if (!csrfToken) {
        throw new Error('CSRF token not found');
    }

    return fetch(url, {
        method: method,
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(data)
    });
}
