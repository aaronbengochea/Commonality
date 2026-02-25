// frontend/src/components/WaveformVisualizer.tsx
"use client";

import { useEffect, useRef } from "react";
import type { WalkieState } from "@/hooks/useWalkieTalkie";

interface WaveformVisualizerProps {
  state: WalkieState;
  className?: string;
}

export default function WaveformVisualizer({ state, className = "" }: WaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const barCount = 32;
    const barWidth = width / barCount * 0.6;
    const gap = width / barCount * 0.4;
    let phase = 0;

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < barCount; i++) {
        const x = i * (barWidth + gap) + gap / 2;
        let barHeight: number;

        if (state === "idle") {
          barHeight = 4 + Math.sin(phase + i * 0.3) * 2;
        } else if (state === "recording") {
          barHeight = 8 + Math.sin(phase * 2 + i * 0.4) * (height * 0.35);
        } else if (state === "processing") {
          barHeight = 6 + Math.sin(phase * 1.5) * 8;
        } else {
          barHeight = 6 + Math.sin(phase * 1.8 + i * 0.5) * (height * 0.25);
        }

        const y = (height - barHeight) / 2;

        if (state === "recording") {
          ctx.fillStyle = "rgba(239, 68, 68, 0.8)";
        } else if (state === "processing") {
          ctx.fillStyle = "rgba(250, 204, 21, 0.7)";
        } else if (state === "playing") {
          ctx.fillStyle = "rgba(34, 197, 94, 0.8)";
        } else {
          ctx.fillStyle = "rgba(148, 163, 184, 0.4)";
        }

        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();
      }

      phase += 0.05;
      animationRef.current = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      cancelAnimationFrame(animationRef.current);
    };
  }, [state]);

  return (
    <canvas
      ref={canvasRef}
      className={`w-full h-24 ${className}`}
      style={{ display: "block" }}
    />
  );
}
