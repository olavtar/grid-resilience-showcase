// This project was developed with assistance from AI tools.

import { useEffect, useRef, useState } from "react";
import { AppStreamer, StreamType, LogLevel, StreamStatus } from "@nvidia/omniverse-webrtc-streaming-library";

interface SubstationPanelProps {
  signalingServer: string;
}

export function SubstationPanel({ signalingServer }: SubstationPanelProps) {
  const [status, setStatus] = useState<string>("connecting");
  const firstFrameRef = useRef(false);

  useEffect(() => {
    if (!signalingServer) return;
    let terminated = false;

    AppStreamer.connect({
      streamSource: StreamType.DIRECT,
      logLevel: LogLevel.WARN,
      streamConfig: {
        signalingServer,
        signalingPort: 443,
        forceWSS: true,
        videoElementId: "kit-stream-video",
        audioElementId: "kit-stream-audio",
        width: 1920,
        height: 1080,
        fps: 30,
        maxReconnects: 10,
        reconnectDelay: 5000,
        onStart: () => {
          if (terminated) return;
          setStatus("streaming");
          firstFrameRef.current = true;
        },
        onStop: () => {
          if (terminated) return;
          setStatus("reconnecting");
        },
      },
    }).catch(() => {
      if (!terminated) {
        setStatus("error");
      }
    });

    return () => {
      terminated = true;
      if (AppStreamer.streamStatus !== StreamStatus.none) {
        AppStreamer.terminate().catch(() => undefined);
      }
    };
  }, [signalingServer]);

  return (
    <div className="grid-card" style={{ height: 300, display: "flex", flexDirection: "column" }}>
      <div className="grid-card__header">3D Substation Digital Twin</div>
      <div className="grid-card__body--flush" style={{ flex: 1, position: "relative", background: "#1e1e1e" }}>
        <video
          id="kit-stream-video"
          autoPlay
          muted
          playsInline
          style={{ width: "100%", height: "100%", objectFit: "contain" }}
        />
        <audio id="kit-stream-audio" autoPlay muted playsInline style={{ display: "none" }} />
        {status !== "streaming" && (
          <div style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
            gap: 6,
            color: "#ccc",
            fontSize: 13,
            background: "rgba(30,30,30,0.9)",
          }}>
            <span>
              {status === "error" ? "WebRTC connection failed" :
               status === "reconnecting" ? "Reconnecting to digital twin..." :
               "Connecting to substation digital twin..."}
            </span>
            <span className="grid-mono" style={{ fontSize: 10 }}>{signalingServer}</span>
          </div>
        )}
      </div>
    </div>
  );
}
