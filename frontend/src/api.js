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
  //
  // The endpoint returns { ranked, insufficient_volume, min_group_n }, NOT an array and
  // not a `sites` key. AdminDashboard read `siteData.sites`, which is undefined, so it
  // always fell through to hardcoded chart data - the "Live Aggregates" panel had never
  // once shown a real number.
  //
  // `ranked` is what to chart. `insufficient_volume` is the groups that fell below
  // min_group_n: real sites with too few reports to rate honestly. They are returned
  // rather than dropped so the UI can grey them out instead of pretending they do not
  // exist, which is the whole point of the small-denominator guard.
  getSites: async () => {

    const res = await fetch(
      `${BASE_URL}/aggregate/sites`
    );

    const body = await handleResponse(res);

    return {
      ranked: body.ranked ?? [],
      insufficientVolume: body.insufficient_volume ?? [],
      minGroupN: body.min_group_n ?? 0
    };
  },


  // ----------------------------------------
  // HEALTH - IS THIS REAL DATA OR THE SEEDED STUB?
  // ----------------------------------------
  //
  // `data_source` is "postgres" or "seeded_stub". The dashboard shows a badge when it is
  // the stub, so nobody reads fixture numbers off a screen believing they are live.
  getHealth: async () => {

    const res = await fetch(`${BASE_URL}/health`);

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