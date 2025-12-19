'use client';

import { useTheme as useNextTheme } from "next-themes";

export const useTheme = () => {
    const { theme, setTheme, resolvedTheme } = useNextTheme();
    return { theme, setTheme, resolvedTheme };
};
