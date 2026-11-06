// microsoftParser.js — parses Microsoft Careers Eightfold API response (/api/pcsx/search).

export function parseMicrosoftJobs(data) {
  const positions = (data && data.data && data.data.positions) ? data.data.positions : [];
  return positions
    .filter(p => p.id)
    .map(p => ({
      id:       `microsoft-${p.id}`,
      title:    (p.name || "").trim(),
      location: (p.locations || []).join(", "),
      url:      `https://apply.careers.microsoft.com${p.positionUrl || ""}`,
      posted:   p.postedTs
        ? new Date(p.postedTs * 1000).toISOString().slice(0, 10)
        : "",
      source:   "Microsoft",
    }));
}
