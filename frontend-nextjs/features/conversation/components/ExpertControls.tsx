'use client';

import { Plus } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface ExpertControlsProps {
  activeExpertPerspective: string;
  expertPerspectiveOptions: readonly string[];
  onExpertPerspectiveChange?: (next: string) => void;
  summonOptions: readonly string[];
  onSummonExpert?: (target: string) => void;
}

export function ExpertControls({
  activeExpertPerspective,
  expertPerspectiveOptions,
  onExpertPerspectiveChange,
  summonOptions,
  onSummonExpert,
}: ExpertControlsProps) {
  const [showSummonMenu, setShowSummonMenu] = useState(false);
  const summonMenuRef = useRef<HTMLDivElement>(null);
  const canChoosePerspective = expertPerspectiveOptions.length > 0;
  const canSummonExpert = summonOptions.length > 0;

  useEffect(() => {
    if (!showSummonMenu) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (!summonMenuRef.current) return;
      if (!summonMenuRef.current.contains(event.target as Node)) {
        setShowSummonMenu(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowSummonMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [showSummonMenu]);

  if (!canChoosePerspective && !canSummonExpert) {
    return null;
  }

  return (
    <div className="mb-2 flex items-center rounded-[1rem] border border-white/10 bg-black/35 px-3 py-2 text-xs text-white/88 backdrop-blur-sm">
      <div className="inline-flex items-center gap-2">
        {canChoosePerspective && (
          <select
            value={activeExpertPerspective}
            onChange={(event) => onExpertPerspectiveChange?.(event.target.value)}
            className="ui-type-meta min-w-[132px] rounded-full border border-white/10 bg-black/45 px-2.5 py-1 text-white outline-none"
            aria-label="选择专家视角"
          >
            {expertPerspectiveOptions.map((option) => (
              <option key={option} value={option} className="bg-[#1f1f1f] text-white">
                {option}
              </option>
            ))}
          </select>
        )}
        {canSummonExpert && (
          <div ref={summonMenuRef} className="relative">
          <button
            type="button"
            onClick={() => setShowSummonMenu((prev) => !prev)}
            className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/10 bg-black/45 text-white transition hover:border-white/10 hover:bg-black/45"
            aria-label="召集团队"
            title="召集团队"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
          {showSummonMenu && (
            <div className="absolute left-0 bottom-[calc(100%+8px)] min-w-[150px] rounded-2xl border border-white/10 bg-[#1f1f1f]/98 p-1.5 shadow-[0_18px_38px_rgba(0,0,0,0.36)] backdrop-blur-sm">
              {summonOptions.map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => {
                    onSummonExpert?.(option);
                    setShowSummonMenu(false);
                  }}
                  className="ui-type-meta flex w-full items-center justify-start rounded-xl px-2.5 py-2 text-white/92 transition hover:bg-white/8"
                >
                  {option}
                </button>
              ))}
            </div>
          )}
          </div>
        )}
      </div>
    </div>
  );
}
