import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Multi-Agent Newsroom",
  description: "An evidence-first autonomous newsroom with human editorial control.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
