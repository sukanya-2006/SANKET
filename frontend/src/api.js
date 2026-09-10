const BASE_URL =
  import.meta.env?.VITE_API_URL ||
  (window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://sanket-backend-put3.onrender.com');
    
export const api = {
  analyzeReport: async (text) => {
    const res = await fetch(`${BASE_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ report_text: text })
    });
    return res.json();
  },
  getReports: async (limit = 20, offset = 0) => {
    const res = await fetch(`${BASE_URL}/reports?limit=${limit}&offset=${offset}`);
    return res.json();
  },
  getSummary: async () => {
    const res = await fetch(`${BASE_URL}/aggregate/summary`);
    return res.json();
  },
  getSites: async () => {
    const res = await fetch(`${BASE_URL}/aggregate/sites`);
    return res.json();
  },
  updateReportStatus: async (reportId, status) => {
    const res = await fetch(`${BASE_URL}/reports/${reportId}/status`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    // Unlike the functions above, this one throws on a non-2xx response.
    // handleAction's try/catch in AdminTriage.jsx depends on this to tell a
    // real failure (404, 500) apart from a successful update - without this
    // check, fetch() resolves normally even on an error status, and the
    // error body would get treated as a successful result.
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Failed to update status (${res.status})`);
    }
    return res.json();
  }
};