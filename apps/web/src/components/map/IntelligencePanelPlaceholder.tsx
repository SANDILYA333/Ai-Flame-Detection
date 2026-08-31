"use client";

import React from "react";
import { EventIntelligenceFeed, EventIntelligenceFeedProps } from "@/components/events/EventIntelligenceFeed";

export interface IntelligencePanelProps extends EventIntelligenceFeedProps {}

export function IntelligencePanelPlaceholder(props: IntelligencePanelProps) {
  return <EventIntelligenceFeed {...props} />;
}
