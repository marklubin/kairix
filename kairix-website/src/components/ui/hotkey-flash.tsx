import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface HotkeyFlash {
  id: string;
  keys: string;
  action: string;
}

export function HotkeyFlashModal() {
  const [flashes, setFlashes] = useState<HotkeyFlash[]>([]);

  useEffect(() => {
    // Listen for hotkey flash events
    const handleFlash = (event: CustomEvent<{ keys: string; action: string }>) => {
      const flash: HotkeyFlash = {
        id: Date.now().toString(),
        keys: event.detail.keys,
        action: event.detail.action
      };

      setFlashes(prev => [...prev, flash]);

      // Remove after animation
      setTimeout(() => {
        setFlashes(prev => prev.filter(f => f.id !== flash.id));
      }, 2000);
    };

    window.addEventListener('hotkey-flash' as any, handleFlash);
    return () => window.removeEventListener('hotkey-flash' as any, handleFlash);
  }, []);

  const formatHotkey = (keys: string): string => {
    return keys
      .split(',')[0]
      .trim()
      .replace(/cmd\+/g, '⌘')
      .replace(/ctrl\+/g, 'Ctrl+')
      .replace(/shift\+/g, 'Shift+')
      .replace(/alt\+/g, 'Alt+')
      .replace(/\+(.)/g, (_, char) => char.toUpperCase());
  };

  return (
    <div className="fixed bottom-8 right-8 z-50 space-y-2">
      {flashes.map((flash, index) => (
        <div
          key={flash.id}
          className={cn(
            "bg-background/95 backdrop-blur border rounded-lg shadow-lg p-4",
            "flex items-center gap-3 min-w-[200px]",
            "animate-in slide-in-from-bottom-5 fade-in duration-300",
            index > 0 && "opacity-60"
          )}
          style={{
            animationDelay: `${index * 50}ms`
          }}
        >
          <kbd className="px-2 py-1 text-sm font-mono bg-muted rounded border">
            {formatHotkey(flash.keys)}
          </kbd>
          <span className="text-sm font-medium">
            {flash.action}
          </span>
        </div>
      ))}
    </div>
  );
}

// Helper function to trigger flash
export function flashHotkey(keys: string, action: string) {
  window.dispatchEvent(new CustomEvent('hotkey-flash', {
    detail: { keys, action }
  }));
}