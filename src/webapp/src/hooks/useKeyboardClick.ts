import { KeyboardEvent, MouseEvent } from "react";

/**
 * Utility to make clickable elements keyboard accessible
 * Handles Enter and Space key presses to trigger click actions
 * This is a pure function, not a hook, so it can be used inside loops
 */
export function getKeyboardProps<T = HTMLElement>(
  onClick?: (event: MouseEvent<T> | KeyboardEvent<T>) => void
) {
  const handleKeyDown = (event: KeyboardEvent<T>) => {
    // Only trigger on Enter or Space keys
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault(); // Prevent page scroll on Space
      onClick?.(event);
    }
  };

  return {
    onClick,
    onKeyDown: handleKeyDown,
    tabIndex: 0,
    role: "button" as const,
  };
}

// Keep the hook version for backward compatibility if needed at top level
export function useKeyboardClick<T = HTMLElement>(
  onClick?: (event: MouseEvent<T> | KeyboardEvent<T>) => void
) {
  return getKeyboardProps(onClick);
}
