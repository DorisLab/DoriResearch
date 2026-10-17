export function SavedTime({ value }: { value: number }) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const pad = (n: number) => String(n).padStart(2, '0');
  const text = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  return (
    <time dateTime={date.toISOString()} title="最近保存时间">
      {text}
    </time>
  );
}
