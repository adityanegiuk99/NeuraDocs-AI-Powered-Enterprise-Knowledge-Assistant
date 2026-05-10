/**
 * API service — centralized HTTP client for backend communication.
 * Handles JWT token attachment, refresh logic, and error formatting.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API = `${API_BASE}/api/v1`;

function getTokens() {
  return {
    access: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),
  };
}

function setTokens(access, refresh) {
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

async function request(endpoint, options = {}) {
  const { access } = getTokens();
  const headers = { ...options.headers };

  if (access) {
    headers['Authorization'] = `Bearer ${access}`;
  }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API}${endpoint}`, { ...options, headers });

  if (res.status === 401) {
    // Try refresh
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${getTokens().access}`;
      const retry = await fetch(`${API}${endpoint}`, { ...options, headers });
      if (!retry.ok) throw await formatError(retry);
      if (retry.status === 204) return null;
      return retry.json();
    }
    clearTokens();
    window.location.href = '/login';
    throw new Error('Session expired');
  }

  if (!res.ok) throw await formatError(res);
  if (res.status === 204) return null;
  return res.json();
}

async function tryRefresh() {
  const { refresh } = getTokens();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

async function formatError(res) {
  try {
    const data = await res.json();
    return new Error(data.detail || `Request failed (${res.status})`);
  } catch {
    return new Error(`Request failed (${res.status})`);
  }
}

// ── Auth ──
export const auth = {
  register: (data) => request('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: async (email, password) => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setTokens(data.access_token, data.refresh_token);
    return data;
  },
  me: () => request('/auth/me'),
  logout: () => clearTokens(),
};

// ── Chat ──
export const chat = {
  query: (query, conversationId = null, filters = null) =>
    request('/chat/query', {
      method: 'POST',
      body: JSON.stringify({ query, conversation_id: conversationId, filters }),
    }),
  createConversation: (title) =>
    request('/chat/conversations', { method: 'POST', body: JSON.stringify({ title }) }),
  listConversations: () => request('/chat/conversations'),
  getHistory: (conversationId) => request(`/chat/history/${conversationId}`),
  submitFeedback: (queryLogId, rating, text = null) =>
    request('/chat/feedback', {
      method: 'POST',
      body: JSON.stringify({ query_log_id: queryLogId, rating, feedback_text: text }),
    }),
};

// ── Documents ──
export const documents = {
  upload: (file, metadata = {}) => {
    const form = new FormData();
    form.append('file', file);
    if (metadata.department) form.append('department', metadata.department);
    if (metadata.doc_type) form.append('doc_type', metadata.doc_type);
    if (metadata.author) form.append('author', metadata.author);
    if (metadata.tags) form.append('tags', metadata.tags);
    return request('/documents/upload', { method: 'POST', body: form });
  },
  list: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/documents/${q ? '?' + q : ''}`);
  },
  get: (id) => request(`/documents/${id}`),
  updateMetadata: (id, data) =>
    request(`/documents/${id}/metadata`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id) => request(`/documents/${id}`, { method: 'DELETE' }),
};

// ── Admin ──
export const admin = {
  health: () => request('/admin/health'),
  listUsers: () => request('/admin/users'),
  updateUser: (id, data) =>
    request(`/admin/users/${id}/role`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteUser: (id) => request(`/admin/users/${id}`, { method: 'DELETE' }),
  queryAnalytics: () => request('/admin/analytics/queries'),
  queryLogs: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/admin/analytics/logs${q ? '?' + q : ''}`);
  },
};
