import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "VieNeu Studio",
    short_name: "VieNeu",
    description: "PWA control surface for a local VieNeu TTS server",
    start_url: "/",
    display: "standalone",
    background_color: "#f7f9f8",
    theme_color: "#0f8b83",
    icons: [
      {
        src: "/icons/icon.svg",
        sizes: "any",
        type: "image/svg+xml"
      },
      {
        src: "/icons/maskable.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "maskable"
      }
    ]
  };
}
