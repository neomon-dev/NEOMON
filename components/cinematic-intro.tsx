"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import Image from "next/image";

export function CinematicIntro() {
  const [mounted, setMounted] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [hasVideoError, setHasVideoError] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const completeTimerRef = useRef<NodeJS.Timeout | null>(null);

  const finishIntro = useCallback(() => {
    setIsFadingOut(true);
    setTimeout(() => {
      setIsVisible(false);
    }, 550);
  }, []);

  const toggleSound = useCallback((e?: React.MouseEvent) => {
    if (e) {
      e.stopPropagation();
    }
    if (videoRef.current) {
      const targetMuted = !videoRef.current.muted;
      videoRef.current.muted = targetMuted;
      videoRef.current.volume = 1.0;
      setIsMuted(targetMuted);
      if (!targetMuted) {
        setAutoplayBlocked(false);
        videoRef.current.play().catch(() => {});
      }
    }
  }, []);

  useEffect(() => {
    setMounted(true);
    let prefersReducedMotion = false;

    if (typeof window !== "undefined" && window.matchMedia) {
      prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    if (prefersReducedMotion) {
      setIsVisible(false);
      return;
    }

    // Always play on initial load and on every page refresh
    setIsVisible(true);

    // Failsafe timer (5.4s) in case video stalled or onEnded didn't trigger
    completeTimerRef.current = setTimeout(() => {
      finishIntro();
    }, 5400);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        finishIntro();
      } else if (e.key === " " || e.key === "m" || e.key === "M") {
        toggleSound();
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    // Ensure audio is immediately active and unmuted on the earliest possible user interaction
    const handleFirstGesture = () => {
      if (videoRef.current) {
        videoRef.current.muted = false;
        videoRef.current.volume = 1.0;
        setIsMuted(false);
        setAutoplayBlocked(false);
      }
    };
    window.addEventListener("pointermove", handleFirstGesture, { once: true, passive: true });
    window.addEventListener("pointerdown", handleFirstGesture, { once: true, passive: true });
    window.addEventListener("touchstart", handleFirstGesture, { once: true, passive: true });
    window.addEventListener("focus", handleFirstGesture, { once: true, passive: true });

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("pointermove", handleFirstGesture);
      window.removeEventListener("pointerdown", handleFirstGesture);
      window.removeEventListener("touchstart", handleFirstGesture);
      window.removeEventListener("focus", handleFirstGesture);
      if (completeTimerRef.current) {
        clearTimeout(completeTimerRef.current);
      }
    };
  }, [finishIntro, toggleSound]);

  useEffect(() => {
    if (isVisible && videoRef.current) {
      const video = videoRef.current;
      video.currentTime = 0;
      video.volume = 1.0;
      video.muted = false;
      setIsMuted(false);

      const playPromise = video.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            // Direct unmuted playback succeeded
            setIsMuted(false);
            setAutoplayBlocked(false);
          })
          .catch((err) => {
            // Browser policy delayed unmuted playback until interaction: start playback visually,
            // keep the button in UNMUTED state ("🔊 SOUND ON") at start, and unmute on earliest motion.
            console.warn("Autoplay policy delayed unmuted audio:", err);
            video.muted = true;
            video.play().catch(() => {});
            setIsMuted(false);
            setAutoplayBlocked(false);

            const activateSound = () => {
              if (videoRef.current) {
                videoRef.current.muted = false;
                videoRef.current.volume = 1.0;
                setIsMuted(false);
              }
            };
            window.addEventListener("pointermove", activateSound, { once: true, passive: true });
            window.addEventListener("pointerdown", activateSound, { once: true, passive: true });
            window.addEventListener("keydown", activateSound, { once: true, passive: true });
            window.addEventListener("touchstart", activateSound, { once: true, passive: true });
            window.addEventListener("focus", activateSound, { once: true, passive: true });
          });
      }
    }
  }, [isVisible]);

  if (!mounted || !isVisible) {
    return null;
  }

  const handleVideoError = () => {
    setHasVideoError(true);
    // If video fails, show CSS/SVG fallback for 3 seconds then exit cleanly
    if (completeTimerRef.current) {
      clearTimeout(completeTimerRef.current);
    }
    completeTimerRef.current = setTimeout(() => {
      finishIntro();
    }, 3200);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="NEOMON Intro Experience"
      onClick={isMuted ? toggleSound : undefined}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 99999,
        backgroundColor: "#030712",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: isFadingOut ? 0 : 1,
        transition: "opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1)",
        pointerEvents: isFadingOut ? "none" : "auto",
        overflow: "hidden",
        cursor: isMuted ? "pointer" : "default",
      }}
    >
      {/* Subtle background glow */}
      <div
        style={{
          position: "absolute",
          width: "600px",
          height: "600px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(54, 197, 222, 0.12) 0%, rgba(8, 47, 73, 0.05) 50%, transparent 70%)",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
      />

      {/* Action controls in top right */}
      <div
        style={{
          position: "absolute",
          top: "24px",
          right: "24px",
          zIndex: 10,
          display: "flex",
          alignItems: "center",
          gap: "12px",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sound toggle button */}
        <button
          type="button"
          onClick={toggleSound}
          aria-label={isMuted ? "Unmute Audio" : "Mute Audio"}
          style={{
            background: isMuted ? "rgba(8, 47, 73, 0.85)" : "rgba(8, 126, 171, 0.6)",
            border: isMuted ? "1px solid rgba(54, 197, 222, 0.6)" : "1px solid rgba(54, 197, 222, 0.4)",
            backdropFilter: "blur(8px)",
            color: "#F5FAFC",
            fontSize: "12px",
            fontWeight: 600,
            letterSpacing: "0.08em",
            padding: "8px 16px",
            borderRadius: "20px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            transition: "all 0.2s ease",
            boxShadow: isMuted
              ? "0 0 20px rgba(54, 197, 222, 0.35)"
              : "0 0 15px rgba(54, 197, 222, 0.15)",
            animation: autoplayBlocked ? "soundPulseNotice 1.5s ease-in-out infinite" : "none",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "rgba(54, 197, 222, 0.9)";
            e.currentTarget.style.transform = "translateY(-1px)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = isMuted ? "rgba(54, 197, 222, 0.6)" : "rgba(54, 197, 222, 0.4)";
            e.currentTarget.style.transform = "translateY(0)";
          }}
        >
          <span>{isMuted ? "🔇 UNMUTE AUDIO" : "🔊 SOUND ON"}</span>
          <span style={{ fontSize: "10px", opacity: 0.6, fontFamily: "monospace" }}>[M]</span>
        </button>

        {/* Skip button */}
        <button
          type="button"
          onClick={finishIntro}
          aria-label="Skip Intro"
          style={{
            background: "rgba(8, 47, 73, 0.5)",
            border: "1px solid rgba(54, 197, 222, 0.3)",
            backdropFilter: "blur(8px)",
            color: "#F5FAFC",
            fontSize: "12px",
            fontWeight: 600,
            letterSpacing: "0.08em",
            padding: "8px 16px",
            borderRadius: "20px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            transition: "all 0.2s ease",
            boxShadow: "0 0 15px rgba(54, 197, 222, 0.15)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "rgba(54, 197, 222, 0.8)";
            e.currentTarget.style.boxShadow = "0 0 25px rgba(54, 197, 222, 0.4)";
            e.currentTarget.style.transform = "translateY(-1px)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "rgba(54, 197, 222, 0.3)";
            e.currentTarget.style.boxShadow = "0 0 15px rgba(54, 197, 222, 0.15)";
            e.currentTarget.style.transform = "translateY(0)";
          }}
        >
          <span>SKIP INTRO</span>
          <span style={{ fontSize: "10px", opacity: 0.6, fontFamily: "monospace" }}>[ESC]</span>
          <span style={{ fontSize: "14px", lineHeight: 1 }}>›</span>
        </button>
      </div>

      {/* Main Video presentation */}
      {!hasVideoError ? (
        <div
          style={{
            position: "relative",
            width: "100%",
            maxWidth: "960px",
            aspectRatio: "16 / 9",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <video
            ref={videoRef}
            src="/brand/neomon-intro.mp4"
            autoPlay
            playsInline
            onEnded={finishIntro}
            onError={handleVideoError}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
              filter: "drop-shadow(0 0 40px rgba(54, 197, 222, 0.25))",
            }}
          />
        </div>
      ) : (
        /* CSS / SVG Fallback if video is unavailable or blocked */
        <div
          style={{
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: "20px",
            animation: "introFallbackFade 3s ease forwards",
          }}
        >
          <div
            style={{
              position: "relative",
              width: "160px",
              height: "160px",
              filter: "drop-shadow(0 0 30px rgba(54, 197, 222, 0.45))",
            }}
          >
            <Image
              src="/brand/neomon-symbol.svg"
              alt="NEOMON Cube"
              width={160}
              height={160}
              priority
              style={{ objectFit: "contain" }}
            />
          </div>
          <div>
            <h1
              style={{
                fontSize: "36px",
                fontWeight: 800,
                letterSpacing: "0.22em",
                margin: "0 0 8px 0",
                background: "linear-gradient(135deg, #F5FAFC 0%, #36C5DE 60%, #647BFF 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
              }}
            >
              NEOMON
            </h1>
            <p
              style={{
                fontSize: "13px",
                letterSpacing: "0.24em",
                fontWeight: 600,
                color: "#94a3b8",
                margin: 0,
                textTransform: "uppercase",
              }}
            >
              RESEARCH BEYOND THE SURFACE.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
