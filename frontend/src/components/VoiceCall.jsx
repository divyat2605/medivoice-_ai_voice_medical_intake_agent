import React, { useCallback, useEffect, useRef, useState } from "react";
import { Room, RoomEvent, Track } from "livekit-client";

const TOKEN_SERVER_URL = import.meta.env.VITE_TOKEN_SERVER_URL || "http://localhost:8080";

export default function VoiceCall() {
  const [status, setStatus] = useState("idle"); // idle | connecting | connected | error
  const [transcript, setTranscript] = useState([]);
  const [errorMsg, setErrorMsg] = useState("");
  const roomRef = useRef(null);
  const audioContainerRef = useRef(null);

  const connect = useCallback(async () => {
    setStatus("connecting");
    setErrorMsg("");
    try {
      const res = await fetch(`${TOKEN_SERVER_URL}/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_name: "Patient" }),
      });
      if (!res.ok) throw new Error(`Token server error: ${res.status}`);
      const { token, url } = await res.json();

      const room = new Room({ adaptiveStream: true, dynacast: true });
      roomRef.current = room;

      room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          audioContainerRef.current?.appendChild(el);
        }
      });

      room.on(RoomEvent.Disconnected, () => {
        setStatus("idle");
      });

      // Agent speech-to-text / responses arrive as data messages in many
      // livekit-agents setups; this is a lightweight example listener.
      room.on(RoomEvent.DataReceived, (payload) => {
        try {
          const text = new TextDecoder().decode(payload);
          const msg = JSON.parse(text);
          if (msg?.text) {
            setTranscript((prev) => [...prev, msg]);
          }
        } catch {
          // ignore non-JSON payloads
        }
      });

      await room.connect(url, token);
      await room.localParticipant.setMicrophoneEnabled(true);

      setStatus("connected");
    } catch (err) {
      console.error(err);
      setErrorMsg(err.message || "Failed to connect");
      setStatus("error");
    }
  }, []);

  const disconnect = useCallback(async () => {
    await roomRef.current?.disconnect();
    roomRef.current = null;
    setStatus("idle");
  }, []);

  useEffect(() => {
    return () => {
      roomRef.current?.disconnect();
    };
  }, []);

  return (
    <div style={styles.card}>
      <h1 style={styles.title}>🩺 MediVoice Intake</h1>
      <p style={styles.subtitle}>
        Speak naturally — Maya will collect your intake details before your visit.
      </p>

      <div style={styles.statusRow}>
        <span style={styles.statusDot(status)} />
        <span>{statusLabel(status)}</span>
      </div>

      {errorMsg && <p style={styles.error}>{errorMsg}</p>}

      <div style={styles.buttonRow}>
        {status !== "connected" ? (
          <button
            style={styles.button}
            onClick={connect}
            disabled={status === "connecting"}
          >
            {status === "connecting" ? "Connecting…" : "Start Call"}
          </button>
        ) : (
          <button style={{ ...styles.button, background: "#d64545" }} onClick={disconnect}>
            End Call
          </button>
        )}
      </div>

      <div ref={audioContainerRef} />

      <div style={styles.transcriptBox}>
        {transcript.length === 0 ? (
          <p style={styles.transcriptPlaceholder}>Conversation will appear here.</p>
        ) : (
          transcript.map((t, i) => (
            <p key={i} style={styles.transcriptLine}>
              <strong>{t.role || "agent"}:</strong> {t.text}
            </p>
          ))
        )}
      </div>
    </div>
  );
}

function statusLabel(status) {
  switch (status) {
    case "connecting":
      return "Connecting…";
    case "connected":
      return "On call with Maya";
    case "error":
      return "Connection error";
    default:
      return "Ready to start";
  }
}

const styles = {
  card: {
    maxWidth: 480,
    margin: "48px auto",
    padding: 32,
    borderRadius: 16,
    boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
    fontFamily: "system-ui, sans-serif",
    background: "#fff",
  },
  title: { margin: 0, fontSize: 24 },
  subtitle: { color: "#666", marginTop: 8 },
  statusRow: { display: "flex", alignItems: "center", gap: 8, margin: "20px 0" },
  statusDot: (status) => ({
    width: 10,
    height: 10,
    borderRadius: "50%",
    background:
      status === "connected" ? "#2ecc71" : status === "error" ? "#e74c3c" : "#f1c40f",
    display: "inline-block",
  }),
  error: { color: "#e74c3c", fontSize: 14 },
  buttonRow: { margin: "16px 0" },
  button: {
    padding: "12px 24px",
    borderRadius: 8,
    border: "none",
    background: "#3ECF8E",
    color: "#fff",
    fontSize: 16,
    cursor: "pointer",
  },
  transcriptBox: {
    marginTop: 24,
    padding: 16,
    borderRadius: 8,
    background: "#f7f7f9",
    minHeight: 120,
    maxHeight: 300,
    overflowY: "auto",
  },
  transcriptPlaceholder: { color: "#999", fontSize: 14 },
  transcriptLine: { fontSize: 14, margin: "4px 0" },
};
