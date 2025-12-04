import { useCallback } from 'react';

export function useSelectableClick() {
  const createClickHandler = useCallback(
    <T extends any[]>(callback: (...args: T) => void) => 
      (...args: [...T, React.MouseEvent]) => {
        const event = args[args.length - 1] as React.MouseEvent;
        
        // Check if the user has text selected
        const selection = window.getSelection();
        if (selection && selection.toString().length > 0) {
          return;
        }

        // Ignore multi-clicks (double-click, triple-click, etc.)
        if (event.detail > 1) {
          return;
        }

        // Call the original callback with all arguments except the event
        const callbackArgs = args.slice(0, -1) as T;
        callback(...callbackArgs);
      },
    []
  );

  return { createClickHandler };
}