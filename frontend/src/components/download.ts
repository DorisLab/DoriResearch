let handler: ((path: string) => void) | undefined;
export const setDownloadHandler = (value: (path: string) => void) => {
  handler = value;
};
export function hostDownload(path: string) {
  if (!handler) return false;
  handler(path);
  return true;
}
