import { useEffect, useState } from 'react';
import type { ResearchHost } from '../types';

export function PublishedImage({
  path,
  alt,
  host,
}: {
  path: string;
  alt?: string;
  host: ResearchHost;
}) {
  const readImage = host.readImage;
  const [loaded, setLoaded] = useState<{ path: string; url?: string; error?: string }>();
  useEffect(() => {
    let active = true;
    void readImage?.(path).then(
      (url) => {
        if (active) setLoaded({ path, url });
      },
      (error) => {
        if (active) setLoaded({ path, error: String(error) });
      },
    );
    return () => {
      active = false;
    };
  }, [path, readImage]);
  const value = loaded?.path === path ? loaded : undefined;
  return value?.url && /^data:image\/(png|jpeg|webp|svg\+xml);base64,/.test(value.url) ? (
    <img className="published-cover" src={value.url} alt={alt || '研究图表'} />
  ) : (
    <span>{value?.error || alt || '正在读取图表…'}</span>
  );
}
