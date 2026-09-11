import { content as c } from '../content';
import { MainHero } from '../components/MainHero';
import { MediaVideo } from '../media/MediaVideo';
import { ScrubMediaVideo } from '../media/ScrubMediaVideo';
import { getProductionClip, getProductionPoster } from '../media/production';
import { JunctionTransition } from './JunctionTransition';
import { JUNCTION_END, JUNCTION_MEDIA_VERSION } from './junction';
import { MonitorPortal } from '../portal/MonitorPortal';
import type { JourneyState } from './useJourney';
export function Journey({ state }: { state: JourneyState }) {
  const {
    city,
    film,
    filmSecond,
    portalFilm,
    heroViewport,
    heroSlot,
    tools,
    magazines,
    monitor,
    portalBypass,
    setPortalEndReady,
    scene,
    turnReady,
    setTurnReady,
    ready,
    setReady,
    portalReady,
    setPortalReady,
    failed,
    setFailed,
    paused,
    setPaused,
    reduced,
    visible,
    variant,
    idleReady,
    setIdleReady,
    requestedMedia,
    profile,
    liveEnabled,
    liveMedia,
    chapter,
    entered,
    portal,
    moving,
    asset,
    streetAsset,
    junction,
    go,
    skip,
    togglePause,
    card,
    journeyUiOpacity,
    poster,
  } = state;
  return (
    <section
      hidden={entered}
      className={
        'journey scroll-journey ' +
        (moving ? 'moving ' : '') +
        (portal ? 'portal ' : '') +
        (liveEnabled && scene.time >= 78 ? 'monitor-portal-journey' : '')
      }
      aria-label="店舗を巡る映像"
    >
      <picture className="film fallback">
        <source
          media="(max-width:700px)"
          srcSet={
            getProductionPoster('mobile', poster) ??
            (poster === 'city'
              ? `/media/images/fallback/mobile/drive.jpg?v=${JUNCTION_MEDIA_VERSION}`
              : '/media/images/fallback/mobile/' + poster + '.jpg')
          }
        />
        <img
          src={
            getProductionPoster('desktop', poster) ??
            (poster === 'city'
              ? `/media/images/fallback/desktop/drive.jpg?v=${JUNCTION_MEDIA_VERSION}`
              : '/media/images/fallback/desktop/' + poster + '.jpg')
          }
          alt=""
        />
      </picture>
      <MediaVideo
        aria-hidden="true"
        videoRef={city}
        style={{
          opacity:
            scene.progress < JUNCTION_END &&
            (junction.stage === 'drive' || !turnReady) &&
            !reduced
              ? 1
              : 0,
        }}
        className="film city"
        autoPlay={false}
        muted
        loop
        playsInline
        poster={
          getProductionPoster(profile, 'city') ?? streetAsset('drive.jpg')
        }
        media={getProductionClip(variant, 'drive')}
        enabled={!reduced}
        preload="auto"
        playing={
          visible && scene.progress === 0 && !paused && !reduced && !entered
        }
        onPlayBlocked={() => setPaused(true)}
        onError={() => setFailed(true)}
      />
      <JunctionTransition
        profile={variant}
        requested={requestedMedia.junction && !reduced}
        time={junction.turnTime}
        active={
          junction.stage === 'turn' &&
          scene.progress < JUNCTION_END &&
          !reduced &&
          !failed
        }
        onReady={setTurnReady}
      />
      <ScrubMediaVideo
        videoRef={film}
        secondRef={filmSecond}
        time={scene.time}
        className={
          'film interior ' +
          (ready && scene.time < 81 && !reduced && !failed ? 'visible' : ' ')
        }
        media={getProductionClip(variant, 'route')}
        enabled={requestedMedia.route && !reduced}
        onReady={setReady}
        onError={() => setFailed(true)}
      />
      <MediaVideo
        aria-hidden="true"
        videoRef={portalFilm}
        className={
          'film portal-film ' +
          (scene.time >= 81 && portalReady && !reduced ? 'visible' : '')
        }
        muted
        playsInline
        preload="metadata"
        media={liveMedia('portal')}
        enabled={requestedMedia.portal && !reduced}
        onLoadStart={() => setPortalReady(false)}
        onError={() => {
          setPortalReady(false);
          if (liveEnabled) setFailed(true);
        }}
        onLoadedData={() => setPortalReady(true)}
      />
      {(
        [
          ['tools', tools],
          ['magazines', magazines],
          ['monitor', monitor],
        ] as const
      ).map(([name, ref]) => (
        <MediaVideo
          aria-hidden="true"
          key={name}
          videoRef={ref}
          className="film ambient"
          style={{
            opacity:
              scene.hold === name && idleReady[name] && !reduced
                ? scene.cardOpacity
                : 0,
          }}
          muted
          loop
          playsInline
          preload="auto"
          media={
            name === 'monitor'
              ? liveMedia('monitor-idle')
              : getProductionClip(variant, name + '-idle')
          }
          enabled={requestedMedia[name] && !reduced}
          onLoadStart={() => setIdleReady((v) => ({ ...v, [name]: false }))}
          playing={
            visible && !entered && !paused && !reduced && scene.hold === name
          }
          onLoadedData={() => setIdleReady((v) => ({ ...v, [name]: true }))}
        />
      ))}
      {scene.hold && !idleReady[scene.hold] && (
        <img
          className="film hold-poster"
          src={
            getProductionPoster(profile, scene.hold) ??
            asset(scene.hold + '.jpg')
          }
          alt=""
        />
      )}

      <MonitorPortal
        profile={profile}
        enabled={liveEnabled}
        time={scene.time}
        hold={scene.hold === 'monitor'}
        complete={scene.complete}
        entered={entered}
        bypass={portalBypass && scene.complete}
        route={film}
        routeSecond={filmSecond}
        portal={portalFilm}
        monitor={monitor}
        viewport={heroViewport}
        slot={heroSlot}
        onEndpoint={setPortalEndReady}
      />
      <div className="film-shade" />
      {scene.progress < 0.03 && (
        <div className="welcome" style={{ opacity: scene.introOpacity }}>
          <p className="eyebrow">TOYONAKA, OSAKA / AUTOMOTIVE CARE</p>
          <h1>
            {c.headline[0]}
            <br />
            {c.headline[1]}
          </h1>
          <p className="welcome-caption">車と過ごす日々を、あなたらしく。</p>
          <button className="text-link" onClick={() => go(1)}>
            店舗を巡る <span>↗</span>
          </button>
        </div>
      )}
      {card && (
        <article
          style={{ opacity: scene.cardOpacity }}
          inert={scene.cardOpacity < 0.1}
          aria-hidden={scene.cardOpacity < 0.1}
          key={chapter}
          className={'reading-card card-' + chapter}
        >
          <p className="eyebrow">{card.label}</p>
          <h2>{card.title}</h2>
          <p>{card.body}</p>
          <button className="text-link" onClick={() => skip('services')}>
            サービスを見る <span>↗</span>
          </button>
        </article>
      )}
      {scene.inviteOpacity > 0 && (
        <div
          className="monitor-invite"
          inert={scene.inviteOpacity < 0.1}
          aria-hidden={scene.inviteOpacity < 0.1}
          style={{ opacity: scene.inviteOpacity }}
        >
          <p className="eyebrow">03 / CONTINUE THE STORY</p>
          <h2>この先も、あなたと。</h2>
          <button className="text-link" onClick={() => go(4)}>
            サイトへ入る ↗
          </button>
        </div>
      )}
      {portal && reduced && (
        <div
          className="reduced-handoff"
          inert
          style={{ opacity: scene.portal }}
          aria-hidden="true"
        >
          <MainHero />
        </div>
      )}
      <div
        className="journey-bottom"
        style={liveEnabled ? { opacity: journeyUiOpacity } : undefined}
        inert={liveEnabled && journeyUiOpacity === 0}
      >
        <div className="chapter-nav" aria-label="映像の場面">
          {c.chapters.map((label, i) => (
            <button
              key={label}
              aria-current={chapter === i ? 'step' : undefined}
              onClick={() => go(i)}
            >
              <span>0{i + 1}</span>
              <b>{label}</b>
            </button>
          ))}
        </div>
        <div className="journey-actions">
          <button
            onClick={togglePause}
            aria-label={paused ? '背景の動きを再生' : '背景の動きを一時停止'}
          >
            {paused ? '背景を再生 ▷' : '背景を停止 Ⅱ'}
          </button>
          <button className="next" onClick={() => go(chapter + 1)}>
            {chapter === 3 ? 'サイトへ' : '次の場面へ'} <span>↓</span>
          </button>
        </div>
      </div>
      <span
        className="status"
        aria-live="polite"
        style={liveEnabled ? { opacity: journeyUiOpacity } : undefined}
      >
        {failed
          ? '映像を読み込めませんでした。各場面とサービスは引き続きご覧いただけます。'
          : reduced
            ? '動きを抑えて表示しています。'
            : 'スクロールに合わせて進みます / 上へ戻すとカメラも戻ります'}
      </span>
    </section>
  );
}
