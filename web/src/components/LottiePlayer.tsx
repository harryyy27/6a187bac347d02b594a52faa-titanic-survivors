import { useEffect, useRef } from 'react';
import type { AnimationItem } from 'lottie-web';

interface LottiePlayerProps {
  /** Path (served from public/, e.g. under animations/) to a Lottie JSON file. */
  animationPath: string;
  loop?: boolean;
  autoplay?: boolean;
  className?: string;
}

/**
 * Renders a Lottie animation (e.g. public/animations/survive.json or
 * not_survive.json) into a container div. Loads lottie-web lazily via a
 * dynamic import so the library is never touched outside the browser
 * (e.g. during SSR or unit tests running under Node).
 */
export function LottiePlayer({
  animationPath,
  loop = true,
  autoplay = true,
  className,
}: LottiePlayerProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (typeof window === 'undefined' || !containerRef.current) {
      return;
    }

    let animationInstance: AnimationItem | null = null;
    let cancelled = false;

    import('lottie-web').then(({ default: lottie }) => {
      if (cancelled || !containerRef.current) {
        return;
      }
      animationInstance = lottie.loadAnimation({
        container: containerRef.current,
        renderer: 'svg',
        loop,
        autoplay,
        path: animationPath,
      });
    });

    return () => {
      cancelled = true;
      animationInstance?.destroy();
    };
  }, [animationPath, loop, autoplay]);

  return <div ref={containerRef} className={className} data-testid="lottie-player" />;
}

export default LottiePlayer;
