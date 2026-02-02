import { renderResumeHtml } from "../../../lib/render-resume";
import { generatePdfBuffer } from "../../../lib/pdf-generator";
import { rateLimit } from "../../../lib/rate-limiter";

export const runtime = "nodejs";

function getClientIp(request) {
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    return forwarded.split(",")[0].trim();
  }
  return request.headers.get("x-real-ip") || "unknown";
}

export async function POST(request) {
  const ip = getClientIp(request);
  const limitResult = rateLimit(ip);

  if (!limitResult.allowed) {
    return new Response(
      JSON.stringify({ error: "Rate limit excedido. Intentá más tarde." }),
      {
        status: 429,
        headers: {
          "Content-Type": "application/json",
          "Retry-After": "60"
        }
      }
    );
  }

  try {
    const resume = await request.json();
    const html = renderResumeHtml(resume);
    const pdfBuffer = await generatePdfBuffer(html);

    return new Response(pdfBuffer, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": "attachment; filename=\"cv.pdf\""
      }
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: "JSON inválido o error al generar." }), {
      status: 400,
      headers: {
        "Content-Type": "application/json"
      }
    });
  }
}
