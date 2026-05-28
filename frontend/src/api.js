// API Utility for Breathe ESG Ingestor

// Base URL detection
export const API_BASE = import.meta.env.DEV 
  ? 'http://localhost:8000' 
  : `${window.location.origin}/_/backend`;

// Pre-seeded Analyst User Token (seeded via management command)
const ANALYST_TOKEN = 'f8df9911f1c56734ef297ada95eda525128b5c15';
export const CURRENT_USER = {
  username: 'analyst',
  email: 'analyst@breatheesg.com',
  token: ANALYST_TOKEN
};

// Default tenant slug
export const DEFAULT_TENANT = {
  name: 'Breathe Industries Ltd',
  slug: 'breathe-ind'
};

/**
 * Standard fetch wrapper with auth token and tenant headers.
 */
export async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  
  const headers = {
    'Authorization': `Token ${CURRENT_USER.token}`,
    'X-Tenant-Slug': DEFAULT_TENANT.slug,
    ...options.headers
  };

  // If body is not FormData, set Content-Type to JSON
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const response = await fetch(url, {
    ...options,
    headers
  });

  if (!response.ok) {
    let errMsg = `API Error: ${response.statusText}`;
    try {
      const errData = await response.json();
      errMsg = errData.error || errData.detail || JSON.stringify(errData);
    } catch (_) {}
    throw new Error(errMsg);
  }

  // Return json or null
  if (response.status === 204) return null;
  return await response.json();
}
