"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface DeterministicAvatarProps {
    name: string;
    className?: string;
    size?: number;
}

const COLORS = [
    ["#FFAD08", "#EDD75A"],
    ["#73BBC5", "#108496"],
    ["#3F51B5", "#2196F3"],
    ["#F44336", "#E91E63"],
    ["#9C27B0", "#673AB7"],
    ["#4CAF50", "#8BC34A"],
];

function getHashOfString(str: string) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    hash = Math.abs(hash);
    return hash;
}

export function DeterministicAvatar({ name, className, size = 40 }: DeterministicAvatarProps) {
    const initials = useMemo(() => {
        return name
            .split(" ")
            .map((n) => n[0])
            .join("")
            .slice(0, 2)
            .toUpperCase();
    }, [name]);

    const colorPair = useMemo(() => {
        const hash = getHashOfString(name);
        return COLORS[hash % COLORS.length];
    }, [name]);

    return (
        <svg
            viewBox="0 0 100 100"
            version="1.1"
            xmlns="http://www.w3.org/2000/svg"
            className={cn("rounded-full", className)}
            width={size}
            height={size}
        >
            <defs>
                <linearGradient id={`gradient-${name}`} x1="0" x2="1" y1="0" y2="1">
                    <stop offset="0%" stopColor={colorPair[0]} />
                    <stop offset="100%" stopColor={colorPair[1]} />
                </linearGradient>
            </defs>
            <rect width="100" height="100" fill={`url(#gradient-${name})`} />
            <text
                x="50"
                y="50"
                alignmentBaseline="central"
                textAnchor="middle"
                fill="white"
                fontSize="40"
                fontWeight="bold"
                dy="2" // slight vertical adjustment
            >
                {initials}
            </text>
        </svg>
    );
}
