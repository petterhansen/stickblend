import React from "react";
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type TimelineWord = { w: string; s: number; e: number };
export type TimelineLine = {
  id: string;
  text: string;
  start: number;
  end: number;
  dur: number;
  words: TimelineWord[];
};
export type Timeline = {
  fps: number;
  total: number;
  audio: string;
  lines: TimelineLine[];
};

export type SfxCue = { s: string; at: number; v?: number };
export type SceneOverlayFn = (p: { t: number; dur: number; words: TimelineWord[] }) => React.ReactNode;

const norm = (s: string) => s.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
const relWords = (l: TimelineLine): TimelineWord[] =>
  l.words.map((w) => ({ w: w.w, s: w.s - l.start, e: w.e - l.start }));

// ---- Captions (SHORTS-REGELN.md): 2-4 words per group, punctuation kept, numbers as digits, ẞ in caps,
// always inside the safe box. Default = cross-platform zone (YouTube Shorts + Reels + TikTok): x 70-860, bottom <= 1240.
// TikTok-only exports may use the TikTok caption box (yc 1290, bottom <= 1500) via the `captionBox` prop.
export type CaptionBox = { x0: number; x1: number; yc: number };
export const CAPTION_BOX_UNIVERSAL: CaptionBox = { x0: 70, x1: 860, yc: 1120 };
export const CAPTION_BOX_TIKTOK: CaptionBox = { x0: 70, x1: 860, yc: 1290 };
const up = (s: string) => s.replace(/ß/g, "ẞ").toUpperCase();
type Grp = { txt: string; s: number; e: number };
const groupWords = (words: TimelineWord[], numbers: [RegExp, string][]): Grp[] => {
  const disp = (w: string) => { let x = w.replace(/–/g, "").trim(); for (const [re, d] of numbers) x = x.replace(re, d); return x; };
  const ws = words.filter((w) => norm(w.w));
  const out: Grp[] = []; let cur: TimelineWord[] = [];
  const flush = () => { if (cur.length) out.push({ txt: cur.map((w) => disp(w.w)).join(" "), s: cur[0].s, e: cur[cur.length - 1].e }); cur = []; };
  ws.forEach((w, i) => {
    const nx = ws[i + 1]; cur.push(w);
    const len = cur.map((x) => disp(x.w)).join(" ").length;
    const clause = /[.,:;!?“"]$/.test(w.w);
    const gap = nx ? nx.s - w.e > 0.32 : true;
    const nlen = nx ? len + 1 + disp(nx.w).length : 99;
    if (!nx || clause || gap || cur.length >= 4 || nlen > 22) flush();
  });
  flush();
  return out;
};
const wrapLines = (s: string, max = 13) => {
  const lines: string[] = []; let l = "";
  for (const w of s.split(" ")) { if (l && (l + " " + w).length > max) { lines.push(l); l = w; } else l = l ? l + " " + w : w; }
  if (l) lines.push(l);
  return lines;
};

const Caption: React.FC<{
  words: TimelineWord[];
  t: number;
  highlights: string[];
  box?: CaptionBox;
  numbers?: [RegExp, string][];
}> = ({ words, t, highlights, box = CAPTION_BOX_UNIVERSAL, numbers = [] }) => {
  const groups = React.useMemo(() => groupWords(words, numbers), [words, numbers]);
  let g = -1;
  groups.forEach((x, k) => { if (t >= x.s - 0.03) g = k; });
  if (g < 0) return null;
  const G = groups[g]; const next = groups[g + 1];
  if (t > G.e + 0.5 && (!next || t < next.s - 0.03)) return null;
  const k = Math.min(1, (t - G.s + 0.03) / 0.08);
  const lines = wrapLines(up(G.txt));
  const longest = Math.max(...lines.map((l) => l.length));
  const size = Math.min(92, (box.x1 - box.x0) / (0.74 * Math.max(8, longest)));
  const top = box.yc - size * 0.54 * lines.length;
  const hl = highlights.some((h) => norm(G.txt).includes(h));
  return (
    <div style={{ position: "absolute", left: box.x0, width: box.x1 - box.x0, top, textAlign: "center",
      fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif", fontWeight: 900, fontSize: size, color: hl ? "#ffe066" : "#fff",
      WebkitTextStroke: `${size * 0.16}px #111`, paintOrder: "stroke fill", transform: `scale(${0.92 + 0.08 * k})`,
      textShadow: "0 6px 0 rgba(0,0,0,0.35)", lineHeight: 1.08 }}>
      {lines.map((l, i) => <div key={i}>{l}</div>)}
    </div>
  );
};

export interface StickblendShortProps {
  slug: string;
  timeline: Timeline;
  overlays?: Record<string, SceneOverlayFn>;
  sfxByScene?: Record<string, SfxCue[]>;
  sfxGain?: Record<string, number>;
  highlights?: string[];
  showCaptions?: boolean;
  captionBox?: CaptionBox;               // default CAPTION_BOX_UNIVERSAL (YouTube + Reels + TikTok)
  captionNumbers?: [RegExp, string][];   // e.g. [[/^fünfzehn$/i, "15"]] -> numbers as digits
  showProgressBar?: boolean;
  musicVolume?: number;
  duckSceneIds?: string[];
}

export const StickblendShort: React.FC<StickblendShortProps> = ({
  slug,
  timeline,
  overlays = {},
  sfxByScene = {},
  sfxGain = {},
  highlights = [],
  showCaptions = false,
  captionBox,
  captionNumbers,
  showProgressBar = false,
  musicVolume = 0.12,
  duckSceneIds = [],
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const cues = timeline.lines.flatMap((l) =>
    (sfxByScene[l.id] ?? []).map((c) => ({ ...c, at: l.start + c.at })),
  );
  const duckRanges = timeline.lines
    .filter((l) => duckSceneIds.includes(l.id))
    .map((l) => [l.start, l.end] as const);

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {timeline.lines.map((line) => {
        const from = Math.round(line.start * fps);
        const durFrames = Math.max(1, Math.round(line.end * fps) - from);
        return (
          <Sequence key={line.id} from={from} durationInFrames={durFrames}>
            <SceneClip
              slug={slug}
              line={line}
              fps={fps}
              overlay={overlays[line.id]}
              highlights={highlights}
              showCaptions={showCaptions}
              captionBox={captionBox}
              captionNumbers={captionNumbers}
            />
          </Sequence>
        );
      })}

      <Audio src={staticFile(`shorts/${slug}/${timeline.audio}`)} />

      <Audio
        src={staticFile(`shorts/${slug}/audio/music.wav`)}
        volume={(f) => {
          const t = f / fps;
          let duck = 1;
          for (const [s, e] of duckRanges) {
            const d = interpolate(
              t,
              [s - 0.2, s + 0.3, e - 0.3, e + 0.3],
              [1, 0.35, 0.35, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            );
            duck = Math.min(duck, d);
          }
          const fadeIn = interpolate(t, [0, 0.5], [0.3, 1], { extrapolateRight: "clamp" });
          return musicVolume * duck * fadeIn;
        }}
      />

      {cues.map((c, i) => (
        <Sequence key={i} from={Math.max(0, Math.round(c.at * fps))} durationInFrames={150}>
          <Audio
            src={staticFile(`shorts/${slug}/audio/sfx/${c.s}.wav`)}
            volume={(c.v ?? 0.7) * (sfxGain[c.s] ?? 0.3)}
          />
        </Sequence>
      ))}

      {showProgressBar && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            height: 10,
            width: `${(frame / durationInFrames) * 100}%`,
            background: "#ffc928",
          }}
        />
      )}
    </AbsoluteFill>
  );
};

const SceneClip: React.FC<{
  slug: string;
  line: TimelineLine;
  fps: number;
  overlay?: SceneOverlayFn;
  highlights: string[];
  showCaptions: boolean;
  captionBox?: CaptionBox;
  captionNumbers?: [RegExp, string][];
}> = ({ slug, line, fps, overlay, highlights, showCaptions, captionBox, captionNumbers }) => {
  const f = useCurrentFrame();
  const t = f / fps;
  const words = relWords(line);
  const fin = Math.min(1, t / 0.18);

  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <OffthreadVideo src={staticFile(`shorts/${slug}/bl/${line.id}.mp4`)} muted />
      <AbsoluteFill>
        <svg width={1080} height={1920} viewBox="0 0 1080 1920">
          {overlay && overlay({ t, dur: line.dur, words })}
          <image
            href={staticFile(`shorts/${slug}/img/grain.png`)}
            x={-((f * 137) % 400)}
            y={-((f * 71) % 400)}
            width={2160}
            height={2160}
            opacity={0.05}
            style={{ mixBlendMode: "overlay" }}
          />
          <rect width={1080} height={1920} fill="#000" opacity={1 - fin} />
        </svg>
        {showCaptions && <Caption words={words} t={t} highlights={highlights} box={captionBox} numbers={captionNumbers} />}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
