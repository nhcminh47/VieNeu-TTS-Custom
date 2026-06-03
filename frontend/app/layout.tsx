import type { Metadata, Viewport } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "VieNeu Studio",
  description: "Local PWA control surface for VieNeu TTS Server",
  applicationName: "VieNeu Studio",
  appleWebApp: {
    capable: true,
    title: "VieNeu Studio",
    statusBarStyle: "default"
  }
};

export const viewport: Viewport = {
  themeColor: "#0f8b83",
  width: "device-width",
  initialScale: 1
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
