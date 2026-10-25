import "./globals.css";
import { Suspense } from "react";
import Link from "next/link";
import { Montserrat } from "next/font/google";
import RoleNav from "@/components/RoleNav";
import BackButton from "@/components/BackButton";

const font = Montserrat({ subsets: ["latin"] });

export const metadata = {
  title: "DigitalWitness",
  description: "Save your evidence. Show it hasn’t changed.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${font.className} bg-page text-ink antialiased`}>
        <div className="mx-auto my-3 max-w-6xl rounded-[2rem] bg-paper p-4 sm:my-6 sm:p-8">
          <header className="flex items-center justify-between">
            <Link href="/report/new" className="font-bold">
              DigitalWitness
            </Link>
            <RoleNav />
          </header>
          <Suspense fallback={null}>
            <BackButton />
          </Suspense>
          {children}
        </div>
      </body>
    </html>
  );
}