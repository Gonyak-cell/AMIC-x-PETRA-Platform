import type { CalendarEvent } from "@/types/calendar";

function formatIcsDate(date: string): string {
  return date.replace(/-/g, "") + "T000000";
}

function escapeIcsText(text: string): string {
  return text.replace(/[\\;,\n]/g, (match) => {
    if (match === "\n") return "\\n";
    return `\\${match}`;
  });
}

export function generateIcs(events: CalendarEvent[]): string {
  const lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//AMIC x PETRA Platform//Calendar//EN",
    "CALSCALE:GREGORIAN",
  ];

  for (const event of events) {
    lines.push("BEGIN:VEVENT");
    lines.push(`UID:${event.id}@amic-petra`);
    lines.push(`DTSTART:${formatIcsDate(event.date)}`);
    if (event.endDate) {
      lines.push(`DTEND:${formatIcsDate(event.endDate)}`);
    }
    lines.push(`SUMMARY:${escapeIcsText(event.title)}`);
    lines.push(
      `DESCRIPTION:${escapeIcsText(`Module: ${event.module.toUpperCase()} | Type: ${event.type}`)}`,
    );
    lines.push("END:VEVENT");
  }

  lines.push("END:VCALENDAR");
  return lines.join("\r\n");
}

export function downloadIcs(events: CalendarEvent[], filename = "calendar.ics") {
  const content = generateIcs(events);
  const blob = new Blob([content], { type: "text/calendar;charset=utf-8" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}
