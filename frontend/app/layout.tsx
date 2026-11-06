import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "AVRT Studio · Không còn rào cản ngôn ngữ",
  description:
    "Không gian dịch hội thoại Anh–Việt, model mở và giám sát tài nguyên trực tiếp.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
