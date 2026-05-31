import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FFCES - نظام إدارة العهد المالية الميدانية",
  description: "نظام متكامل لإدارة العهد المالية والمستحقات والعمليات الميدانية",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ar" dir="rtl">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased min-h-screen bg-background font-sans">
        {children}
      </body>
    </html>
  );
}
