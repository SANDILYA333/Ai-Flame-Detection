"use client";

import React, { useState, useEffect } from "react";
import type {
  EmergencyResponder,
  ResponsePriority,
  NotificationAction,
  NotificationChannel,
} from "@/types/responders";
import {
  ShieldAlert,
  X,
  Send,
  Building2,
  Phone,
  CheckCircle2,
  Clock,
  MessageSquare,
  Smartphone,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface NotificationConfirmModalProps {
  isOpen: boolean;
  responder: EmergencyResponder | null;
  eventId: string;
  priority: ResponsePriority;
  action: NotificationAction;
  demoPhone?: string;
  onConfirm: (notes?: string, channels?: NotificationChannel[]) => Promise<void>;
  onClose: () => void;
}

export function NotificationConfirmModal({
  isOpen,
  responder,
  eventId,
  priority,
  action,
  demoPhone,
  onConfirm,
  onClose,
}: NotificationConfirmModalProps) {
  const [notes, setNotes] = useState("");
  const [smsEnabled, setSmsEnabled] = useState(true);
  const [whatsappEnabled, setWhatsappEnabled] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setNotes("");
      setSmsEnabled(true);
      setWhatsappEnabled(true);
      setIsSubmitting(false);
    }
  }, [isOpen]);

  // Handle Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isSubmitting) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isSubmitting, onClose]);

  if (!isOpen || !responder) return null;

  const isMobilize = action === "MOBILIZE";
  const displayPhone = demoPhone || responder.phone || "+91-112";

  const selectedChannels: NotificationChannel[] = [];
  if (smsEnabled) selectedChannels.push("SMS");
  if (whatsappEnabled) selectedChannels.push("WHATSAPP");

  const isConfirmDisabled = isSubmitting || selectedChannels.length === 0;

  const handleConfirmClick = async () => {
    if (isConfirmDisabled) return;
    setIsSubmitting(true);
    try {
      await onConfirm(notes.trim() || undefined, selectedChannels);
      onClose();
    } catch {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-150 select-none">
      <div
        className="w-full max-w-md bg-surface-raised border border-border rounded-panel shadow-2xl p-4 sm:p-5 flex flex-col gap-4 animate-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
      >
        {/* Header */}
        <div className="flex items-start justify-between border-b border-border pb-3">
          <div className="flex items-center gap-2.5">
            <div
              className={cn(
                "w-9 h-9 rounded-control flex items-center justify-center border",
                isMobilize
                  ? "bg-state-error/15 border-state-error/30 text-state-error"
                  : "bg-accent/15 border-accent/30 text-accent"
              )}
            >
              <ShieldAlert className="w-4 h-4 animate-pulse-subtle" />
            </div>
            <div>
              <h2
                id="confirm-modal-title"
                className="text-sm font-bold text-foreground font-mono uppercase tracking-wider"
              >
                {isMobilize ? "Confirm NDRF Mobilization" : "Confirm Emergency Notification"}
              </h2>
              <div className="text-[11px] font-mono text-foreground-muted flex items-center gap-1.5 mt-0.5">
                <span className="text-accent font-semibold">{eventId}</span>
                <span>•</span>
                <span className="px-1.5 py-0.2 rounded bg-surface border border-border text-[9.5px]">
                  PRIORITY: {priority}
                </span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            title="Cancel and close dialog (Esc)"
            aria-label="Cancel and close dialog"
            className="p-1 text-foreground-muted hover:text-foreground rounded-control hover:bg-surface transition-colors disabled:opacity-50"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Target Recipient Card */}
        <div className="p-3 rounded-control bg-surface border border-border font-mono text-xs space-y-2">
          <div className="flex items-center justify-between text-[11px] text-foreground-muted border-b border-border/40 pb-1.5">
            <span className="uppercase tracking-wider">TARGET RECIPIENT</span>
            <span className="px-1.5 py-0.5 rounded bg-accent/10 text-accent text-[10px] font-bold border border-accent/20">
              {responder.type.replace(/_/g, " ")}
            </span>
          </div>

          <div className="font-semibold text-foreground text-sm flex items-center gap-1.5">
            <Building2 className="w-4 h-4 text-accent shrink-0" />
            <span className="truncate">{responder.name}</span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] text-foreground-secondary pt-1">
            <div className="flex items-center gap-1">
              <span className="text-foreground-muted">Distance:</span>
              <span className="font-semibold text-foreground">{responder.formatted_distance}</span>
            </div>
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-accent-cyan shrink-0" />
              <span className="text-foreground-muted">Est. ETA:</span>
              <span className="font-semibold text-foreground">{responder.formatted_eta}</span>
            </div>
            <div className="flex items-center gap-1 col-span-2">
              <Phone className="w-3 h-3 text-foreground-muted shrink-0" />
              <span className="text-foreground-muted">Destination Number:</span>
              <span className="font-mono text-accent font-semibold">{displayPhone}</span>
            </div>
            {responder.plume_impact_status && responder.plume_impact_status !== "UNAVAILABLE" && (
              <div className="flex items-center gap-1.5 col-span-2 pt-1 border-t border-border/30 text-[10px]">
                <span className="text-foreground-muted">Downwind Plume Status:</span>
                <span className="font-bold text-accent font-mono">
                  {responder.plume_impact_status.replace(/_/g, " ")}
                </span>
              </div>
            )}
          </div>

          {/* Interactive Multi-Channel Selector */}
          <div className="pt-2 border-t border-border/40 space-y-1.5">
            <span className="text-[10px] text-foreground-muted uppercase tracking-wider block font-semibold">
              Select Delivery Channels
            </span>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 cursor-pointer text-[10.5px]">
                <input
                  type="checkbox"
                  checked={smsEnabled}
                  onChange={(e) => setSmsEnabled(e.target.checked)}
                  disabled={isSubmitting}
                  className="rounded border-border text-accent focus:ring-accent"
                />
                <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-accent/10 text-accent font-bold border border-accent/20">
                  <Smartphone className="w-3 h-3" /> SMS (Fast2SMS)
                </span>
              </label>

              <label className="flex items-center gap-1.5 cursor-pointer text-[10.5px]">
                <input
                  type="checkbox"
                  checked={whatsappEnabled}
                  onChange={(e) => setWhatsappEnabled(e.target.checked)}
                  disabled={isSubmitting}
                  className="rounded border-border text-state-success focus:ring-state-success"
                />
                <span className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-state-success/10 text-state-success font-bold border border-state-success/20">
                  <MessageSquare className="w-3 h-3" /> WhatsApp (RichAutomate)
                </span>
              </label>
            </div>
            {selectedChannels.length === 0 && (
              <span className="text-[9.5px] text-state-error block">
                At least one delivery channel must be selected.
              </span>
            )}
          </div>
        </div>

        {/* Operational Safety & Simulation Mode Notice */}
        <div className="p-2.5 rounded-control bg-accent-cyan/10 border border-accent-cyan/30 text-[10.5px] font-mono text-accent-cyan flex items-start gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-accent-cyan" />
          <div className="space-y-1">
            <div className="font-bold tracking-wider uppercase text-[10px]">
              MODE: CONTROLLED EMERGENCY DISPATCH
            </div>
            <p className="text-foreground-secondary leading-relaxed">
              Analyst authorization confirmed. Dispatches scientific alert payloads and records verifiable audit timestamps across selected communication channels.
            </p>
          </div>
        </div>

        {/* Optional Analyst Dispatch Notes */}
        <div className="space-y-1.5 font-mono text-xs">
          <label htmlFor="analyst-notes" className="text-[10.5px] text-foreground-muted uppercase tracking-wider">
            Analyst Dispatch Directives (Optional)
          </label>
          <textarea
            id="analyst-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={isSubmitting}
            placeholder="e.g., Deploy chemical foam tender to Sector 4 perimeter; monitor toxic dispersion..."
            className="w-full h-16 px-2.5 py-1.5 rounded-control bg-background border border-border text-foreground text-xs focus:outline-none focus:border-accent resize-none placeholder:text-foreground-muted/50"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-border">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="px-3 py-1.5 text-xs font-mono text-foreground-secondary hover:text-foreground rounded-control hover:bg-surface border border-border transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirmClick}
            disabled={isConfirmDisabled}
            className={cn(
              "px-4 py-1.5 text-xs font-mono font-bold rounded-control flex items-center gap-1.5 shadow-panel transition-all active:scale-95 disabled:opacity-50",
              isMobilize
                ? "bg-state-error text-white hover:bg-state-error/90"
                : "bg-accent text-bg-base hover:bg-accent/90"
            )}
          >
            {isSubmitting ? (
              <>
                <div className="w-3.5 h-3.5 rounded-full border-2 border-white/20 border-t-white animate-spin" />
                <span>Dispatching...</span>
              </>
            ) : (
              <>
                <Send className="w-3.5 h-3.5" />
                <span>{isMobilize ? "Confirm Mobilization" : "Confirm Notification"}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
