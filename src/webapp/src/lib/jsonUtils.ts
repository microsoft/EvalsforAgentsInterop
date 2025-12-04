/**
 * Utility functions for handling JSON formatting and parsing
 */

/**
 * Formats a JSON value for display, handling escaped strings and proper indentation
 * @param value - The value to format (can be string, object, or any JSON-serializable type)
 * @returns A formatted JSON string with proper indentation
 */
export function formatJsonForDisplay(value: any): string {
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return value;
    }
  }
  return JSON.stringify(value, null, 2);
}

/**
 * Advanced JSON formatter with custom handling for escaped characters and nested objects
 * Used specifically for tool response formatting with proper escape sequence handling
 * @param obj - The object to format
 * @param indent - Current indentation level
 * @returns A formatted JSON string with proper indentation and escape handling
 */
export function formatResponseJson(obj: any, indent = 0): string {
  const spaces = '  '.repeat(indent);
  
  if (obj === null) return 'null';
  if (typeof obj === 'boolean') return obj.toString();
  if (typeof obj === 'number') return obj.toString();
  if (typeof obj === 'string') {
    const cleaned = obj
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\r/g, '\r')
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, '\\');
    return `"${cleaned}"`;
  }
  
  if (Array.isArray(obj)) {
    if (obj.length === 0) return '[]';
    const items = obj.map(item => `${spaces}  ${formatResponseJson(item, indent + 1)}`).join(',\n');
    return `[\n${items}\n${spaces}]`;
  }
  
  if (typeof obj === 'object') {
    const entries = Object.entries(obj);
    if (entries.length === 0) return '{}';
    const items = entries.map(([key, value]) => 
      `${spaces}  "${key}": ${formatResponseJson(value, indent + 1)}`
    ).join(',\n');
    return `{\n${items}\n${spaces}}`;
  }
  
  return String(obj);
}

/**
 * Safely attempts to parse a JSON string, returning the original value if parsing fails
 * @param value - The value to parse
 * @returns The parsed JSON object or the original value if parsing fails
 */
export function safeJsonParse(value: any): any {
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }
  return value;
}

/**
 * Determines if a response is considered "long" and should be collapsible
 * @param response - The response object to check
 * @returns True if the response should be collapsible
 */
export function isResponseLong(response: any): boolean {
  const responseText = JSON.stringify(response, null, 2);
  return responseText.length > 500 || responseText.split('\n').length > 10;
}

/**
 * Gets a truncated version of a response for preview
 * @param response - The response object to truncate
 * @returns A truncated string representation
 */
export function getTruncatedResponse(response: any): string {
  const responseText = JSON.stringify(response, null, 2);
  const lines = responseText.split('\n');
  if (lines.length <= 10) return responseText;
  return lines.slice(0, 10).join('\n') + '\n...';
}