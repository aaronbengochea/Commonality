"use client";

import {
  LiveKitRoom,
  RoomAudioRenderer,
  ControlBar,
} from "@livekit/components-react";
import "@livekit/components-styles";

interface Props {
  token: string;
  serverUrl: string;
  onDisconnected?: () => void;
}

export default function VoiceRoom({ token, serverUrl, onDisconnected }: Props) {
  return (
    <LiveKitRoom
      token={token}
      serverUrl={serverUrl}
      connect={true}
      audio={true}
      video={false}
      onDisconnected={onDisconnected}
    >
      <div className="glass-card flex flex-col items-center gap-6 rounded-xl p-8">
        <RoomAudioRenderer />
        <ControlBar
          variation="verbose"
          controls={{
            microphone: true,
            camera: false,
            chat: false,
            screenShare: false,
            leave: true,
          }}
        />
      </div>
    </LiveKitRoom>
  );
}
