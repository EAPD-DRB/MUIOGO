/**
 * Global API Error Boundary and Toast Fallback System
 * Provides centralized error handling for AJAX requests and UI failures
 */
class ErrorBoundaryClass {
  constructor() {
    this.isInitialized = false;
    this.errorCount = 0;
    this.maxErrors = 10; // Prevent error spam
    this.errorCache = new Set(); // Prevent duplicate error messages

    this.setupGlobalErrorHandling();
    this.setupAjaxInterceptor();
  }

  /**
   * Initialize global error handling
   */
  setupGlobalErrorHandling() {
    const self = this;

    // Global JavaScript error handler
    window.addEventListener("error", function (event) {
      self.handleGlobalError({
        type: "javascript",
        message: event.message,
        source: event.filename,
        line: event.lineno,
        column: event.colno,
        error: event.error,
      });
    });

    // Unhandled promise rejection handler
    window.addEventListener("unhandledrejection", function (event) {
      self.handleGlobalError({
        type: "promise",
        message: event.reason?.message || "Unhandled promise rejection",
        reason: event.reason,
      });
    });

    this.isInitialized = true;
  }

  /**
   * Setup jQuery AJAX error interceptor
   */
  setupAjaxInterceptor() {
    const self = this;

    if (typeof $ !== "undefined" && $.ajaxSetup) {
      // Global AJAX error handler
      $(document).ajaxError(function (event, jqXHR, ajaxSettings, thrownError) {
        self.handleAPIError({
          status: jqXHR.status,
          statusText: jqXHR.statusText,
          responseText: jqXHR.responseText,
          url: ajaxSettings.url,
          method: ajaxSettings.type || "GET",
          error: thrownError,
        });
      });

      // Setup default AJAX settings for better error handling
      $.ajaxSetup({
        timeout: 30000, // 30 second timeout
        cache: false,
        beforeSend: function (xhr, settings) {
          // Add loading state management if needed
          self.onAPIRequestStart(settings);
        },
        complete: function (xhr, textStatus) {
          // Clean up loading states
          self.onAPIRequestComplete(xhr, textStatus);
        },
      });
    }
  }

  /**
   * Handle API-specific errors (500, 404, network failures)
   */
  handleAPIError(errorInfo) {
    if (this.errorCount >= this.maxErrors) return;

    const errorKey = `${errorInfo.status}-${errorInfo.url}`;
    if (this.errorCache.has(errorKey)) return;

    this.errorCache.add(errorKey);
    this.errorCount++;

    let userMessage = "An error occurred while communicating with the server.";
    let errorLevel = "warning";

    // Customize message based on error type
    switch (errorInfo.status) {
      case 0:
        userMessage =
          "Network connection failed. Please check your internet connection.";
        errorLevel = "error";
        break;
      case 400:
        userMessage = "Invalid request. Please check your input and try again.";
        break;
      case 401:
        userMessage = "Authentication required. Please refresh the page.";
        errorLevel = "error";
        break;
      case 403:
        userMessage =
          "Access denied. You may not have permission for this action.";
        errorLevel = "error";
        break;
      case 404:
        userMessage = "The requested resource was not found.";
        break;
      case 500:
        userMessage =
          "Server error occurred. The development team has been notified.";
        errorLevel = "error";
        break;
      case 502:
      case 503:
      case 504:
        userMessage =
          "Server is temporarily unavailable. Please try again in a moment.";
        errorLevel = "error";
        break;
    }

    // Show user-friendly notification
    this.showErrorToast(userMessage, errorLevel, errorInfo);

    // Log detailed error for debugging
    this.logError("API", errorInfo);
  }

  /**
   * Handle general JavaScript errors
   */
  handleGlobalError(errorInfo) {
    if (this.errorCount >= this.maxErrors) return;

    this.errorCount++;

    // Only show critical errors to users
    if (errorInfo.type === "javascript" && errorInfo.message) {
      this.showErrorToast(
        "An unexpected error occurred. Please refresh the page if problems persist.",
        "warning",
        errorInfo,
      );
    }

    this.logError("Global", errorInfo);
  }

  /**
   * Display error toast using SmartAdmin notification system
   */
  showErrorToast(message, level = "warning", errorDetails = null) {
    try {
      // Use existing SmartAdmin notification system
      if (typeof $.bigBox === "function") {
        $.bigBox({
          title: level === "error" ? "Error" : "Warning",
          content: message,
          color: level === "error" ? "#C46A69" : "#C79121",
          icon:
            level === "error"
              ? "fa fa-warning shake animated"
              : "fa fa-exclamation swing animated",
          number: "1",
          timeout: level === "error" ? 8000 : 5000,
        });
      }
      // Fallback to Message class if available (ES6 module import)
      else if (typeof window.Message !== "undefined") {
        if (level === "error") {
          window.Message.danger(message);
        } else {
          window.Message.warning(message);
        }
      }
      // Last resort: browser alert for critical errors
      else if (level === "error") {
        console.error("MUIOGO Error:", message, errorDetails);
        // Only show alert for critical errors when no other notification system available
        if (
          errorDetails &&
          (errorDetails.status === 0 || errorDetails.status >= 500)
        ) {
          alert("Critical Error: " + message);
        }
      }
    } catch (notificationError) {
      console.error("Error showing notification:", notificationError);
      console.error("Original error:", message, errorDetails);
    }
  }

  /**
   * Log errors for debugging and monitoring
   */
  logError(category, errorInfo) {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      category,
      userAgent: navigator.userAgent,
      url: window.location.href,
      ...errorInfo,
    };

    console.group(`🔥 MUIOGO ${category} Error - ${timestamp}`);
    console.error("Error Details:", logEntry);
    console.groupEnd();

    // Store in sessionStorage for debugging (limit to 50 entries)
    try {
      const errorLog = JSON.parse(
        sessionStorage.getItem("muiogo_error_log") || "[]",
      );
      errorLog.push(logEntry);
      if (errorLog.length > 50) {
        errorLog.splice(0, errorLog.length - 50);
      }
      sessionStorage.setItem("muiogo_error_log", JSON.stringify(errorLog));
    } catch (storageError) {
      console.warn("Could not store error log:", storageError);
    }
  }

  /**
   * API request lifecycle management
   */
  onAPIRequestStart(settings) {
    // Add request tracking if needed
    // Could integrate with loading spinners, etc.
  }

  onAPIRequestComplete(xhr, textStatus) {
    // Clean up request tracking
    // Remove loading indicators, etc.
  }

  /**
   * Recovery utilities
   */
  clearErrorCache() {
    this.errorCache.clear();
    this.errorCount = 0;
  }

  getErrorLog() {
    try {
      return JSON.parse(sessionStorage.getItem("muiogo_error_log") || "[]");
    } catch (e) {
      return [];
    }
  }

  exportErrorLog() {
    const log = this.getErrorLog();
    const blob = new Blob([JSON.stringify(log, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `muiogo-error-log-${new Date().toISOString().split("T")[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /**
   * Graceful sidebar recovery for known sidebar failure scenarios
   */
  recoverSidebar() {
    try {
      // Attempt to reload sidebar
      if (typeof $ !== "undefined") {
        $("aside").load(
          "App/View/Sidebar.html",
          function (response, status) {
            if (status === "success") {
              this.showErrorToast("Sidebar recovered successfully.", "info");
            } else {
              console.error("Sidebar recovery failed:", status);
            }
          }.bind(this),
        );
      }
    } catch (e) {
      console.error("Sidebar recovery failed:", e);
    }
  }
}

// Auto-initialize when DOM is ready
$(document).ready(function () {
  if (typeof window.MUIErrorBoundary === "undefined") {
    window.MUIErrorBoundary = new ErrorBoundaryClass();
    console.log("✅ MUIOGO Error Boundary initialized");
  }
});

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = ErrorBoundaryClass;
}

// Make available as window global for non-module usage
window.ErrorBoundaryClass = ErrorBoundaryClass;
