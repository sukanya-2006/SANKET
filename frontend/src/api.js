const BASE_URL = 'http://localhost:8000';

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
  }
};
