"use client";

import { useState, useEffect, useCallback, useRef } from "react";

export interface DragBounds {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export interface UseDraggableOptions {
  storageKey?: string;
  defaultPosition: { x: number; y: number } | (() => { x: number; y: number });
  boundsOffset?: Partial<DragBounds>;
}

export function useDraggable({
  storageKey,
  defaultPosition,
  boundsOffset = {},
}: UseDraggableOptions) {
  const bounds: DragBounds = {
    top: boundsOffset.top ?? 56,
    bottom: boundsOffset.bottom ?? 56,
    left: boundsOffset.left ?? 12,
    right: boundsOffset.right ?? 12,
  };

  const [position, setPosition] = useState<{ x: number; y: number }>(() => {
    if (typeof window !== "undefined" && storageKey) {
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (typeof parsed.x === "number" && typeof parsed.y === "number") {
            return parsed;
          }
        }
      } catch {
        // Fall back to defaultPosition
      }
    }
    return typeof defaultPosition === "function" ? defaultPosition() : defaultPosition;
  });

  const [isDragging, setIsDragging] = useState(false);
  const cardRef = useRef<HTMLDivElement | null>(null);
  const dragStartRef = useRef<{
    startX: number;
    startY: number;
    initialX: number;
    initialY: number;
  } | null>(null);

  const clampPosition = useCallback(
    (pos: { x: number; y: number }) => {
      if (typeof window === "undefined") return pos;
      const cardWidth = cardRef.current?.offsetWidth || 260;
      const cardHeight = cardRef.current?.offsetHeight || 140;
      const maxX = Math.max(bounds.left, window.innerWidth - cardWidth - bounds.right);
      const maxY = Math.max(bounds.top, window.innerHeight - cardHeight - bounds.bottom);

      return {
        x: Math.min(Math.max(bounds.left, pos.x), maxX),
        y: Math.min(Math.max(bounds.top, pos.y), maxY),
      };
    },
    [bounds.top, bounds.bottom, bounds.left, bounds.right]
  );

  // Re-clamp position on window resize
  useEffect(() => {
    const handleResize = () => {
      setPosition((prev) => clampPosition(prev));
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [clampPosition]);

  // Pointer down handler for the header drag handle
  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      // Only initiate on left click / primary pointer
      if (e.button !== 0) return;
      e.preventDefault();
      e.stopPropagation();

      dragStartRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        initialX: position.x,
        initialY: position.y,
      };
      setIsDragging(true);

      const onPointerMove = (moveEvent: PointerEvent) => {
        if (!dragStartRef.current) return;
        const dx = moveEvent.clientX - dragStartRef.current.startX;
        const dy = moveEvent.clientY - dragStartRef.current.startY;
        const nextPos = clampPosition({
          x: dragStartRef.current.initialX + dx,
          y: dragStartRef.current.initialY + dy,
        });
        setPosition(nextPos);
      };

      const onPointerUp = (upEvent: PointerEvent) => {
        if (!dragStartRef.current) return;
        const dx = upEvent.clientX - dragStartRef.current.startX;
        const dy = upEvent.clientY - dragStartRef.current.startY;
        const finalPos = clampPosition({
          x: dragStartRef.current.initialX + dx,
          y: dragStartRef.current.initialY + dy,
        });
        setPosition(finalPos);

        if (storageKey) {
          try {
            localStorage.setItem(storageKey, JSON.stringify(finalPos));
          } catch {
            // Ignore quota errors
          }
        }

        dragStartRef.current = null;
        setIsDragging(false);
        window.removeEventListener("pointermove", onPointerMove);
        window.removeEventListener("pointerup", onPointerUp);
        window.removeEventListener("pointercancel", onPointerUp);
      };

      window.addEventListener("pointermove", onPointerMove);
      window.addEventListener("pointerup", onPointerUp);
      window.addEventListener("pointercancel", onPointerUp);
    },
    [clampPosition, position.x, position.y, storageKey]
  );

  return {
    position,
    setPosition,
    isDragging,
    cardRef,
    handlePointerDown,
  };
}
