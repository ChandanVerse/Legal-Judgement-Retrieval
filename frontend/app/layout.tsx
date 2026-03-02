import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Legal Assistant",
  description: "AI-powered legal case search for Indian judgments",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Playfair+Display:wght@400;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased font-sans bg-legal-cream">{children}</body>
    </html>
  );
}
