export const metadata = {
  title: "Invoice Photo Proof",
  description: "Send invoice to finance with photo proof",
  viewport: "width=device-width, initial-scale=1, viewport-fit=cover",
};
export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif", background: "#eef2f7", color: "#0f172a" }}>
        {children}
      </body>
    </html>
  );
}
