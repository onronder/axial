"use client";

import { Upload, Server } from "lucide-react";
import { cn } from "@/lib/utils";

interface DataSourceIconProps {
  sourceId: string;
  className?: string;
  size?: "sm" | "md" | "lg";
}

// Google Drive Logo SVG (official multi-color)
const GoogleDriveIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M2 11.9556C2 8.47078 2 6.7284 2.67818 5.39739C3.27473 4.22661 4.22661 3.27473 5.39739 2.67818C6.7284 2 8.47078 2 11.9556 2H20.0444C23.5292 2 25.2716 2 26.6026 2.67818C27.7734 3.27473 28.7253 4.22661 29.3218 5.39739C30 6.7284 30 8.47078 30 11.9556V20.0444C30 23.5292 30 25.2716 29.3218 26.6026C28.7253 27.7734 27.7734 28.7253 26.6026 29.3218C25.2716 30 23.5292 30 20.0444 30H11.9556C8.47078 30 6.7284 30 5.39739 29.3218C4.22661 28.7253 3.27473 27.7734 2.67818 26.6026C2 25.2716 2 23.5292 2 20.0444V11.9556Z" fill="white"/>
    <path d="M16.0019 12.4507L12.541 6.34297C12.6559 6.22598 12.7881 6.14924 12.9203 6.09766C11.8998 6.43355 11.4315 7.57961 11.4315 7.57961L5.10895 18.7345C5.01999 19.0843 4.99528 19.4 5.0064 19.6781H11.9072L16.0019 12.4507Z" fill="#34A853"/>
    <path d="M16.002 12.4507L20.0967 19.6781H26.9975C27.0086 19.4 26.9839 19.0843 26.8949 18.7345L20.5724 7.57961C20.5724 7.57961 20.1029 6.43355 19.0835 6.09766C19.2145 6.14924 19.3479 6.22598 19.4628 6.34297L16.002 12.4507Z" fill="#FBBC05"/>
    <path d="M16.0019 12.4514L19.4628 6.34371C19.3479 6.22671 19.2144 6.14997 19.0835 6.09839C18.9327 6.04933 18.7709 6.01662 18.5954 6.00781H18.4125H13.5913H13.4084C13.2342 6.01536 13.0711 6.04807 12.9203 6.09839C12.7894 6.14997 12.6559 6.22671 12.541 6.34371L16.0019 12.4514Z" fill="#188038"/>
    <path d="M11.9082 19.6782L8.48687 25.7168C8.48687 25.7168 8.3732 25.6614 8.21875 25.5469C8.70434 25.9206 9.17633 25.9998 9.17633 25.9998H22.6134C23.3547 25.9998 23.5092 25.7168 23.5092 25.7168C23.5116 25.7155 23.5129 25.7142 23.5153 25.713L20.0965 19.6782H11.9082Z" fill="#4285F4"/>
    <path d="M11.9086 19.6782H5.00781C5.04241 20.4985 5.39826 20.9778 5.39826 20.9778L5.65773 21.4281C5.67627 21.4546 5.68739 21.4697 5.68739 21.4697L6.25205 22.461L7.51976 24.6676C7.55683 24.7569 7.60008 24.8386 7.6458 24.9166C7.66309 24.9431 7.67915 24.972 7.69769 24.9972C7.70263 25.0047 7.70757 25.0123 7.71252 25.0198C7.86944 25.2412 8.04489 25.4123 8.22034 25.5469C8.37479 25.6627 8.48847 25.7168 8.48847 25.7168L11.9086 19.6782Z" fill="#1967D2"/>
    <path d="M20.0967 19.6782H26.9974C26.9628 20.4985 26.607 20.9778 26.607 20.9778L26.3475 21.4281C26.329 21.4546 26.3179 21.4697 26.3179 21.4697L25.7532 22.461L24.4855 24.6676C24.4484 24.7569 24.4052 24.8386 24.3595 24.9166C24.3422 24.9431 24.3261 24.972 24.3076 24.9972C24.3026 25.0047 24.2977 25.0123 24.2927 25.0198C24.1358 25.2412 23.9604 25.4123 23.7849 25.5469C23.6305 25.6627 23.5168 25.7168 23.5168 25.7168L20.0967 19.6782Z" fill="#EA4335"/>
  </svg>
);

// OneDrive Logo SVG (official Microsoft)
const OneDriveIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="onedrive0" x1="4.42591" y1="24.6668" x2="27.2309" y2="23.2764" gradientUnits="userSpaceOnUse">
        <stop stopColor="#2086B8"/>
        <stop offset="1" stopColor="#46D3F6"/>
      </linearGradient>
      <linearGradient id="onedrive1" x1="23.8302" y1="19.6668" x2="30.2108" y2="15.2082" gradientUnits="userSpaceOnUse">
        <stop stopColor="#1694DB"/>
        <stop offset="1" stopColor="#62C3FE"/>
      </linearGradient>
      <linearGradient id="onedrive2" x1="8.51037" y1="7.33333" x2="23.3335" y2="15.9348" gradientUnits="userSpaceOnUse">
        <stop stopColor="#0D3D78"/>
        <stop offset="1" stopColor="#063B83"/>
      </linearGradient>
      <linearGradient id="onedrive3" x1="-0.340429" y1="19.9998" x2="14.5634" y2="14.4649" gradientUnits="userSpaceOnUse">
        <stop stopColor="#16589B"/>
        <stop offset="1" stopColor="#1464B7"/>
      </linearGradient>
      <mask id="onedriveMask" style={{ maskType: "alpha" }} maskUnits="userSpaceOnUse" x="0" y="6" width="32" height="20">
        <path d="M7.82979 26C3.50549 26 0 22.5675 0 18.3333C0 14.1921 3.35322 10.8179 7.54613 10.6716C9.27535 7.87166 12.4144 6 16 6C20.6308 6 24.5169 9.12183 25.5829 13.3335C29.1316 13.3603 32 16.1855 32 19.6667C32 23.0527 29 26 25.8723 25.9914L7.82979 26Z" fill="#C4C4C4"/>
      </mask>
    </defs>
    <g mask="url(#onedriveMask)">
      <path d="M7.83017 26.0001C5.37824 26.0001 3.18957 24.8966 1.75391 23.1691L18.0429 16.3335L30.7089 23.4647C29.5926 24.9211 27.9066 26.0001 26.0004 25.9915C23.1254 26.0001 12.0629 26.0001 7.83017 26.0001Z" fill="url(#onedrive0)"/>
      <path d="M25.5785 13.3149L18.043 16.3334L30.709 23.4647C31.5199 22.4065 32.0004 21.0916 32.0004 19.6669C32.0004 16.1857 29.1321 13.3605 25.5833 13.3337C25.5817 13.3274 25.5801 13.3212 25.5785 13.3149Z" fill="url(#onedrive1)"/>
      <path d="M7.06445 10.7028L18.0423 16.3333L25.5779 13.3148C24.5051 9.11261 20.6237 6 15.9997 6C12.4141 6 9.27508 7.87166 7.54586 10.6716C7.3841 10.6773 7.22358 10.6877 7.06445 10.7028Z" fill="url(#onedrive2)"/>
      <path d="M1.7535 23.1687L18.0425 16.3331L7.06471 10.7026C3.09947 11.0792 0 14.3517 0 18.3331C0 20.1665 0.657197 21.8495 1.7535 23.1687Z" fill="url(#onedrive3)"/>
    </g>
  </svg>
);

// SharePoint Logo SVG (official Microsoft)
const SharePointIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="sharepoint0" x1="6" y1="11.5" x2="26.5833" y2="11.5" gradientUnits="userSpaceOnUse">
        <stop stopColor="#103A3B"/>
        <stop offset="1" stopColor="#116B6E"/>
      </linearGradient>
      <linearGradient id="sharepoint1" x1="18" y1="13" x2="32" y2="21" gradientUnits="userSpaceOnUse">
        <stop stopColor="#1D9097"/>
        <stop offset="1" stopColor="#29BBC2"/>
      </linearGradient>
      <linearGradient id="sharepoint2" x1="12" y1="21.5" x2="23" y2="26.5" gradientUnits="userSpaceOnUse">
        <stop stopColor="#28A6B5"/>
        <stop offset="1" stopColor="#31D6EC"/>
      </linearGradient>
      <linearGradient id="sharepoint3" x1="0" y1="16" x2="19.5" y2="16" gradientUnits="userSpaceOnUse">
        <stop stopColor="#105557"/>
        <stop offset="1" stopColor="#116B6E"/>
      </linearGradient>
      <mask id="sharepointMask" style={{ maskType: "alpha" }} maskUnits="userSpaceOnUse" x="10" y="6" width="13" height="24">
        <path d="M23 23.5C23 27.0899 20.0899 30 16.5 30C12.9101 30 10 27.0899 10 23.5C10 19.9102 10 6 10 6H23C23 6 23 21.1988 23 23.5Z" fill="#C4C4C4"/>
      </mask>
    </defs>
    <circle cx="15.5" cy="11.5" r="9.5" fill="url(#sharepoint0)"/>
    <circle cx="24" cy="17" r="8" fill="url(#sharepoint1)"/>
    <g mask="url(#sharepointMask)">
      <circle cx="16.5" cy="23.5" r="6.5" fill="url(#sharepoint2)"/>
      <path d="M7 12C7 10.3431 8.34315 9 10 9H17C18.6569 9 20 10.3431 20 12V24C20 25.6569 18.6569 27 17 27H7V12Z" fill="#000000" fillOpacity="0.3"/>
    </g>
    <rect y="7" width="18" height="18" rx="2" fill="url(#sharepoint3)"/>
    <path d="M13 18.1229C13 16.5726 11.9602 15.8883 9.79665 15.0922C8.10273 14.4637 7.70021 14.2821 7.70021 13.6816C7.70021 13.1648 8.20335 12.8156 9.0587 12.8156C9.93082 12.8156 10.7526 13.1089 11.6751 13.6117L12.6143 11.9497C11.6247 11.3352 10.4507 11 9.02516 11C6.84486 11 5.28512 12.1173 5.28512 13.8212C5.28512 15.567 6.52621 16.1257 8.60587 16.8659C10.2662 17.4525 10.5849 17.7458 10.5849 18.2626C10.5849 18.8771 9.9979 19.1844 9.07547 19.1844C7.98532 19.1844 7.02935 18.8073 6.07338 18.1927L5 19.7849C6.174 20.595 7.63312 21 9.12579 21C11.3732 21 13 19.9385 13 18.1229Z" fill="white"/>
  </svg>
);

// Dropbox Logo SVG (official)
const DropboxIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 -1.5 48 48" xmlns="http://www.w3.org/2000/svg">
    <path d="M24,26.033255 L14.1195,34.34573 L0,25.053538 L9.7635,17.17347 L23.999971,26.033238 L38.2362,17.172109 L47.9997,25.05369 L33.8802,34.345881 L23.9997,26.033406 Z M14.1198,0 L0.0003,9.292191 L9.7638,17.17226 L24.0003,8.312475 L14.1198,0 Z M24.02895,27.821692 L14.11995,36.109976 L9.87945,33.318993 L9.87945,36.447132 L24.02895,45 L38.17845,36.447132 L38.17845,33.318993 L33.93795,36.109976 L24.02895,27.821692 Z M48,9.292343 L33.8805,0.000151 L24,8.312626 L38.2365,17.172411 L48,9.292343 Z" fill="#0F82E2"/>
  </svg>
);

// Notion Logo SVG (official)
const NotionIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M3.25781 3.11684C3.67771 3.45796 3.83523 3.43193 4.62369 3.37933L12.0571 2.93299C12.2147 2.93299 12.0836 2.77571 12.0311 2.74957L10.7965 1.85711C10.56 1.67347 10.2448 1.46315 9.64083 1.51576L2.44308 2.04074C2.18059 2.06677 2.12815 2.19801 2.2327 2.30322L3.25781 3.11684ZM3.7041 4.84917V12.6704C3.7041 13.0907 3.91415 13.248 4.38693 13.222L12.5562 12.7493C13.0292 12.7233 13.0819 12.4341 13.0819 12.0927V4.32397C13.0819 3.98306 12.9508 3.79921 12.6612 3.82545L4.12422 4.32397C3.80918 4.35044 3.7041 4.50803 3.7041 4.84917ZM11.7688 5.26872C11.8212 5.50518 11.7688 5.74142 11.5319 5.76799L11.1383 5.84641V11.6205C10.7965 11.8042 10.4814 11.9092 10.2188 11.9092C9.79835 11.9092 9.69305 11.7779 9.37812 11.3844L6.80345 7.34249V11.2532L7.61816 11.437C7.61816 11.437 7.61816 11.9092 6.96086 11.9092L5.14879 12.0143C5.09615 11.9092 5.14879 11.647 5.33259 11.5944L5.80546 11.4634V6.29276L5.1489 6.24015C5.09625 6.00369 5.22739 5.66278 5.5954 5.63631L7.53935 5.50528L10.2188 9.5998V5.97765L9.53564 5.89924C9.4832 5.61018 9.69305 5.40028 9.95576 5.37425L11.7688 5.26872ZM1.83874 1.33212L9.32557 0.780787C10.245 0.701932 10.4815 0.754753 11.0594 1.17452L13.4492 2.85424C13.8436 3.14309 13.975 3.22173 13.975 3.53661V12.7493C13.975 13.3266 13.7647 13.6681 13.0293 13.7203L4.33492 14.2454C3.78291 14.2717 3.52019 14.193 3.23111 13.8253L1.47116 11.5419C1.1558 11.1216 1.02466 10.8071 1.02466 10.4392V2.25041C1.02466 1.77825 1.23504 1.38441 1.83874 1.33212Z" fill="#000000"/>
  </svg>
);

// GitHub Logo SVG (for future use)
const GitHubIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <path d="M16 1.375c-8.282 0-14.996 6.714-14.996 14.996 0 6.585 4.245 12.18 10.148 14.195l0.106 0.031c0.75 0.141 1.025-0.322 1.025-0.721 0-0.356-0.012-1.3-0.019-2.549-4.171 0.905-5.051-2.012-5.051-2.012-0.288-0.925-0.878-1.685-1.653-2.184l-0.016-0.009c-1.358-0.93 0.105-0.911 0.105-0.911 0.987 0.139 1.814 0.718 2.289 1.53l0.008 0.015c0.554 0.995 1.6 1.657 2.801 1.657 0.576 0 1.116-0.152 1.582-0.419l-0.016 0.008c0.072-0.791 0.421-1.489 0.949-2.005l0.001-0.001c-3.33-0.375-6.831-1.665-6.831-7.41-0-0.027-0.001-0.058-0.001-0.089 0-1.521 0.587-2.905 1.547-3.938l-0.003 0.004c-0.203-0.542-0.321-1.168-0.321-1.821 0-0.777 0.166-1.516 0.465-2.182l-0.014 0.034s1.256-0.402 4.124 1.537c1.124-0.321 2.415-0.506 3.749-0.506s2.625 0.185 3.849 0.53l-0.1-0.024c2.849-1.939 4.105-1.537 4.105-1.537 0.285 0.642 0.451 1.39 0.451 2.177 0 0.642-0.11 1.258-0.313 1.83l0.012-0.038c0.953 1.032 1.538 2.416 1.538 3.937 0 0.031-0 0.061-0.001 0.091l0-0.005c0 5.761-3.505 7.029-6.842 7.398 0.632 0.647 1.022 1.532 1.022 2.509 0 0.093-0.004 0.186-0.011 0.278l0.001-0.012c0 2.007-0.019 3.619-0.019 4.106 0 0.394 0.262 0.862 1.031 0.712 6.028-2.029 10.292-7.629 10.292-14.226 0-8.272-6.706-14.977-14.977-14.977-0.006 0-0.013 0-0.019 0h0.001z" fill="currentColor"/>
  </svg>
);

// Amazon S3 Logo SVG (for future use)
const AmazonS3Icon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
    <path fill="#e05243" d="M260 348l-137 33V131l137 32z"/>
    <path fill="#8c3123" d="M256 349l133 32V131l-133 32v186"/>
    <path fill="#e05243" d="M256 64v97l58 14V93zM389 131v250l26-13V143zM256 238v97l58-8v-82zM314 367l-58 14v97l58-29z"/>
    <path fill="#8c3123" d="M256 448v-97l-58 14v54zM123 381V131l-26 12v226zM256 274v-97l-58 8v82zM198 145l58-14V34l-58 29z"/>
    <path fill="#5e1f18" d="M314 175l-58 11-58-11 58-15 58 15"/>
    <path fill="#f2b0a9" d="M314 337l-58-11-58 11 58 16 58-16"/>
  </svg>
);

// Slack Logo SVG
const SlackIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 127 127" xmlns="http://www.w3.org/2000/svg">
    <path d="M27.2 80c0 7.3-5.9 13.2-13.2 13.2S.8 87.3.8 80s5.9-13.2 13.2-13.2h13.2V80zm6.6 0c0-7.3 5.9-13.2 13.2-13.2s13.2 5.9 13.2 13.2v33c0 7.3-5.9 13.2-13.2 13.2s-13.2-5.9-13.2-13.2V80z" fill="#E01E5A" />
    <path d="M47 27c-7.3 0-13.2-5.9-13.2-13.2S39.7.6 47 .6s13.2 5.9 13.2 13.2V27H47zm0 6.7c7.3 0 13.2 5.9 13.2 13.2s-5.9 13.2-13.2 13.2H14c-7.3 0-13.2-5.9-13.2-13.2S6.7 33.7 14 33.7h33z" fill="#36C5F0" />
    <path d="M99.9 46.9c0-7.3 5.9-13.2 13.2-13.2s13.2 5.9 13.2 13.2-5.9 13.2-13.2 13.2H99.9V46.9zm-6.6 0c0 7.3-5.9 13.2-13.2 13.2S66.9 54.2 66.9 46.9V14c0-7.3 5.9-13.2 13.2-13.2s13.2 5.9 13.2 13.2v32.9z" fill="#2EB67D" />
    <path d="M80.1 99.8c7.3 0 13.2 5.9 13.2 13.2s-5.9 13.2-13.2 13.2-13.2-5.9-13.2-13.2V99.8h13.2zm0-6.6c-7.3 0-13.2-5.9-13.2-13.2s5.9-13.2 13.2-13.2h33c7.3 0 13.2 5.9 13.2 13.2s-5.9 13.2-13.2 13.2h-33z" fill="#ECB22E" />
  </svg>
);

// Microsoft Teams Logo
const TeamsIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M20.625 6.75h-5.25c-.621 0-1.125.504-1.125 1.125v5.25c0 .621.504 1.125 1.125 1.125h5.25c.621 0 1.125-.504 1.125-1.125v-5.25c0-.621-.504-1.125-1.125-1.125z" fill="#5059C9" />
    <circle cx="18" cy="4.5" r="1.5" fill="#5059C9" />
    <path d="M15.375 5.25a3.375 3.375 0 1 0 0-6.75 3.375 3.375 0 0 0 0 6.75z" fill="#7B83EB" />
    <path d="M13.5 7.5H3a1.5 1.5 0 0 0-1.5 1.5v6.75a5.25 5.25 0 0 0 10.5 0V9a1.5 1.5 0 0 0-1.5-1.5z" fill="#7B83EB" />
  </svg>
);

// Globe/Web Icon
const GlobeIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" stroke="url(#globeGradient)" strokeWidth="2" />
    <ellipse cx="12" cy="12" rx="4" ry="10" stroke="url(#globeGradient)" strokeWidth="2" />
    <path d="M2 12h20" stroke="url(#globeGradient)" strokeWidth="2" />
    <path d="M12 2c2.5 3.5 2.5 14.5 0 20" stroke="url(#globeGradient)" strokeWidth="2" />
    <defs>
      <linearGradient id="globeGradient" x1="2" y1="2" x2="22" y2="22">
        <stop stopColor="#10B981" />
        <stop offset="1" stopColor="#3B82F6" />
      </linearGradient>
    </defs>
  </svg>
);

// Confluence Logo
const ConfluenceIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 256 246" xmlns="http://www.w3.org/2000/svg">
    <path d="M9.26 187.86c-3.11 5.12-6.63 11.06-9.26 15.66a7.46 7.46 0 0 0 2.68 10.2l54.19 33.46a7.46 7.46 0 0 0 10.2-2.45c2.26-3.76 5.23-8.5 8.43-13.6 22.93-36.67 45.86-32.64 87.88-13.6l57.69 26.14a7.46 7.46 0 0 0 9.89-3.69l25.37-55.64a7.46 7.46 0 0 0-3.58-9.8c-17.7-8.28-52.95-24.76-78.55-36.68-73.2-34.04-127.8-33.37-164.94 49.99z" fill="#2684FF" />
    <path d="M246.74 57.94c3.11-5.12 6.63-11.06 9.26-15.66a7.46 7.46 0 0 0-2.68-10.2L199.13-1.38a7.46 7.46 0 0 0-10.2 2.45c-2.26 3.76-5.23 8.5-8.43 13.6-22.93 36.67-45.86 32.64-87.88 13.6L35.05 2.25a7.46 7.46 0 0 0-9.89 3.69L-.21 61.58a7.46 7.46 0 0 0 3.58 9.8c17.7 8.28 52.95 24.76 78.55 36.68 73.2 33.95 127.8 33.28 164.82-50.12z" fill="#0052CC" />
  </svg>
);

// Discord Logo
const DiscordIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 256 199" xmlns="http://www.w3.org/2000/svg">
    <path d="M216.856 16.597A208.502 208.502 0 0 0 164.042 0c-2.275 4.113-4.933 9.645-6.766 14.046-19.692-2.961-39.203-2.961-58.533 0-1.832-4.4-4.55-9.933-6.846-14.046a207.809 207.809 0 0 0-52.855 16.638C5.618 67.147-3.443 116.4 1.087 164.956c22.169 16.555 43.653 26.612 64.775 33.193A161.094 161.094 0 0 0 79.735 175.3a136.413 136.413 0 0 1-21.846-10.632 108.636 108.636 0 0 0 5.356-4.237c42.122 19.702 87.89 19.702 129.51 0a131.66 131.66 0 0 0 5.355 4.237 136.07 136.07 0 0 1-21.886 10.653c4.006 8.02 8.638 15.67 13.873 22.848 21.142-6.58 42.646-16.637 64.815-33.213 5.316-56.288-9.08-105.09-38.056-148.36zM85.474 135.095c-12.645 0-23.015-11.805-23.015-26.18s10.149-26.2 23.015-26.2c12.867 0 23.236 11.804 23.015 26.2.02 14.375-10.148 26.18-23.015 26.18zm85.051 0c-12.645 0-23.014-11.805-23.014-26.18s10.148-26.2 23.014-26.2c12.867 0 23.236 11.804 23.015 26.2 0 14.375-10.148 26.18-23.015 26.18z" fill="#5865F2" />
  </svg>
);

// Box Logo (official blue box)
const BoxIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="boxGradient" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#0061D5" />
        <stop offset="100%" stopColor="#0052B4" />
      </linearGradient>
    </defs>
    <rect x="4" y="8" width="40" height="32" rx="4" fill="url(#boxGradient)" />
    <path d="M19 18v12h2v-5.5l4 5.5h2.5l-4.5-6 4.5-6H25l-4 5.5V18h-2z" fill="white"/>
    <circle cx="32" cy="24" r="2.5" fill="white"/>
    <path d="M14 18c-1.5 0-2.5 1-2.5 2.5v7c0 1.5 1 2.5 2.5 2.5s2.5-1 2.5-2.5v-7c0-1.5-1-2.5-2.5-2.5z" fill="white"/>
  </svg>
);

// Airtable Logo
const AirtableIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 200 170" xmlns="http://www.w3.org/2000/svg">
    <path d="M90.04 8.51L8.17 36.18C-.27 39.05-.47 50.79 7.85 53.93l82.03 31.31c6.05 2.31 12.8 2.31 18.85 0l82.03-31.31c8.32-3.14 8.11-14.87-.11-17.75L108.89 8.51A31.1 31.1 0 0 0 90.04 8.51z" fill="#FCB400" />
    <path d="M105.97 92.54v69.52c0 5.26 5.33 8.87 10.2 6.92l80.78-32.46c3.09-1.24 5.13-4.23 5.13-7.64V59.36c0-5.26-5.33-8.87-10.2-6.92l-80.78 32.46A8.152 8.152 0 0 0 105.97 92.54z" fill="#18BFFF" />
    <path d="M92.09 97.6L26.6 52.32c-4.63-3.2-10.85.56-10.85 6.23v67.52c0 3.11 1.69 5.97 4.4 7.47l64.49 45.28c4.63 3.2 10.85-.56 10.85-6.23V104.86A8.51 8.51 0 0 0 92.09 97.6z" fill="#F82B60" />
  </svg>
);

// Coda Logo
const CodaIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.5 12c0-5.799-4.701-10.5-10.5-10.5S1.5 6.201 1.5 12s4.701 10.5 10.5 10.5c2.898 0 5.523-1.175 7.425-3.075l-3.75-3.75A5.959 5.959 0 0 1 12 17.25c-2.898 0-5.25-2.352-5.25-5.25S9.102 6.75 12 6.75s5.25 2.352 5.25 5.25c0 1.2-.402 2.304-1.08 3.187l3.75 3.75A10.43 10.43 0 0 0 22.5 12z" fill="#F46A54" />
  </svg>
);

// YouTube Logo
const YouTubeIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 256 180" xmlns="http://www.w3.org/2000/svg">
    <path d="M250.346 28.075A32.18 32.18 0 0 0 227.69 5.418C207.824 0 127.87 0 127.87 0S47.912.164 28.046 5.582A32.18 32.18 0 0 0 5.39 28.24c-6.009 35.298-8.34 89.084.165 122.97a32.18 32.18 0 0 0 22.656 22.657c19.866 5.418 99.822 5.418 99.822 5.418s79.955 0 99.82-5.418a32.18 32.18 0 0 0 22.657-22.657c6.338-35.551 8.101-89.246-.164-123.135z" fill="#FF0000" />
    <path d="m102.421 128.06 66.328-38.418-66.328-38.418z" fill="#FFF" />
  </svg>
);

const sizeConfig = {
  sm: "h-4 w-4",
  md: "h-5 w-5",
  lg: "h-6 w-6",
};

const customIconMap: Record<string, React.FC<{ className?: string }>> = {
  "google-drive": GoogleDriveIcon,
  "google_drive": GoogleDriveIcon,
  "notion": NotionIcon,
  "onedrive": OneDriveIcon,
  "one_drive": OneDriveIcon,
  "sharepoint": SharePointIcon,
  "dropbox": DropboxIcon,
  "slack": SlackIcon,
  "teams": TeamsIcon,
  "url-crawler": GlobeIcon,
  "url_crawler": GlobeIcon,
  "confluence": ConfluenceIcon,
  "discord": DiscordIcon,
  "box": BoxIcon,
  "airtable": AirtableIcon,
  "coda": CodaIcon,
  "youtube": YouTubeIcon,
  "github": GitHubIcon,
  "amazon-s3": AmazonS3Icon,
  "amazon_s3": AmazonS3Icon,
  "s3": AmazonS3Icon,
};

// Fallback icons with colors for sources without custom SVGs
const fallbackConfig: Record<string, { icon: typeof Upload; color: string }> = {
  "sftp": { icon: Server, color: "text-muted-foreground" },
  "file-upload": { icon: Upload, color: "text-primary" },
  "file_upload": { icon: Upload, color: "text-primary" },
};

export function DataSourceIcon({ sourceId, className, size = "md" }: DataSourceIconProps) {
  const CustomIcon = customIconMap[sourceId];
  const iconSize = sizeConfig[size];

  // If we have a custom brand icon, use it directly (no wrapper)
  if (CustomIcon) {
    return <CustomIcon className={cn(iconSize, className)} />;
  }

  // Fallback to Lucide icons
  const fallback = fallbackConfig[sourceId] || { icon: Upload, color: "text-muted-foreground" };
  const FallbackIcon = fallback.icon;

  return <FallbackIcon className={cn(iconSize, fallback.color, className)} />;
}
