import React from "react";
import { Composition } from "remotion";
import { StickblendShort, Timeline } from "./shared/StickblendShort";

// Register your short compositions here.
// Example:
// import { MyShort, MY_SHORT_FRAMES } from "./videos/my-short/MyShort";

const DEMO_TIMELINE: Timeline = {
  fps: 30,
  total: 3,
  audio: "audio/voice.wav",
  lines: [],
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ExampleShort"
        component={() => <StickblendShort slug="example" timeline={DEMO_TIMELINE} />}
        durationInFrames={90}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
