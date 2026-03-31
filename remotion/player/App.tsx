import { Player } from '@remotion/player';
import { VideoComposition } from '../src/VideoComposition';
import { parseSrt } from '../src/parseSubtitles';
import { useMemo } from 'react';

function getQueryParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    audio: params.get('audio') || '',
    subtitles: params.get('subtitles') || '',
    images: params.get('images') || '',
    title: params.get('title') || '',
  };
}

export const App: React.FC = () => {
  const params = useMemo(() => getQueryParams(), []);

  const audioSrc = params.audio;
  const subtitleText = params.subtitles
    ? decodeURIComponent(params.subtitles)
    : '';
  const backgroundImages = params.images
    ? params.images.split(',').filter(Boolean)
    : [];
  const titleText = params.title;

  const fps = 30;

  // Calculate duration from subtitles (fallback: 10 seconds)
  const segments = useMemo(() => parseSrt(subtitleText, fps), [subtitleText]);
  const lastEndFrame =
    segments.length > 0 ? segments[segments.length - 1].endFrame : fps * 10;
  const durationInFrames = lastEndFrame + fps * 3; // 3-second buffer

  const compositionProps = {
    audioSrc,
    subtitleText,
    backgroundImages,
    titleText: titleText || undefined,
    fps,
    width: 1920,
    height: 1080,
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '24px',
        minHeight: '100vh',
        background: '#1a1a2e',
      }}
    >
      <h2 style={{ color: '#fff', marginBottom: '16px', fontSize: '24px' }}>
        Video Preview
      </h2>
      <Player
        component={VideoComposition}
        durationInFrames={durationInFrames}
        compositionWidth={1920}
        compositionHeight={1080}
        fps={fps}
        inputProps={compositionProps}
        controls
        style={{
          width: '100%',
          maxWidth: '960px',
          aspectRatio: '16/9',
        }}
      />
    </div>
  );
};
