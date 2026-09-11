import { content as c } from '../content';
export function MainHero({
  projected = false,
  mobileWings = false,
}: {
  projected?: boolean;
  mobileWings?: boolean;
}) {
  return (
    <section className={'main-hero' + (projected ? ' portal-live-hero' : '')}>
      {projected && (
        <canvas className="portal-hero-background" aria-hidden="true" />
      )}
      {mobileWings && (
        <div className="mobile-monitor-wings" aria-hidden="true">
          <div className="monitor-wing monitor-wing-left">
            <img
              src="/media/images/monitor-wings/tools.webp"
              alt=""
              decoding="async"
            />
          </div>
          <div className="monitor-wing monitor-wing-right">
            <img
              src="/media/images/monitor-wings/car.jpg"
              alt=""
              decoding="async"
            />
          </div>
        </div>
      )}
      <div className="hero-label eyebrow">
        CAR PRODUCE ONE — TOYONAKA, OSAKA
      </div>
      <h1>
        {c.headline[0]}
        <br />
        {c.headline[1]}
      </h1>
      <div className="hero-bottom">
        <p>
          車と過ごす日々に、
          <br />
          あなたらしい選択を。
        </p>
        <a
          className={projected ? 'portal-hero-link' : 'text-link'}
          href="#services"
        >
          {projected ? (
            <span className="text-link">
              私たちにできること <span>↓</span>
            </span>
          ) : (
            <>
              私たちにできること <span>↓</span>
            </>
          )}
        </a>
      </div>
      <div className="hero-rule" />
      <div className="giant-type" aria-hidden="true">
        ONE.
      </div>
    </section>
  );
}
