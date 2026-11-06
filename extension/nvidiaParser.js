// nvidiaParser.js — parses NVIDIA Careers API response (/api/pcsx/search).

export function parseNvidiaJobs(data) {
  const positions = (data && data.data && data.data.positions) ? data.data.positions : [];
  return positions
    .filter(p => p.id)
    .map(p => ({
      id:       `nvidia-${p.id}`,
      title:    (p.name || "").trim(),
      location: (p.locations || []).join(", "),
      url:      `https://jobs.nvidia.com${p.positionUrl || ""}`,
      posted:   p.postedTs
        ? new Date(p.postedTs * 1000).toISOString().slice(0, 10)
        : "",
      source:   "NVIDIA",
    }));
}

export function parseNvidiaJobDetail(data) {
  return (data && data.data && data.data.jobDescription) ? data.data.jobDescription : "";
}
