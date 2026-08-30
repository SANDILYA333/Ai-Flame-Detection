import React from 'react';

export type TimeRange = '1h' | '6h' | '24h' | '48h' | '7d' | 'all';

interface TimeRangeControlsProps {
  selectedRange: TimeRange;
  onSelectRange: (range: TimeRange) => void;
}

export const TimeRangeControls: React.FC<TimeRangeControlsProps> = ({
  selectedRange,
  onSelectRange,
}) => {
  const ranges: { id: TimeRange; label: string }[] = [
    { id: '1h', label: '1h' },
    { id: '6h', label: '6h' },
    { id: '24h', label: '24h' },
    { id: '48h', label: '48h' },
    { id: '7d', label: '7d' },
    { id: 'all', label: 'All' },
  ];

  return (
    <div className="bg-[#0c0d12]/90 backdrop-blur-md border border-[#232836] rounded-xl p-1 shadow-lg flex items-center gap-1 font-sans text-xs select-none">
      {ranges.map((r) => {
        const isActive = selectedRange === r.id;
        return (
          <button
            key={r.id}
            onClick={() => onSelectRange(r.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              isActive
                ? 'bg-[#00f0ff] text-[#0c0d12] shadow-[0_0_12px_rgba(0,240,255,0.4)] font-bold'
                : 'text-[#8b92a4] hover:text-white hover:bg-[#161922]'
            }`}
          >
            {r.label}
          </button>
        );
      })}
    </div>
  );
};
