/**
 * Development utilities for testing Error Boundary
 * Only include in development builds
 */
if (
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
) {
  window.MUIErrorBoundaryDev = {
    // Test API error scenarios
    testAPIError: function (status = 500) {
      $.ajax({
        url: "/api/test-error-" + status,
        method: "GET",
      });
    },

    // Test JavaScript error
    testJSError: function () {
      setTimeout(() => {
        throw new Error("Test JavaScript error from ErrorBoundary.Dev");
      }, 100);
    },

    // Test Promise rejection
    testPromiseError: function () {
      Promise.reject(
        new Error("Test Promise rejection from ErrorBoundary.Dev"),
      );
    },

    // View error log
    viewErrorLog: function () {
      if (window.MUIErrorBoundary) {
        console.table(window.MUIErrorBoundary.getErrorLog());
      }
    },

    // Export error log
    exportErrorLog: function () {
      if (window.MUIErrorBoundary) {
        window.MUIErrorBoundary.exportErrorLog();
      }
    },

    // Clear error cache
    clearErrors: function () {
      if (window.MUIErrorBoundary) {
        window.MUIErrorBoundary.clearErrorCache();
        console.log("Error cache cleared");
      }
    },

    // Test sidebar recovery
    testSidebarRecovery: function () {
      if (window.MUIErrorBoundary) {
        window.MUIErrorBoundary.recoverSidebar();
      }
    },

    // Simulate various error scenarios
    simulateNetworkError: function () {
      $.ajax({
        url: "http://fake-nonexistent-domain.test/api/data",
        method: "GET",
      });
    },

    simulate404Error: function () {
      $.ajax({
        url: "/api/nonexistent-endpoint",
        method: "GET",
      });
    },

    simulate500Error: function () {
      // This would need a backend endpoint that returns 500
      $.ajax({
        url: "/api/force-500",
        method: "GET",
      });
    },
  };

  console.log(
    "🛠️ ErrorBoundary Dev utilities loaded. Use window.MUIErrorBoundaryDev",
  );
  console.log("Available methods:", Object.keys(window.MUIErrorBoundaryDev));
}
