import type { JourneyState } from '../journey/useJourney';
export function SiteHeader({ state }: { state: JourneyState }) {
  const {
    skip,
    entered,
    liveEnabled,
    pastHero,
    spacer,
    reduced,
    go,
    menu,
    setMenu,
  } = state;
  return (
    <>
      <a
        className="skip-link"
        href="#services"
        onClick={(e) => {
          e.preventDefault();
          skip('services');
        }}
      >
        サービスへ移動
      </a>
      <header
        className={
          'site-header ' +
          (entered && (!liveEnabled || pastHero) ? 'header-body' : '')
        }
      >
        <button
          className="wordmark"
          onClick={() =>
            entered
              ? window.scrollTo({
                  top: spacer.current?.offsetHeight ?? 0,
                  behavior: reduced ? 'instant' : 'smooth',
                })
              : go(0)
          }
          aria-label="CAR PRODUCE ONE トップ"
        >
          CAR PRODUCE ONE<span>AUTOMOTIVE / SERVICE & CARE</span>
        </button>
        <nav className="desktop-nav" aria-label="メインナビゲーション">
          <a
            href="#services"
            onClick={(e) => {
              if (!entered) {
                e.preventDefault();
                skip('services');
              }
            }}
          >
            サービス
          </a>
          <a
            href="#about"
            onClick={(e) => {
              if (!entered) {
                e.preventDefault();
                skip('about');
              }
            }}
          >
            私たちについて
          </a>
          <a
            href="#access"
            onClick={(e) => {
              if (!entered) {
                e.preventDefault();
                skip('access');
              }
            }}
          >
            アクセス
          </a>
          <a
            href="#contact"
            className="contact-link"
            onClick={(e) => {
              if (!entered) {
                e.preventDefault();
                skip('contact');
              }
            }}
          >
            相談する <span>↗</span>
          </a>
        </nav>
        <button
          className="menu-toggle"
          aria-label={menu ? 'メニューを閉じる' : 'メニューを開く'}
          aria-controls="mobile-menu"
          aria-expanded={menu}
          onClick={() => setMenu(!menu)}
        >
          {menu ? '閉じる −' : 'MENU +'}
        </button>
      </header>
      {menu && (
        <nav
          id="mobile-menu"
          className="menu-panel"
          aria-label="メインナビゲーション"
        >
          {[
            ['services', 'サービス'],
            ['about', '私たちについて'],
            ['access', 'アクセス'],
            ['contact', '相談する'],
          ].map(([id, label]) => (
            <a
              key={id}
              href={'#' + id}
              onClick={(e) => {
                e.preventDefault();
                skip(id);
              }}
            >
              {label} ↗
            </a>
          ))}
        </nav>
      )}
    </>
  );
}
