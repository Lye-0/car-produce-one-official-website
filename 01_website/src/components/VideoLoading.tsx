import type { JourneyState } from '../journey/useJourney';
export function VideoLoading({ state }: { state: JourneyState }) {
  const { startup } = state;
  if (
    !startup.blocked &&
    !state.videoWaiting &&
    !state.boundaryWaiting &&
    !startup.error
  )
    return null;
  if ((state.entered && !state.boundaryWaiting) || state.reduced) return null;
  const full = startup.blocked && startup.stage === 'city';
  const label = startup.error
    ? '映像を読み込めませんでした'
    : full
      ? '街の映像を準備中'
      : startup.blocked
        ? '店内の映像を準備中'
        : 'この先の映像を準備中';
  return (
    <div
      className={`video-loading ${full ? 'video-loading--black' : 'video-loading--glass'}`}
      data-stage={startup.blocked ? startup.stage : 'buffering'}
    >
      <div className="video-loading-card">
        <div className="video-loading-ring" aria-hidden="true" />
        <p role="status" aria-live="polite">
          {label}
        </p>
        {!startup.error && (startup.blocked || state.boundaryWaiting) && (
          <span
            className="video-loading-percent"
            role="progressbar"
            aria-label={label}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={
              startup.blocked ? startup.progress : state.boundaryProgress
            }
          >
            {startup.blocked ? startup.progress : state.boundaryProgress}
            <small>%</small>
          </span>
        )}
        {startup.error && (
          <div className="video-loading-actions">
            <button
              onClick={() => {
                state.setFailed(false);
                startup.retry();
              }}
            >
              再試行
            </button>
            <button
              onClick={() => {
                startup.bypass();
                state.skip();
              }}
            >
              サイトへ進む
            </button>
          </div>
        )}
        {full && state.paused && !startup.error && (
          <button onClick={state.togglePause}>
            {state.paused ? '背景の映像を再生' : '背景の映像を一時停止'}
          </button>
        )}
      </div>
    </div>
  );
}
