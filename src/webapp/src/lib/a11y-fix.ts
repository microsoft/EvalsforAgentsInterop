/**
 * Accessibility utility to fix aria-hidden elements that are focusable
 * Removes tabindex from elements with aria-hidden="true" to prevent keyboard focus
 * This addresses the WCAG violation where hidden elements should not be focusable
 */

export function fixAriaHiddenFocus() {
  // Find all elements with aria-hidden="true" and remove any positive tabindex
  const hiddenElements = document.querySelectorAll('[aria-hidden="true"]')

  hiddenElements.forEach((element) => {
    const tabindex = element.getAttribute('tabindex')
    // Remove tabindex if it's >= 0 (focusable)
    if (tabindex !== null && parseInt(tabindex) >= 0) {
      element.removeAttribute('tabindex')
    }
  })
}

// Run on initial page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', fixAriaHiddenFocus)
} else {
  fixAriaHiddenFocus()
}

// Aggressively watch for new aria-hidden elements and fix them immediately
const observer = new MutationObserver(() => {
  // Run the fix continuously to catch newly created elements
  requestAnimationFrame(() => {
    const hiddenElements = document.querySelectorAll('[aria-hidden="true"][tabindex]')
    hiddenElements.forEach((element) => {
      const tabindex = element.getAttribute('tabindex')
      if (tabindex !== null && parseInt(tabindex) >= 0) {
        element.removeAttribute('tabindex')
      }
    })
  })
})

// Observe the entire document for changes
observer.observe(document.documentElement, {
  subtree: true,
  attributes: false,
  childList: true,
  characterData: false,
})
