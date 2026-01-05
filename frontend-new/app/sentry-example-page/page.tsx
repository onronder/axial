"use client";

import * as Sentry from "@sentry/nextjs";

export default function SentryExamplePage() {
    const triggerError = () => {
        // This will trigger a Sentry error
        throw new Error("Sentry Frontend Test Error - This is a test!");
    };

    const triggerSentryError = () => {
        // Alternative: Use Sentry's captureException
        Sentry.captureException(new Error("Manual Sentry Test Error from Frontend"));
        alert("Error sent to Sentry! Check your Sentry dashboard.");
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100 dark:bg-gray-900">
            <div className="bg-white dark:bg-gray-800 p-8 rounded-lg shadow-lg max-w-md w-full text-center">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                    🐞 Sentry Test Page
                </h1>
                <p className="text-gray-600 dark:text-gray-300 mb-6">
                    Click the button below to trigger a test error and verify Sentry integration.
                </p>

                <div className="space-y-4">
                    <button
                        onClick={triggerSentryError}
                        className="w-full py-3 px-4 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors"
                    >
                        Send Test Error to Sentry
                    </button>

                    <button
                        onClick={triggerError}
                        className="w-full py-3 px-4 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors"
                    >
                        Throw Uncaught Error (Crash Page)
                    </button>
                </div>

                <p className="text-sm text-gray-500 dark:text-gray-400 mt-6">
                    After clicking, check the Sentry dashboard for the error.
                </p>
            </div>
        </div>
    );
}
