'use client';

export const useAuth = () => ({
    user: { name: "John Doe", plan: "Pro" },
    isAuthenticated: true,
    logout: () => console.log("Logout"),
});
