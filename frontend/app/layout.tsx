import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AML Investigation Copilot // AI Command Center",
  description: "Futuristic Anti-Money Laundering AI financial intelligence investigation workstation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#030712] text-gray-100 min-h-screen selection:bg-cyan-500/30 selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}
