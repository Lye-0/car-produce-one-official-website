import type { JourneyState } from '../journey/useJourney';
import { useLayoutEffect, useRef } from 'react';
export function SiteHeader({ state }: { state: JourneyState }) {
  const header = useRef<HTMLElement>(null);
  useLayoutEffect(() => {
    const element = header.current;
    if (!element) return;
    const update = () =>
      document.documentElement.style.setProperty(
        '--site-header-bottom',
        `${element.getBoundingClientRect().bottom}px`,
      );
    const observer = new ResizeObserver(update);
    observer.observe(element);
    update();
    return () => {
      observer.disconnect();
      document.documentElement.style.removeProperty('--site-header-bottom');
    };
  }, []);
  const { skip, entered, liveEnabled, pastHero, replay, menu, setMenu } = state;
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
        ref={header}
        className={
          'site-header ' +
          (entered && (!liveEnabled || pastHero) ? 'header-body' : '')
        }
      >
        <button
          className="wordmark"
          onClick={replay}
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
