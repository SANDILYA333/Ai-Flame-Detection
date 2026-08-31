import React from "react";
import { Search } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SearchInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  shortcut?: string;
  onClear?: () => void;
}

export const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  ({ className, shortcut = "⌘K", value, onClear, ...props }, ref) => {
    return (
      <div className={cn("relative flex items-center w-full", className)}>
        <Search className="absolute left-2.5 w-3.5 h-3.5 text-foreground-muted pointer-events-none" />
        <input
          ref={ref}
          value={value}
          className="w-full h-8 pl-8 pr-12 text-xs bg-surface/90 border border-border rounded-control text-foreground placeholder:text-foreground-muted/70 transition-all duration-150 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent focus:bg-surface"
          {...props}
        />
        {shortcut && !value && (
          <kbd className="absolute right-2 px-1.5 py-0.5 text-[9px] font-mono text-foreground-muted bg-surface-raised border border-border rounded pointer-events-none uppercase">
            {shortcut}
          </kbd>
        )}
        {value && onClear && (
          <button
            type="button"
            onClick={onClear}
            className="absolute right-2 w-4 h-4 rounded text-foreground-muted hover:text-foreground hover:bg-surface-hover flex items-center justify-center text-xs"
          >
            ×
          </button>
        )}
      </div>
    );
  }
);

SearchInput.displayName = "SearchInput";
