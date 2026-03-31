import { useCurrentFrame, interpolate } from 'remotion';
import { SubtitleSegment } from './parseSubtitles';

interface SubtitlesProps {
  segments: SubtitleSegment[];
}

export const Subtitles: React.FC<SubtitlesProps> = ({ segments }) => {
  const frame = useCurrentFrame();

  // Find the active subtitle for the current frame
  const active = segments.find(
    (seg) => frame >= seg.startFrame && frame < seg.endFrame
  );

  if (!active) return null;

  // Fade in/out near segment boundaries
  const fadeInDuration = 5;
  const fadeOutDuration = 5;

  const opacity = interpolate(
    frame,
    [
      active.startFrame,
      active.startFrame + fadeInDuration,
      active.endFrame - fadeOutDuration,
      active.endFrame,
    ],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  return (
    <div
      style={{
        position: 'absolute',
        bottom: '10%',
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        opacity,
      }}
    >
      <span
        style={{
          color: '#ffffff',
          fontSize: 48,
          fontFamily: 'Arial, sans-serif',
          fontWeight: 'bold',
          textAlign: 'center',
          lineHeight: 1.4,
          padding: '12px 24px',
          backgroundColor: 'rgba(0, 0, 0, 0.6)',
          borderRadius: 12,
          textShadow: '2px 2px 4px rgba(0, 0, 0, 0.8)',
          maxWidth: '80%',
        }}
      >
        {active.text}
      </span>
    </div>
  );
};
