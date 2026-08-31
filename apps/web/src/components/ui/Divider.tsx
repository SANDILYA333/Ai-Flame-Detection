import React from "react";
import { cn } from "@/lib/utils";

export interface DividerProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "horizontal" | "vertical";
}

export function Divider({
  className,
  orientation = "horizontal",
  ...props
}: DividerProps) {
  if (orientation === "vertical") {
    return (
      <div
        className={cn("w-[1px] h-full bg-border/80 self-stretch my-auto", className)}
        {...props}
      />
    );
  }

  return (
    <div
      className={cn("h-[1px] w-full bg-border/80 my-2", className)}
      {...props}
    />
  );
}
