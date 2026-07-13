const LOCAL_TIME_ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";

export function parseUtcDate(value) {
  if (!value) return null;
  const normalized = typeof value === "string" && !/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? `${value.replace(" ", "T")}Z` : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function utcTime(value) {
  return parseUtcDate(value)?.getTime() || 0;
}

function formatLocalTime(date) {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: LOCAL_TIME_ZONE,
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(date);
}

export function formatPktDateTime(value) {
  const date = parseUtcDate(value);
  if (!date) return "";
  const localDate = new Date(date.getTime());
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const localDay = new Date(localDate.getFullYear(), localDate.getMonth(), localDate.getDate());

  if (localDay.getTime() === today.getTime()) {
    return `Today - ${formatLocalTime(localDate)}`;
  }
  if (localDay.getTime() === yesterday.getTime()) {
    return `Yesterday - ${formatLocalTime(localDate)}`;
  }
  const dayDiff = Math.round((today.getTime() - localDay.getTime()) / 86400000);
  if (dayDiff > 1 && dayDiff < 7) {
    return `${new Intl.DateTimeFormat("en-US", {
      weekday: "long",
      timeZone: LOCAL_TIME_ZONE,
    }).format(localDate)} - ${formatLocalTime(localDate)}`;
  }
  return new Intl.DateTimeFormat("en-US", {
    timeZone: LOCAL_TIME_ZONE,
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(localDate);
}

export function formatPktFull(value) {
  const date = parseUtcDate(value);
  if (!date) return "";
  return new Intl.DateTimeFormat("en-US", {
    timeZone: LOCAL_TIME_ZONE,
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
