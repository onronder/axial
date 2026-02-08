/**
 * Custom 404 Page
 *
 * Shown when a user navigates to a URL that doesn't match any route.
 * Uses inline styles because this page can render outside the root layout.
 */

import Link from "next/link";

export default function NotFound() {
    return (
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
                <p
                    style={{
                        fontSize: "5rem",
                        fontWeight: "bold",
                        lineHeight: "1",
                        marginBottom: "0.5rem",
                        background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                    }}
                >
                    404
                </p>

                <h1
                    style={{
                        fontSize: "1.5rem",
                        fontWeight: "bold",
                        marginBottom: "1rem",
                    }}
                >
                    Page not found
                </h1>

                <p
                    style={{
                        color: "#a1a1aa",
                        marginBottom: "2rem",
                        lineHeight: "1.6",
                    }}
                >
                    The page you&apos;re looking for doesn&apos;t exist or has been moved.
                </p>

                <div style={{ display: "flex", gap: "0.75rem", justifyContent: "center" }}>
                    <Link
                        href="/dashboard"
                        style={{
                            backgroundColor: "#3b82f6",
                            color: "white",
                            padding: "0.75rem 1.5rem",
                            borderRadius: "0.5rem",
                            border: "none",
                            cursor: "pointer",
                            fontSize: "1rem",
                            fontWeight: "500",
                            textDecoration: "none",
                        }}
                    >
                        Go to Dashboard
                    </Link>

                    <Link
                        href="/"
                        style={{
                            backgroundColor: "transparent",
                            color: "#a1a1aa",
                            padding: "0.75rem 1.5rem",
                            borderRadius: "0.5rem",
                            border: "1px solid #27272a",
                            cursor: "pointer",
                            fontSize: "1rem",
                            fontWeight: "500",
                            textDecoration: "none",
                        }}
                    >
                        Go Home
                    </Link>
                </div>
            </div>
        </div>
    );
}
