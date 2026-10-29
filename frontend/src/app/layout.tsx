import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import "./redesign.css";

export const metadata: Metadata = {
  title: { default: "DigitalWitness | Document what happened", template: "%s · DigitalWitness" },
  description: "Privately preserve digital evidence, review AI-assisted notes, and prepare a complaint draft when you are ready.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
