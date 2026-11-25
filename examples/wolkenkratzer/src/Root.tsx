import React from "react";
import { Composition } from "remotion";
import { Short, NFR } from "./Short";
export const RemotionRoot: React.FC = () => (
  <Composition id="Wolkenkratzer" component={Short} durationInFrames={NFR} fps={30} width={1080} height={1920} />
);
