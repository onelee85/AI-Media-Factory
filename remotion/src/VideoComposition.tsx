import {
  AbsoluteFill,
  Audio,
  Composition,
  Img,
  interpolate,
  Sequence,
  staticFile,
  useCurrentFrame,
} from 'remotion';
import { Subtitles } from './Subtitles';
import { parseSrt } from './parseSubtitles';

export type VideoCompositionProps = {
  audioSrc: string;
  subtitleText: string;
  backgroundImages: string[];
  titleText?: string;
  fps?: number;
  width?: number;
  height?: number;
};

const Background: React.FC<{
  images: string[];
  totalFrames: number;
  fps: number;
}> = ({ images, totalFrames, fps }) => {
  const frame = useCurrentFrame();

  if (!images || images.length === 0) {
    return (
      <AbsoluteFill
        style={{
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
        }}
      />
    );
  }

  const secondsPerImage = Math.max(totalFrames / images.length / fps, 3);
  const framesPerImage = Math.round(secondsPerImage * fps);
  const currentIndex = Math.min(
    Math.floor(frame / framesPerImage),
    images.length - 1
  );

  // Crossfade between images
  const localFrame = frame % framesPerImage;
  const crossfadeDuration = Math.round(0.5 * fps);

  const opacity =
    images.length === 1
      ? 1
      : interpolate(
          localFrame,
          [
            0,
            crossfadeDuration,
            framesPerImage - crossfadeDuration,
            framesPerImage,
          ],
          [0, 1, 1, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );

  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
        }}
      />
      <AbsoluteFill style={{ opacity }}>
        <Img
          src={images[currentIndex]}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const TitleOverlay: React.FC<{ title: string; fps: number }> = ({
  title,
  fps,
}) => {
  const frame = useCurrentFrame();
  const titleDuration = Math.round(3 * fps);

  const opacity = interpolate(
    frame,
    [0, Math.round(0.5 * fps), titleDuration - Math.round(0.5 * fps), titleDuration],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  if (frame >= titleDuration) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: '40%',
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        opacity,
      }}
    >
      <h1
        style={{
          color: '#ffffff',
          fontSize: 72,
          fontFamily: 'Arial, sans-serif',
          fontWeight: 'bold',
          textAlign: 'center',
          textShadow: '3px 3px 6px rgba(0, 0, 0, 0.8)',
        }}
      >
        {title}
      </h1>
    </div>
  );
};

const VideoCompositionInner: React.FC<VideoCompositionProps> = ({
  audioSrc,
  subtitleText,
  backgroundImages,
  titleText,
  fps = 30,
}) => {
  const frame = useCurrentFrame();
  const segments = parseSrt(subtitleText, fps);

  // Calculate total frames from segments for background timing
  const lastEndFrame =
    segments.length > 0 ? segments[segments.length - 1].endFrame : fps * 10;
  const totalFrames = lastEndFrame + fps;

  return (
    <AbsoluteFill>
      {/* Background layer */}
      <Background
        images={backgroundImages}
        totalFrames={totalFrames}
        fps={fps}
      />

      {/* Audio layer */}
      {audioSrc && <Audio src={audioSrc} />}

      {/* Title overlay */}
      {titleText && <TitleOverlay title={titleText} fps={fps} />}

      {/* Subtitles layer */}
      <Subtitles segments={segments} />
    </AbsoluteFill>
  );
};

// calculateMetadata: dynamically set duration from audio
const calculateMetadata = async ({ props }: { props: VideoCompositionProps }) => {
  const fps = props.fps || 30;
  let durationInSeconds = 10; // default fallback

  if (props.audioSrc) {
    try {
      const { Input, UrlSource, ALL_FORMATS } = await import('mediabunny');
      const input = new Input({
        source: new UrlSource(props.audioSrc),
        formats: ALL_FORMATS,
      });
      const duration = await input.computeDuration();
      if (duration && isFinite(duration)) {
        durationInSeconds = duration;
      }
    } catch {
      // Fallback: estimate from subtitle timing
    }
  }

  if (durationInSeconds === 10 && props.subtitleText) {
    const segments = parseSrt(props.subtitleText, fps);
    if (segments.length > 0) {
      durationInSeconds = segments[segments.length - 1].endMs / 1000;
    }
  }

  // Add 30-frame buffer after last subtitle
  const durationInFrames = Math.ceil(durationInSeconds * fps) + 30;

  return { durationInFrames };
};

export const VideoComposition: React.FC<VideoCompositionProps> = (props) => {
  return <VideoCompositionInner {...props} />;
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="VideoComposition"
      component={VideoComposition}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{
        audioSrc: '',
        subtitleText: '',
        backgroundImages: [],
        titleText: '',
        fps: 30,
        width: 1920,
        height: 1080,
      }}
      calculateMetadata={calculateMetadata}
    />
  );
};
