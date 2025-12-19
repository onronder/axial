"use client";

import { useState } from "react";

export const useAuth = () => {
    // Mock user state
    const [user, setUser] = useState<{ name: string; email: string; plan: string } | null>({
        name: "John Doe",
        email: "john@example.com",
        plan: "Pro"
    });

    const login = async (email: string, pass: string) => {
        console.log("Mock login", email);
        setUser({ name: "John Doe", email, plan: "Pro" });
        return true;
    };

    const register = async (name: string, email: string, pass: string) => {
        console.log("Mock register", name, email);
        setUser({ name, email, plan: "Free" });
        return true;
    };

    const logout = () => {
        console.log("Mock logout");
        setUser(null);
    }

    return {
        user,
        isAuthenticated: !!user,
        login,
        register,
        logout
    };
};
