import "./globals.css";

export const metadata = {
  title: "Editor de CV",
  description: "Editor visual de CV en una página con exportación a PDF."
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
