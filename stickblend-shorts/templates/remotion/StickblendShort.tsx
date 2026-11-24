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

const Caption: React.FC<{
  words: TimelineWord[];
  t: number;
  highlights: string[];
}> = ({ words, t, highlights }) => {
  let i = -1;
  words.forEach((w, k) => {
    if (t >= w.s - 0.04) i = k;
  });
  if (i < 0) return null;
  const w = words[i];
  const txt = w.w.replace(/[.!?:]$/g, "");
  const k = Math.min(1, (t - w.s + 0.04) / 0.1);
  const hl = highlights.some((h) => norm(w.w).startsWith(h));
  const size = Math.min(104, 1500 / Math.max(6, txt.length));
  return (
    <g transform={`translate(540,1360) scale(${0.92 + 0.08 * k})`} opacity={0.4 + 0.6 * k}>
      <text
        textAnchor="middle"
        fontFamily="system-ui, -apple-system, 'Segoe UI', sans-serif"
        fontWeight={900}
        fontSize={size}
        fill={hl ? "#ffe066" : "#fff"}
        stroke="#111"
        strokeWidth={size * 0.17}
        strokeLinejoin="round"
        paintOrder="stroke"
      >
        {txt}
      </text>
    </g>
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
}> = ({ slug, line, fps, overlay, highlights, showCaptions }) => {
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
          {showCaptions && <Caption words={words} t={t} highlights={highlights} />}
          <rect width={1080} height={1920} fill="#000" opacity={1 - fin} />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
