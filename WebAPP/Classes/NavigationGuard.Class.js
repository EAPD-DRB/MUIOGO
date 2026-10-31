import { Message } from "./Message.Class.js";

let activeGuard = null;
let leaveRequestPending = false;

async function runAllowed(guard, onAllowed) {
    // A destination may install its own guard. Restore the original only when
    // navigation fails or is refused before a replacement guard takes over.
    NavigationGuard.deactivate();
    try {
        const result = await onAllowed();
        if (result === false && !activeGuard) NavigationGuard.activate(guard);
        return result;
    } catch (error) {
        if (!activeGuard) NavigationGuard.activate(guard);
        throw error;
    }
}

// Warn before reloading or closing a page with unsaved changes
function handleBeforeUnload(event) {
    if (!activeGuard || !activeGuard.hasChanges()) {
        return;
    }

    event.preventDefault();
    event.returnValue = "";
}

// Controls whether the user can leave a page with unsaved changes
export class NavigationGuard {
    // Starts checking the current page for unsaved changes
    static activate(handlers) {
        activeGuard = handlers;
        leaveRequestPending = false;
        window.addEventListener("beforeunload", handleBeforeUnload);
    }

    // Stops checking after the user leaves the page
    static deactivate() {
        activeGuard = null;
        leaveRequestPending = false;
        window.removeEventListener("beforeunload", handleBeforeUnload);
    }

    // Checks whether the user can leave, then continues when allowed
    static async requestLeave(onAllowed, onBlocked = () => {}) {
        if (!activeGuard) {
            return await onAllowed();
        }

        if (leaveRequestPending) {
            return;
        }

        if (!activeGuard.hasChanges()) {
            return await runAllowed(activeGuard, onAllowed);
        }

        leaveRequestPending = true;

        // Wait for the user to choose whether to save or leave
        try {
            const choice = await Message.confirmUnsavedModelChanges();

            if (choice === "Don't save") {
                return await runAllowed(activeGuard, onAllowed);
            }

            if (choice === "Save") {
                // update() owns persistence and any follow-up navigation. Restore
                // the accepted URL while that asynchronous save is in progress.
                activeGuard.update();
                onBlocked();
            }
        } finally {
            leaveRequestPending = false;
        }
    }
}
