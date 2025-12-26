"use client";

/**
 * Global Error Handler for Next.js App Router
 * 
 * This component catches unhandled errors in the app and reports them to Sentry.
 * It provides a user-friendly error UI while ensuring errors are tracked.
 */

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        // Report error to Sentry
        Sentry.captureException(error);
    }, [error]);

    return (
        <html>
            <body>
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        minHeight: "100vh",
                        padding: "2rem",
                        fontFamily: "system-ui, sans-serif",
                        backgroundColor: "#0a0a0a",
                        color: "#fafafa",
                    }}
                >
                    <div
                        style={{
                            textAlign: "center",
                            maxWidth: "500px",
                        }}
                    >
                        <h1
                            style={{
                                fontSize: "2rem",
                                fontWeight: "bold",
                                marginBottom: "1rem",
                            }}
                        >
                            Something went wrong
                        </h1>

                        <p
                            style={{
                                color: "#a1a1aa",
                                marginBottom: "2rem",
                                lineHeight: "1.6",
                            }}
                        >
                            We apologize for the inconvenience. Our team has been notified
                            and is working to fix this issue.
                        </p>

                        {error.digest && (
                            <p
                                style={{
                                    color: "#71717a",
                                    fontSize: "0.875rem",
                                    marginBottom: "1.5rem",
                                    fontFamily: "monospace",
                                }}
                            >
                                Error ID: {error.digest}
                            </p>
                        )}

                        <button
                            onClick={() => reset()}
                            style={{
                                backgroundColor: "#3b82f6",
                                color: "white",
                                padding: "0.75rem 1.5rem",
                                borderRadius: "0.5rem",
                                border: "none",
                                cursor: "pointer",
                                fontSize: "1rem",
                                fontWeight: "500",
                                marginRight: "0.5rem",
                            }}
                            onMouseOver={(e) => {
                                (e.target as HTMLButtonElement).style.backgroundColor = "#2563eb";
                            }}
                            onMouseOut={(e) => {
                                (e.target as HTMLButtonElement).style.backgroundColor = "#3b82f6";
                            }}
                        >
                            Try Again
                        </button>

                        <button
                            onClick={() => (window.location.href = "/")}
                            style={{
                                backgroundColor: "transparent",
                                color: "#a1a1aa",
                                padding: "0.75rem 1.5rem",
                                borderRadius: "0.5rem",
                                border: "1px solid #27272a",
                                cursor: "pointer",
                                fontSize: "1rem",
                                fontWeight: "500",
                            }}
                            onMouseOver={(e) => {
                                (e.target as HTMLButtonElement).style.borderColor = "#3f3f46";
                            }}
                            onMouseOut={(e) => {
                                (e.target as HTMLButtonElement).style.borderColor = "#27272a";
                            }}
                        >
                            Go Home
                        </button>
                    </div>
                </div>
            </body>
        </html>
    );
}
