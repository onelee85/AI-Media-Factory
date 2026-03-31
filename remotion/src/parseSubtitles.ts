export interface SubtitleSegment {
  id: number;
  text: string;
  startFrame: number;
  endFrame: number;
  startMs: number;
  endMs: number;
}

const TIMESTAMP_RE = /(\d{2}):(\d{2}):(\d{2}),(\d{3})/;

function parseTimestamp(ts: string): number {
  const match = ts.match(TIMESTAMP_RE);
  if (!match) return 0;
  const [, hh, mm, ss, ms] = match;
  return (
    parseInt(hh, 10) * 3600000 +
    parseInt(mm, 10) * 60000 +
    parseInt(ss, 10) * 1000 +
    parseInt(ms, 10)
  );
}

export function parseSrt(srtText: string, fps: number = 30): SubtitleSegment[] {
  if (!srtText || !srtText.trim()) return [];

  const blocks = srtText.trim().split(/\n\s*\n/);
  const segments: SubtitleSegment[] = [];

  for (const block of blocks) {
    const lines = block.trim().split('\n');
    if (lines.length < 2) continue;

    // First line: index number
    const id = parseInt(lines[0].trim(), 10);
    if (isNaN(id)) continue;

    // Second line: timestamps
    const timestampLine = lines[1];
    const arrowIdx = timestampLine.indexOf('-->');
    if (arrowIdx === -1) continue;

    const startTs = timestampLine.substring(0, arrowIdx).trim();
    const endTs = timestampLine.substring(arrowIdx + 3).trim();

    const startMs = parseTimestamp(startTs);
    const endMs = parseTimestamp(endTs);

    // Remaining lines: subtitle text
    const text = lines.slice(2).join(' ').trim();

    segments.push({
      id,
      text,
      startMs,
      endMs,
      startFrame: Math.round((startMs / 1000) * fps),
      endFrame: Math.round((endMs / 1000) * fps),
    });
  }

  return segments;
}
