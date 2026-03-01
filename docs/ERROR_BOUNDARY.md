# MUIOGO Error Boundary System

## Overview

The Error Boundary system provides centralized error handling for AJAX requests and UI failures in MUIOGO, addressing Issue 3: Global API Error Boundary and Toast Fallbacks.

## Features

- **Global AJAX Error Interception**: Automatically catches and handles all jQuery AJAX errors
- **JavaScript Error Handling**: Catches unhandled JavaScript errors and promise rejections
- **User-Friendly Toast Notifications**: Uses SmartAdmin's notification system with graceful fallbacks
- **Error Logging**: Stores error details in sessionStorage for debugging
- **Rate Limiting**: Prevents error spam with configurable limits
- **Recovery Utilities**: Includes methods for graceful recovery from common failures

## Files

### Core Files

- `WebAPP/Classes/ErrorBoundary.Class.js` - Main error boundary implementation
- `WebAPP/Classes/ErrorBoundary.Dev.js` - Development utilities for testing

### Enhanced Files

- `WebAPP/index.html` - Updated to include ErrorBoundary scripts
- `WebAPP/Routes/Routes.Class.js` - Enhanced with error handling integration
- `WebAPP/Classes/Message.Class.js` - Added API-specific error methods

## Usage

### Automatic Handling

The ErrorBoundary automatically handles:

- AJAX errors (network failures, 500 errors, etc.)
- JavaScript runtime errors
- Unhandled promise rejections

### Manual Usage

```javascript
// Show API errors
Message.showAPIError("Custom error message", { details: "Additional info" });
Message.showAPIWarning("Warning message");
Message.showNetworkError(); // Uses default message
Message.showServerError(); // Uses default message

// Access error boundary directly
if (window.MUIErrorBoundary) {
  window.MUIErrorBoundary.showErrorToast("Custom message", "error");
  window.MUIErrorBoundary.recoverSidebar(); // Attempt sidebar recovery
  window.MUIErrorBoundary.clearErrorCache(); // Clear error cache
  window.MUIErrorBoundary.exportErrorLog(); // Download error log
}
```

### Development Testing

In development environments (localhost), use the dev utilities:

```javascript
// Test different error scenarios
MUIErrorBoundaryDev.testAPIError(500); // Test 500 error
MUIErrorBoundaryDev.testJSError(); // Test JavaScript error
MUIErrorBoundaryDev.testPromiseError(); // Test promise rejection
MUIErrorBoundaryDev.simulateNetworkError(); // Test network failure
MUIErrorBoundaryDev.simulate404Error(); // Test 404 error

// Debug and monitoring
MUIErrorBoundaryDev.viewErrorLog(); // Console table of errors
MUIErrorBoundaryDev.exportErrorLog(); // Download error log
MUIErrorBoundaryDev.clearErrors(); // Clear error cache
MUIErrorBoundaryDev.testSidebarRecovery(); // Test sidebar recovery
```

## Error Types Handled

### API Errors

- **0**: Network connection failed
- **400**: Invalid request
- **401**: Authentication required
- **403**: Access denied
- **404**: Resource not found
- **500**: Server error
- **502/503/504**: Server unavailable

### JavaScript Errors

- Runtime JavaScript errors
- Unhandled promise rejections
- Route navigation failures

## Configuration

### Error Rate Limiting

```javascript
// Default settings in ErrorBoundary.Class.js
this.maxErrors = 10; // Maximum errors before stopping notifications
this.errorCache = new Set(); // Prevents duplicate error messages
```

### AJAX Settings

```javascript
// Default AJAX configuration
$.ajaxSetup({
  timeout: 30000, // 30 second timeout
  cache: false,
});
```

## Logging

Errors are automatically logged to:

1. Browser console (with grouped formatting)
2. SessionStorage (`muiogo_error_log` - limited to 50 entries)

### Log Format

```json
{
    "timestamp": "2026-03-02T10:30:00.000Z",
    "category": "API|Global|Route",
    "userAgent": "...",
    "url": "...",
    "status": 500,
    "message": "...",
    "error": {...}
}
```

## Integration with Existing Systems

### SmartAdmin Integration

- Primary notification method using `$.bigBox()`
- Fallback to existing Message class methods
- Last resort: browser alerts for critical errors

### Message Class Enhancement

New methods added to `Message.Class.js`:

- `showAPIError(message, details)`
- `showAPIWarning(message, details)`
- `showNetworkError(message)`
- `showServerError(message)`

### Routes Class Enhancement

Added to `Routes.Class.js`:

- `initializeErrorHandling()`
- `handleRouteError(route, error)`

## GSoC 2026 Compliance

This implementation aligns with GSoC 2026 objectives:

- **Platform Independence**: Consistent error handling across environments
- **Maintainability**: Centralized error management
- **User Experience**: Graceful degradation and recovery
- **No Parallel Architectures**: Enhances existing SmartAdmin notifications

## Testing

Use development utilities to test error scenarios:

1. Load the application in development (localhost)
2. Open browser console
3. Use `MUIErrorBoundaryDev` methods to simulate errors
4. Verify appropriate user notifications and error logging

## Recovery Features

### Sidebar Recovery

If the sidebar fails to load or becomes corrupted:

```javascript
window.MUIErrorBoundary.recoverSidebar();
```

### Error Cache Management

Clear accumulated errors and reset counters:

```javascript
window.MUIErrorBoundary.clearErrorCache();
```

