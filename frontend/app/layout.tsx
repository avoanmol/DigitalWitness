
import "./globals.css";
import { Suspense } from "react";
import Link from "next/link";
import { Montserrat } from "next/font/google";
import RoleNav from "@/components/RoleNav";
import BackButton from "@/components/BackButton";

const font = Montserrat({ subsets: ["latin"] });

export const metadata = {
  title: "DigitalWitness",
  description: "Save your evidence. Show it hasn't changed.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${font.className} min-h-screen bg-white text-[#242424] antialiased`}>
        <div className="mx-auto min-h-screen w-full max-w-[1440px] px-5 sm:px-8 lg:px-14">
          <header className="flex min-h-[88px] flex-wrap items-center justify-between gap-5 border-b border-[#E8E6E0] py-5">
            <Link
              href="/report/new"
              className="text-xl font-bold tracking-tight text-[#242424]"
            >
              DigitalWitness
            </Link>

            <RoleNav />
          </header>

          <Suspense fallback={null}>
            <BackButton />
          </Suspense>

          <div className="pb-16 pt-8 sm:pt-10">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
