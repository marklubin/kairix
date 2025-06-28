import { useHotkey } from '@/contexts/HotkeyContext';
import { getHotkeysByCategory } from '@/services/hotkeys/defaultHotkeys';
import { cn } from '@/lib/utils';
import { X } from 'lucide-react';
import { Button } from './button';

export function HotkeyOverlay() {
  const { hotkeyConfig, showOverlay, setShowOverlay } = useHotkey();
  
  if (!showOverlay) return null;
  
  const categories = getHotkeysByCategory();
  
  // Format hotkey for display (e.g., "cmd+k, ctrl+k" -> "⌘K / Ctrl+K")
  const formatHotkey = (keys: string): string => {
    return keys
      .split(',')
      .map(key => key.trim())
      .map(key => {
        return key
          .replace(/cmd\+/g, '⌘')
          .replace(/ctrl\+/g, 'Ctrl+')
          .replace(/shift\+/g, 'Shift+')
          .replace(/alt\+/g, 'Alt+')
          .replace(/\+(.)/g, (_, char) => char.toUpperCase());
      })
      .join(' / ');
  };
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={() => setShowOverlay(false)}
      />
      
      {/* Overlay Content */}
      <div className="relative bg-background/95 backdrop-blur border rounded-lg shadow-lg max-w-4xl w-full max-h-[80vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Keyboard Shortcuts</h2>
          <Button
            size="icon"
            variant="ghost"
            onClick={() => setShowOverlay(false)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        
        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {categories.map(category => (
              <div key={category.name}>
                <h3 className="font-semibold mb-3 text-sm text-muted-foreground uppercase tracking-wider">
                  {category.name}
                </h3>
                <div className="space-y-2">
                  {category.actions.map(action => {
                    const keys = hotkeyConfig[action.id] || action.defaultKeys;
                    return (
                      <div
                        key={action.id}
                        className="flex items-center justify-between p-2 rounded hover:bg-muted/50"
                      >
                        <div className="flex-1">
                          <div className="font-medium text-sm">{action.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {action.description}
                          </div>
                        </div>
                        <div className="ml-4">
                          <kbd className={cn(
                            "px-2 py-1 text-xs font-mono",
                            "bg-muted rounded border",
                            "text-muted-foreground"
                          )}>
                            {formatHotkey(keys)}
                          </kbd>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
          
          {/* Footer Note */}
          <div className="mt-6 pt-6 border-t text-center text-sm text-muted-foreground">
            Press {formatHotkey(hotkeyConfig.showHotkeys || 'cmd+?, ctrl+?')} to toggle this overlay
          </div>
        </div>
      </div>
    </div>
  );
}