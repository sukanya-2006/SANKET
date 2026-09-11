const BASE_URL =
  import.meta.env?.VITE_API_URL ||
  (window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'https://sanket-backend-put3.onrender.com');


async function handleResponse(res) {
  const body = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new Error(
      body.detail || `Request failed (${res.status})`
    );
  }

  return body;
}


export const api = {

  // ----------------------------------------
  // CLASSIFY / ANALYZE REPORT
  // ----------------------------------------
  analyzeReport: async (text) => {

    const res = await fetch(`${BASE_URL}/analyze`, {
      method: 'POST',

      headers: {
        'Content-Type': 'application/json'
      },

      body: JSON.stringify({
        report_text: text
      })
    });

    return handleResponse(res);
  },


  // ----------------------------------------
  // WORKER SUBMITS A REPORT
  // ----------------------------------------
 submitWorkerReport: async ({
  report_text,
  site,
  activity,
  shift,
  is_contractor = false
}) => {

  const res = await fetch(
    `${BASE_URL}/reports/worker`,
    {
      method: 'POST',

      headers: {
        'Content-Type': 'application/json'
      },

      body: JSON.stringify({
        report_text,
        site,
        activity,
        shift,
        is_contractor
      })
    }
  );

  return handleResponse(res);
},

  // ----------------------------------------
  // ADMIN TRIAGE - GET REPORTS
  // ----------------------------------------
  getReports: async (limit = 20, offset = 0) => {

    const res = await fetch(
      `${BASE_URL}/reports?limit=${limit}&offset=${offset}`
    );

    return handleResponse(res);
  },


  // ----------------------------------------
  // ADMIN DASHBOARD SUMMARY
  // ----------------------------------------
  getSummary: async () => {

    const res = await fetch(
      `${BASE_URL}/aggregate/summary`
    );

    return handleResponse(res);
  },


  // ----------------------------------------
  // SITE RISK RANKING
  // ----------------------------------------
  getSites: async () => {

    const res = await fetch(
      `${BASE_URL}/aggregate/sites`
    );

    return handleResponse(res);
  },


  // ----------------------------------------
  // UPDATE REPORT STATUS
  // ----------------------------------------
  updateReportStatus: async (reportId, status) => {

    const res = await fetch(
      `${BASE_URL}/reports/${reportId}/status`,
      {
        method: 'PATCH',

        headers: {
          'Content-Type': 'application/json'
        },

        body: JSON.stringify({
          status
        })
      }
    );

    return handleResponse(res);
  }

};